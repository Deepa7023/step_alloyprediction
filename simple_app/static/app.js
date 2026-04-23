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

function sheetRow(row) {
  const value = Number(row.value || 0);
  const isMoney = row.unit === "INR" || row.unit === "INR/kg" || row.unit === "INR/USD";
  const displayValue = row.unit === "set"
    ? `${value || row.quantity || 0} set`
    : isMoney
      ? money(value)
      : `${number(value)}${row.unit ? ` ${row.unit}` : ""}`;
  return `
    <div class="sheet-row">
      <span class="sheet-row-no">${row.row}</span>
      <span class="sheet-label">${row.label}</span>
      <span class="sheet-note">${row.note || row.code || ""}</span>
      <strong>${displayValue}</strong>
    </div>
  `;
}

function sheetSections(rows) {
  const grouped = rows.reduce((acc, row) => {
    acc[row.section] = acc[row.section] || [];
    acc[row.section].push(row);
    return acc;
  }, {});

  return Object.entries(grouped).map(([section, items]) => `
    <section class="sheet-section">
      <h3>${section}</h3>
      ${items.map(sheetRow).join("")}
    </section>
  `).join("");
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

    reportFile.textContent = data.file;
    reportEngine.textContent = `Geometry engine: ${data.engine}`;
    costTotal.textContent = money(data.cost.per_part_cost_inr);
    costAlloy.textContent = `${data.cost.alloy.replaceAll("_", " ")} - ${data.cost.alloy_source} - ${number(data.cost.weight_g, " g")}`;
    costRange.textContent = `${money(data.cost.range_inr.min)} - ${money(data.cost.range_inr.max)}`;
    costRangeNote.textContent = `Range includes ${data.cost.range_inr.percent}% metal and process variation.`;

    geometryGrid.innerHTML = [
      metric("Surface area", number(data.geometry.surface_area_mm2 / 100, " cm2")),
      metric("Projected area", number(data.geometry.projected_area_mm2, " mm2"))
    ].join("");

    const summaryBreakdown = data.cost.summary_breakdown_inr || {};
    const summaryHtml = Object.entries(summaryBreakdown)
      .map(([label, value]) => `
        <div class="cost-line">
          <span>${label}</span>
          <strong>${money(value)}</strong>
        </div>
      `).join("");

    const sheetHtml = sheetSections(data.cost.quote_sheet_rows || []);
    costBreakdown.innerHTML = `${summaryHtml}${sheetHtml}`;

    const constants = data.cost.spreadsheet_constants || {};
    costMeta.innerHTML = [
      metric("Detected alloy", data.cost.detected_alloy ? data.cost.detected_alloy.replaceAll("_", " ") : "Fallback"),
      metric("Tooling estimate", money(data.cost.tooling_estimate_inr)),
      metric("Metal price", money(constants.metal_price_inr_per_kg || 0) + "/kg"),
      metric("Runner + scrap", `${number(constants.runner_overflow_percent)}% + ${number(constants.scrap_percent)}%`),
      metric("Melting loss", `${number(constants.melting_process_loss_percent)}%`),
      metric("R&D / S&A / EBIT", `${number(constants.rnd_percent)}% / ${number(constants.sa_percent)}% / ${number(constants.ebit_percent)}%`),
      metric("Die cost", money(constants.die_cost_inr || 0)),
      metric("Die life", number(constants.die_life_shots, " shots")),
      metric("Gross melt", number(data.cost.gross_melt_kg, " kg")),
      metric("Yield factor", number(data.cost.yield_factor)),
      metric("Costing weight", number(data.cost.costing_weight_kg, " kg")),
      ...((data.cost.quote_sheet_rows || []).filter((row) => [58, 59, 60].includes(row.row)).map((row) =>
        metric(`Row ${row.row}`, `${row.label}: ${money(row.value)}`)
      ))
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
