const state = { front: null, back: null };

function setupDropZone(zoneId, inputId, previewId, key) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);

  const handleFile = (file) => {
    if (!file || !file.type.startsWith("image/")) return;
    state[key] = file;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
    zone.classList.add("has-image");
    updateButtonState();
  };

  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", (e) => handleFile(e.target.files[0]));

  ["dragenter", "dragover"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    })
  );
  zone.addEventListener("drop", (e) => handleFile(e.dataTransfer.files[0]));
}

function updateButtonState() {
  document.getElementById("grade-btn").disabled = !(state.front && state.back);
}

function showStatus(message, isError) {
  const el = document.getElementById("status-msg");
  el.textContent = message;
  el.hidden = !message;
  el.classList.toggle("error", Boolean(isError));
}

function renderMeasurements(m) {
  const container = document.getElementById("measurements");
  const tiles = [
    ["Centering L/R", `${m.centering_lr[0]} / ${m.centering_lr[1]}`],
    ["Centering T/B", `${m.centering_tb[0]} / ${m.centering_tb[1]}`],
    ["Corners", m.corners.toFixed(2)],
    ["Edges", m.edges.toFixed(2)],
    ["Surface", m.surface.toFixed(2)],
  ];
  container.innerHTML = tiles
    .map(
      ([label, value]) =>
        `<div class="measure-tile"><div class="label">${label}</div><div class="value">${value}</div></div>`
    )
    .join("");
}

const ACCENT_VARS = {
  PSA: "--psa",
  "Beckett (BGS)": "--bgs",
  CGC: "--cgc",
  TAG: "--tag",
  SGC: "--sgc",
  HGA: "--hga",
};

function renderResults(results) {
  const container = document.getElementById("result-cards");
  container.innerHTML = results
    .map((r) => {
      const subs = Object.entries(r.subgrades)
        .map(([k, v]) => `<li><span>${k.replace(/_/g, " ")}</span><span>${v}</span></li>`)
        .join("");
      const notes = r.notes.map((n) => `<div>${n}</div>`).join("");
      const accentVar = ACCENT_VARS[r.company] || "--accent";
      const slabAlt = `Mockup of the submitted card in a ${r.company} slab, estimated grade ${r.overall} ${r.label}`;
      return `
        <div class="result-card" style="--card-accent: var(${accentVar})">
          <img class="slab-image" src="data:image/png;base64,${r.slab_image_base64}" alt="${slabAlt}" loading="lazy" />
          <div class="company">${r.company}</div>
          <div class="grade">${r.overall}</div>
          <div class="label">${r.label}</div>
          <ul class="sub-list">${subs}</ul>
          <div class="notes">${notes}</div>
        </div>`;
    })
    .join("");
}

async function submitGrade() {
  const btn = document.getElementById("grade-btn");
  btn.disabled = true;
  showStatus("Analyzing card images...", false);
  document.getElementById("results").hidden = true;

  const formData = new FormData();
  formData.append("front", state.front);
  formData.append("back", state.back);

  try {
    const res = await fetch("/api/grade", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    const data = await res.json();
    renderMeasurements(data.measurements);
    renderResults(data.results);
    document.getElementById("results").hidden = false;
    showStatus("", false);
  } catch (err) {
    showStatus(err.message || "Something went wrong.", true);
  } finally {
    updateButtonState();
  }
}

setupDropZone("drop-front", "front-input", "front-preview", "front");
setupDropZone("drop-back", "back-input", "back-preview", "back");
document.getElementById("grade-btn").addEventListener("click", submitGrade);
