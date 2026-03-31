/* web/static/js/main.js — Frontend logic */

// ── State ──────────────────────────────────────────────────────────────────
let selectedFile = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const uploadZone    = document.getElementById("uploadZone");
const fileInput     = document.getElementById("fileInput");
const browseBtn     = document.getElementById("browseBtn");
const previewBox    = document.getElementById("previewBox");
const previewImg    = document.getElementById("previewImg");
const previewName   = document.getElementById("previewName");
const analyzeBtn    = document.getElementById("analyzeBtn");
const clearBtn      = document.getElementById("clearBtn");
const loadingOverlay= document.getElementById("loadingOverlay");
const statsBar      = document.getElementById("statsBar");
const resultsSection= document.getElementById("resultsSection");
const statusBadge   = document.getElementById("status-badge");

// ── Upload zone events ─────────────────────────────────────────────────────
browseBtn.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("click", (e) => {
  if (e.target !== browseBtn) fileInput.click();
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) selectFile(fileInput.files[0]);
});

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  if (e.dataTransfer.files[0]) selectFile(e.dataTransfer.files[0]);
});

function selectFile(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => { previewImg.src = e.target.result; };
  reader.readAsDataURL(file);
  previewName.textContent = file.name + "  (" + formatSize(file.size) + ")";
  previewBox.style.display = "flex";
  uploadZone.style.display = "none";
}

clearBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  previewBox.style.display = "none";
  uploadZone.style.display  = "block";
});

analyzeBtn.addEventListener("click", () => {
  if (!selectedFile) { showToast("Aucun fichier sélectionné.", "error"); return; }
  processFile(selectedFile);
});

// ── Process ────────────────────────────────────────────────────────────────
async function processFile(file) {
  showLoading(true);
  setStatus("● Analyse…", "#fbbf24");

  const steps = [
    { id: "step1", delay: 0 },
    { id: "step2", delay: 1200 },
    { id: "step3", delay: 2400 },
    { id: "step4", delay: 3600 },
  ];
  steps.forEach(({ id, delay }) =>
    setTimeout(() => activateStep(id), delay)
  );

  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", file.name.replace(/\.[^.]+$/, ""));

  try {
    const res  = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();

    showLoading(false);

    if (!res.ok || data.error) {
      showToast(`Erreur : ${data.error}`, "error");
      setStatus("● Erreur", "#ef4444");
      return;
    }

    displayResults(data);
    setStatus("● Prêt", "#86efac");
    showToast("Analyse terminée avec succès !", "success");
    loadHistory();

  } catch (err) {
    showLoading(false);
    showToast(`Erreur réseau : ${err.message}`, "error");
    setStatus("● Erreur", "#ef4444");
  }
}

// ── Display results ────────────────────────────────────────────────────────
function displayResults(data) {
  // Stats
  const { stats, zones, upload_url, result_url, processed_at } = data;
  animateCounter("statTotal",  stats.total_blocks);
  document.getElementById("statConf").textContent   = (stats.avg_confidence * 100).toFixed(1) + "%";
  animateCounter("statHeader", stats.zone_counts.header);
  animateCounter("statBody",   stats.zone_counts.body);
  animateCounter("statFooter", stats.zone_counts.footer);
  document.getElementById("statTime").textContent   = processed_at;

  statsBar.style.display = "grid";

  // Images
  document.getElementById("originalImg").src = upload_url;
  document.getElementById("resultImg").src   = result_url;
  const dlBtn  = document.getElementById("downloadBtn");
  dlBtn.href   = result_url;
  dlBtn.download = "resultat_ocr.png";

  // Zone blocks
  fillZone("headerBlocks", zones.header || []);
  fillZone("bodyBlocks",   zones.body   || []);
  fillZone("footerBlocks", zones.footer || []);

  resultsSection.style.display = "block";
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function fillZone(containerId, blocks) {
  const el = document.getElementById(containerId);
  if (!blocks.length) {
    el.innerHTML = '<div class="history-empty">Aucun texte détecté</div>';
    return;
  }
  el.innerHTML = blocks.map(b => {
    const conf      = b.confidence;
    const confClass = conf >= 95 ? "high" : conf >= 80 ? "medium" : "low";
    return `
      <div class="block-item">
        <span class="block-text">${escHtml(b.text)}</span>
        <span class="block-conf ${confClass}">${conf.toFixed(1)}%</span>
      </div>`;
  }).join("");
}

// ── Loading steps ──────────────────────────────────────────────────────────
function showLoading(show) {
  loadingOverlay.style.display = show ? "flex" : "none";
  if (show) {
    ["step1","step2","step3","step4"].forEach(id => {
      const el = document.getElementById(id);
      el.classList.remove("active","done");
    });
    activateStep("step1");
  }
}

function activateStep(id) {
  const steps = ["step1","step2","step3","step4"];
  const idx   = steps.indexOf(id);
  steps.forEach((sid, i) => {
    const el = document.getElementById(sid);
    if (i < idx)      { el.classList.add("done"); el.classList.remove("active"); }
    else if (i === idx){ el.classList.add("active"); el.classList.remove("done"); }
    else               { el.classList.remove("active","done"); }
  });
}

// ── History ────────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res   = await fetch("/api/history");
    const items = await res.json();
    const grid  = document.getElementById("historyGrid");

    if (!items.length) {
      grid.innerHTML = '<div class="history-empty">Aucune analyse effectuée</div>';
      return;
    }

    grid.innerHTML = items.map(item => `
      <div class="history-item" onclick="window.open('${item.url}','_blank')">
        <img src="${item.url}" alt="Résultat" loading="lazy"/>
        <div class="history-item-info">
          <div class="history-item-date">🕐 ${item.date}</div>
        </div>
      </div>`).join("");
  } catch (_) {}
}

// ── Utils ──────────────────────────────────────────────────────────────────
function animateCounter(id, target) {
  const el    = document.getElementById(id);
  const start = 0;
  const dur   = 600;
  const t0    = performance.now();
  const step  = (now) => {
    const p = Math.min((now - t0) / dur, 1);
    el.textContent = Math.round(start + (target - start) * easeOut(p));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

function formatSize(bytes) {
  return bytes > 1e6 ? (bytes/1e6).toFixed(1)+" MB"
       : bytes > 1e3 ? (bytes/1e3).toFixed(0)+" KB"
       : bytes+" B";
}

function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function setStatus(text, color) {
  statusBadge.textContent = text;
  statusBadge.style.color = color;
}

function showToast(msg, type = "") {
  const el = document.getElementById("toast");
  el.textContent  = msg;
  el.className    = `toast ${type} show`;
  setTimeout(() => el.classList.remove("show"), 3500);
}

// ── Init ───────────────────────────────────────────────────────────────────
loadHistory();
