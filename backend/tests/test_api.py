"""Integration tests for FastAPI endpoints using TestClient."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


# ── Test database ─────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_financial.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    import os
    if os.path.exists("./test_financial.db"):
        os.remove("./test_financial.db")


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Health check ──────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Documents ─────────────────────────────────────────────────────────────────

def test_list_documents_empty(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


def test_upload_invalid_extension(client):
    resp = client.post(
        "/api/documents/upload",
        files={"files": ("test.exe", b"binary content", "application/octet-stream")},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["uploaded"][0]["status"] == "rejected"


def test_upload_csv(client, tmp_path):
    csv_content = b"Item,FY2022,FY2023\nRevenue,1000000,1200000\nCOGS,400000,480000\n"
    resp = client.post(
        "/api/documents/upload",
        files={"files": ("financials.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["uploaded"][0]["status"] == "uploaded"


def test_get_document_not_found(client):
    resp = client.get("/api/documents/99999")
    assert resp.status_code == 404


# ── Extraction ────────────────────────────────────────────────────────────────

def test_list_line_items(client):
    resp = client.get("/api/extraction/line-items")
    assert resp.status_code == 200
    assert "line_items" in resp.json()


def test_line_items_summary(client):
    resp = client.get("/api/extraction/line-items/summary")
    assert resp.status_code == 200
    assert "summary" in resp.json()


# ── Modelling ─────────────────────────────────────────────────────────────────

def test_init_model_no_data(client):
    resp = client.post("/api/modelling/init", json={"period_type": "annual"})
    assert resp.status_code == 400  # No extracted data


def test_get_model_not_found(client):
    resp = client.get("/api/modelling/state?scenario=nonexistent")
    assert resp.status_code == 404


def test_command_no_model(client):
    resp = client.post(
        "/api/modelling/command",
        json={"command": "Model revenue using 15% CAGR", "scenario": "nomodel"},
    )
    assert resp.status_code == 400


def test_list_scenarios(client):
    resp = client.get("/api/modelling/scenarios")
    assert resp.status_code == 200
    assert "scenarios" in resp.json()


def test_command_history(client):
    resp = client.get("/api/modelling/commands")
    assert resp.status_code == 200
    assert "commands" in resp.json()


# ── Export ────────────────────────────────────────────────────────────────────

def test_export_no_model(client):
    resp = client.get("/api/export/excel?scenario=nomodel")
    assert resp.status_code == 404


def test_export_csv_no_model(client):
    resp = client.get("/api/export/csv?scenario=nomodel")
    assert resp.status_code == 404


def test_export_raw_data(client):
    resp = client.get("/api/export/raw-data/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
