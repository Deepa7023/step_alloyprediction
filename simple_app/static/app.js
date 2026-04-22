const form = document.querySelector("#quoteForm");
const fileInput = document.querySelector("#file");
const pickFile = document.querySelector("#pickFile");
const fileLabel = document.querySelector("#fileLabel");
const statusEl = document.querySelector("#status");
const emptyState = document.querySelector("#emptyState");
const processingState = document.querySelector("#processingState");
const results = document.querySelector("#results");
const reportFile = document.querySelector("#reportFile");
const reportEngine = document.querySelector("#reportEngine");
const geometryGrid = document.querySelector("#geometryGrid");
const costTotal = document.querySelector("#costTotal");
const costAlloy = document.querySelector("#costAlloy");
const costRange = document.querySelector("#costRange");
const costRangeNote = document.querySelector("#costRangeNote");
const costBreakdown = document.querySelector("#costBreakdown");
const costMeta = document.querySelector("#costMeta");

const money = (value) => new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2
}).format(value || 0);

const number = (value, unit = "") => `${new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2
}).format(value || 0)}${unit}`;

function errorMessage(data, response) {
  const parts = [];
  if (data.error) parts.push(data.error);
  if (data.detail) parts.push(data.detail);
  if (data.hint) parts.push(data.hint);
  if (!parts.length) parts.push(`Analysis failed with status ${response.status}.`);
  return parts.join(" ");
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function showProcessing() {
  emptyState.classList.add("hidden");
  results.classList.add("hidden");
  processingState.classList.remove("hidden");
}

function showResults() {
  emptyState.classList.add("hidden");
  processingState.classList.add("hidden");
  results.classList.remove("hidden");
}

pickFile.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  fileLabel.textContent = file ? file.name : "Upload CAD file";
  statusEl.textContent = file
    ? `${file.name} selected. Run estimation when ready.`
    : "Upload CAD. Alloy will be detected automatically when metadata is available.";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusEl.textContent = "Extracting CAD geometry and cost inputs...";
  showProcessing();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 120000);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: new FormData(form),
      signal: controller.signal
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(errorMessage(data, response));

    const dims = data.geometry.dimensions_mm || {};
    const validation = data.geometry.validation || {};
    const topology = data.geometry.topology || {};

    reportFile.textContent = data.file;
    reportEngine.textContent = `Geometry engine: ${data.engine}`;
    costTotal.textContent = money(data.cost.per_part_cost_inr);
    costAlloy.textContent = `${data.cost.alloy.replaceAll("_", " ")} - ${data.cost.alloy_source} - ${number(data.cost.weight_g, " g")}`;
    costRange.textContent = `${money(data.cost.range_inr.min)} - ${money(data.cost.range_inr.max)}`;
    costRangeNote.textContent = `Range includes ${data.cost.range_inr.percent}% metal and process variation.`;

    geometryGrid.innerHTML = [
      metric("Bounding box X", number(dims.x, " mm")),
      metric("Bounding box Y", number(dims.y, " mm")),
      metric("Bounding box Z", number(dims.z, " mm")),
      metric("Volume", number(data.geometry.volume_mm3 / 1000, " cm3")),
      metric("Surface area", number(data.geometry.surface_area_mm2 / 100, " cm2")),
      metric("Projected area", number(data.geometry.projected_area_mm2, " mm2")),
      metric("Faces", number(topology.faces)),
      metric("Integrity score", number(validation.integrity_score, "/100"))
    ].join("");

    costBreakdown.innerHTML = Object.entries(data.cost.breakdown_inr)
      .map(([label, value]) => `
        <div class="cost-line">
          <span>${label}</span>
          <strong>${money(value)}</strong>
        </div>
      `).join("");

    costMeta.innerHTML = [
      metric("Annual volume", number(data.cost.annual_volume)),
      metric("Tooling estimate", money(data.cost.tooling_estimate_inr)),
      metric("Detected alloy", data.cost.detected_alloy ? data.cost.detected_alloy.replaceAll("_", " ") : "Fallback"),
      metric("Quote basis", "Reference model")
    ].join("");

    statusEl.textContent = "Per-part HPDC estimate is ready.";
    showResults();
  } catch (error) {
    processingState.classList.add("hidden");
    emptyState.classList.remove("hidden");
    statusEl.textContent = error.name === "AbortError"
      ? "Analysis took too long. Try a smaller STL/STEP file or simplify the CAD before upload."
      : error.message;
  } finally {
    window.clearTimeout(timeout);
  }
});
