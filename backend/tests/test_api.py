"""API integration tests using httpx + async."""
import pytest
import pytest_asyncio
import tempfile
import os
import csv

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db


# ── Test DB setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///./test_financial.db"

test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    if os.path.exists("./test_financial.db"):
        os.remove("./test_financial.db")


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_api_info(client: AsyncClient):
    resp = await client.get("/api/v1/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data


# ── Documents API ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    resp = await client.get("/api/v1/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


@pytest.mark.asyncio
async def test_upload_csv(client: AsyncClient, tmp_path):
    csv_file = tmp_path / "test.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Line Item", "FY2022", "FY2023"])
        writer.writerow(["Revenue", "1000", "1200"])
        writer.writerow(["COGS", "600", "700"])

    with open(csv_file, "rb") as f:
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.csv", f, "text/csv")},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["original_filename"] == "test.csv"
    assert data["document_type"] == "csv"
    return data["id"]


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/documents/99999")
    assert resp.status_code == 404


# ── Models API ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_models_empty(client: AsyncClient):
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_model(client: AsyncClient):
    resp = await client.post(
        "/api/v1/models",
        json={
            "name": "Test Model",
            "description": "A test model",
            "forecast_start": "FY2022",
            "forecast_end": "FY2026",
            "forecast_frequency": "annual",
            "currency": "USD",
            "unit_scale": "thousands",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Model"
    assert data["forecast_start"] == "FY2022"
    return data["id"]


@pytest.mark.asyncio
async def test_model_command(client: AsyncClient):
    # Create model first
    create_resp = await client.post(
        "/api/v1/models",
        json={
            "name": "Command Test Model",
            "forecast_start": "FY2022",
            "forecast_end": "FY2025",
            "forecast_frequency": "annual",
            "currency": "USD",
            "unit_scale": "thousands",
        },
    )
    assert create_resp.status_code == 201
    model_id = create_resp.json()["id"]

    # Send command
    resp = await client.post(
        "/api/v1/models/command",
        json={
            "command": "Build a cashflow forecast",
            "model_state_id": model_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "interpreted_as" in data


@pytest.mark.asyncio
async def test_model_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/models/99999")
    assert resp.status_code == 404


# ── Financial data API ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_financial_records_empty(client: AsyncClient):
    resp = await client.get("/api/v1/financial-data/records")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_financial_summary(client: AsyncClient):
    resp = await client.get("/api/v1/financial-data/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "periods" in data
    assert "income_statement" in data
    assert "balance_sheet" in data


# ── Scenarios ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_scenario(client: AsyncClient):
    # Create model
    create_resp = await client.post(
        "/api/v1/models",
        json={"name": "Scenario Test Model", "forecast_start": "FY2022", "forecast_end": "FY2025",
              "forecast_frequency": "annual", "currency": "USD", "unit_scale": "thousands"},
    )
    model_id = create_resp.json()["id"]

    # Create scenario
    resp = await client.post(
        f"/api/v1/models/{model_id}/scenarios",
        json={"name": "Bear Case", "description": "Downside scenario", "is_base": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bear Case"
