/* ============================================================
   app.js  —  Athletic VC Deal Processor
   ============================================================ */

(function () {
  "use strict";

  // ── Element refs ────────────────────────────────────────────
  const dropZone      = document.getElementById("drop-zone");
  const fileInput     = document.getElementById("file-input");
  const browseBtn     = document.getElementById("browse-btn");
  const fileList      = document.getElementById("file-list");
  const actionRow     = document.getElementById("action-row");
  const processBtn    = document.getElementById("process-btn");
  const btnLabel      = document.getElementById("btn-label");
  const btnSpinner    = document.getElementById("btn-spinner");
  const clearBtn      = document.getElementById("clear-btn");

  const statusSection = document.getElementById("status-section");
  const statusText    = document.getElementById("status-text");
  const progressTrack = document.getElementById("progress-track");
  const progressFill  = document.getElementById("progress-fill");

  const errorBanner   = document.getElementById("error-banner");
  const errorMessage  = document.getElementById("error-message");
  const errorClose    = document.getElementById("error-close");

  const warningBanner = document.getElementById("warning-banner");
  const warningList   = document.getElementById("warning-list");

  const emailBanner   = document.getElementById("email-banner");
  const emailStatusText = document.getElementById("email-status-text");

  const resultsSection = document.getElementById("results-section");
  const summaryFrame  = document.getElementById("summary-frame");
  const copyBtn       = document.getElementById("copy-btn");
  const printBtn      = document.getElementById("print-btn");
  const newDealBtn    = document.getElementById("new-deal-btn");

  // ── State ────────────────────────────────────────────────────
  let selectedFiles = []; // Array of File objects
  let lastHtml      = "";

  // ── Drag-and-drop ────────────────────────────────────────────
  ["dragenter", "dragover"].forEach(evt =>
    dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add("drag-over"); })
  );

  ["dragleave", "drop"].forEach(evt =>
    dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove("drag-over"); })
  );

  dropZone.addEventListener("drop", e => {
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  });

  // ── Browse button ────────────────────────────────────────────
  browseBtn.addEventListener("click", e => {
    e.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });

  fileInput.addEventListener("change", () => {
    addFiles(Array.from(fileInput.files));
    fileInput.value = ""; // allow re-selecting the same file
  });

  // ── File management ──────────────────────────────────────────
  function addFiles(files) {
    files.forEach(file => {
      // Avoid duplicates by name + size
      const dup = selectedFiles.some(f => f.name === file.name && f.size === file.size);
      if (!dup) selectedFiles.push(file);
    });
    renderFileList();
  }

  function renderFileList() {
    fileList.innerHTML = "";
    selectedFiles.forEach((file, idx) => {
      const li = document.createElement("li");
      li.className = "file-item";
      li.innerHTML = `
        <span class="file-icon">${fileIcon(file.name)}</span>
        <span class="file-name">${escHtml(file.name)}</span>
        <span class="file-size">${formatSize(file.size)}</span>
        <button class="file-remove" data-idx="${idx}" title="Remove" aria-label="Remove ${escHtml(file.name)}">&times;</button>
      `;
      fileList.appendChild(li);
    });

    actionRow.style.display = selectedFiles.length ? "flex" : "none";
  }

  fileList.addEventListener("click", e => {
    const btn = e.target.closest(".file-remove");
    if (!btn) return;
    const idx = parseInt(btn.dataset.idx, 10);
    selectedFiles.splice(idx, 1);
    renderFileList();
  });

  // ── Clear ────────────────────────────────────────────────────
  clearBtn.addEventListener("click", resetAll);

  function resetAll() {
    selectedFiles = [];
    renderFileList();
    hideSection(statusSection);
    hideSection(resultsSection);
    hideBanner(errorBanner);
    hideBanner(warningBanner);
    hideBanner(emailBanner);
    lastHtml = "";
    summaryFrame.srcdoc = "";
  }

  // ── Process ──────────────────────────────────────────────────
  processBtn.addEventListener("click", processDocuments);

  async function processDocuments() {
    if (!selectedFiles.length) return;

    hideBanner(errorBanner);
    hideBanner(warningBanner);
    hideBanner(emailBanner);
    hideSection(resultsSection);

    setProcessing(true);
    showSection(statusSection);
    setStatus("Uploading and extracting text from documents…", 20);

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append("files", f));

    let data;
    try {
      const resp = await fetch("/process", {
        method: "POST",
        body: formData,
      });

      // Advance progress bar while waiting for Claude
      setStatus("Analysing documents with Claude AI…", 55);

      data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || `Server error ${resp.status}`);
      }
    } catch (err) {
      setProcessing(false);
      hideSection(statusSection);
      showError(err.message || "An unexpected network error occurred.");
      return;
    }

    setStatus("Finalising summary…", 90);

    // Warnings (partial extraction)
    if (data.warnings && data.warnings.length) {
      showWarnings(data.warnings);
    }

    // Email status
    if (data.email_error) {
      showError(data.email_error, /* fatal= */ false);
    } else if (data.email_sent) {
      showEmailBanner("Summary emailed successfully to will@athletic.vc");
    }

    // Render result
    if (data.html_summary) {
      lastHtml = data.html_summary;
      summaryFrame.srcdoc = lastHtml;
      showSection(resultsSection);
    }

    setStatus("Done.", 100);
    setTimeout(() => { hideSection(statusSection); }, 800);
    setProcessing(false);
  }

  // ── Copy HTML ────────────────────────────────────────────────
  copyBtn.addEventListener("click", async () => {
    if (!lastHtml) return;
    try {
      await navigator.clipboard.writeText(lastHtml);
      copyBtn.textContent = "Copied!";
      setTimeout(() => { copyBtn.innerHTML = "&#128203; Copy HTML"; }, 2000);
    } catch {
      copyBtn.textContent = "Copy failed";
      setTimeout(() => { copyBtn.innerHTML = "&#128203; Copy HTML"; }, 2000);
    }
  });

  // ── Print ────────────────────────────────────────────────────
  printBtn.addEventListener("click", () => {
    if (!lastHtml) return;
    const win = window.open("", "_blank");
    win.document.write(lastHtml);
    win.document.close();
    win.focus();
    win.print();
  });

  // ── New deal ─────────────────────────────────────────────────
  newDealBtn.addEventListener("click", resetAll);

  // ── Error close ──────────────────────────────────────────────
  errorClose.addEventListener("click", () => hideBanner(errorBanner));

  // ── Helpers ──────────────────────────────────────────────────
  function setProcessing(active) {
    processBtn.disabled = active;
    btnLabel.style.display = active ? "none" : "inline";
    btnSpinner.style.display = active ? "inline-block" : "none";
  }

  function setStatus(text, pct) {
    statusText.textContent = text;
    if (pct !== undefined) {
      progressTrack.style.display = "block";
      progressFill.style.width = pct + "%";
    }
  }

  function showError(msg, fatal = true) {
    errorMessage.textContent = msg;
    showBanner(errorBanner);
    if (fatal) {
      hideSection(statusSection);
    }
  }

  function showWarnings(warnings) {
    warningList.innerHTML = "";
    warnings.forEach(w => {
      const li = document.createElement("li");
      li.textContent = w;
      warningList.appendChild(li);
    });
    showBanner(warningBanner);
  }

  function showEmailBanner(msg) {
    emailStatusText.textContent = msg;
    showBanner(emailBanner);
  }

  function showSection(el) { el.style.display = "block"; }
  function hideSection(el) { el.style.display = "none";  }
  function showBanner(el)  { el.style.display = "flex";  }
  function hideBanner(el)  { el.style.display = "none";  }

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function fileIcon(name) {
    const ext = name.split(".").pop().toLowerCase();
    const map = {
      pdf: "📄", docx: "📝", doc: "📝",
      xlsx: "📊", xls: "📊", csv: "📊",
      txt: "📃", md: "📃",
    };
    return map[ext] || "📁";
  }

})();
