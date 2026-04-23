const form = document.querySelector("#quoteForm");
const fileInput = document.querySelector("#file");
const pickFile = document.querySelector("#pickFile");
const fileLabel = document.querySelector("#fileLabel");
const alloyType = document.querySelector("#alloy_type");
const previewAlloy = document.querySelector("#previewAlloy");
const statusEl = document.querySelector("#status");
const emptyState = document.querySelector("#emptyState");
const processingState = document.querySelector("#processingState");
const results = document.querySelector("#results");
const geometryGrid = document.querySelector("#geometryGrid");
const costTotal = document.querySelector("#costTotal");
const costAlloy = document.querySelector("#costAlloy");
const heroCastingWeight = document.querySelector("#heroCastingWeight");
const costBreakdown = document.querySelector("#costBreakdown");
const cadPreview = document.querySelector("#cadPreview");
const cadPreviewLabel = document.querySelector("#cadPreviewLabel");

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

function drawCadPreview(dimensions) {
  const x = Math.max(Number(dimensions?.x) || 1, 1);
  const y = Math.max(Number(dimensions?.y) || 1, 1);
  const z = Math.max(Number(dimensions?.z) || 1, 1);
  const maxDim = Math.max(x, y, z);

  const sx = 150 * (x / maxDim);
  const sy = 110 * (y / maxDim);
  const sz = 95 * (z / maxDim);

  const ox = 150;
  const oy = 145;

  const frontBottomLeft = [ox - sx / 2, oy + sy / 2];
  const frontBottomRight = [ox + sx / 2, oy + sy / 2];
  const frontTopLeft = [ox - sx / 2, oy - sy / 2];
  const frontTopRight = [ox + sx / 2, oy - sy / 2];
  const depth = [sz * 0.55, -sz * 0.42];

  const backBottomLeft = [frontBottomLeft[0] + depth[0], frontBottomLeft[1] + depth[1]];
  const backBottomRight = [frontBottomRight[0] + depth[0], frontBottomRight[1] + depth[1]];
  const backTopLeft = [frontTopLeft[0] + depth[0], frontTopLeft[1] + depth[1]];
  const backTopRight = [frontTopRight[0] + depth[0], frontTopRight[1] + depth[1]];

  const points = (list) => list.map(([px, py]) => `${px},${py}`).join(" ");
  const line = (a, b, color, width = 2.5, dash = "") =>
    `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" ${dash ? `stroke-dasharray="${dash}"` : ""} />`;

  cadPreview.innerHTML = `
    <svg viewBox="0 0 320 280" role="img" aria-label="Lightweight CAD preview">
      <defs>
        <linearGradient id="cadFaceA" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="rgba(5,150,105,0.26)" />
          <stop offset="100%" stop-color="rgba(5,150,105,0.08)" />
        </linearGradient>
        <linearGradient id="cadFaceB" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="rgba(217,119,6,0.20)" />
          <stop offset="100%" stop-color="rgba(217,119,6,0.07)" />
        </linearGradient>
      </defs>
      <polygon points="${points([backTopLeft, backTopRight, frontTopRight, frontTopLeft])}" fill="url(#cadFaceA)" stroke="none"></polygon>
      <polygon points="${points([frontTopRight, backTopRight, backBottomRight, frontBottomRight])}" fill="url(#cadFaceB)" stroke="none"></polygon>
      <polygon points="${points([frontTopLeft, frontTopRight, frontBottomRight, frontBottomLeft])}" fill="rgba(6,78,59,0.06)" stroke="none"></polygon>
      ${line(frontTopLeft, frontTopRight, "#0f766e")}
      ${line(frontTopRight, frontBottomRight, "#0f766e")}
      ${line(frontBottomRight, frontBottomLeft, "#0f766e")}
      ${line(frontBottomLeft, frontTopLeft, "#0f766e")}
      ${line(backTopLeft, backTopRight, "#b45309")}
      ${line(backTopRight, backBottomRight, "#b45309")}
      ${line(backBottomRight, backBottomLeft, "#b45309", 2.2, "6 5")}
      ${line(backBottomLeft, backTopLeft, "#b45309", 2.2, "6 5")}
      ${line(frontTopLeft, backTopLeft, "#0f172a")}
      ${line(frontTopRight, backTopRight, "#0f172a")}
      ${line(frontBottomRight, backBottomRight, "#0f172a")}
      ${line(frontBottomLeft, backBottomLeft, "#0f172a", 2.2, "6 5")}
      <text x="24" y="30" fill="#064e3b" font-size="13" font-weight="700">X ${number(x, " mm")}</text>
      <text x="24" y="50" fill="#92400e" font-size="13" font-weight="700">Y ${number(y, " mm")}</text>
      <text x="24" y="70" fill="#0f172a" font-size="13" font-weight="700">Z ${number(z, " mm")}</text>
    </svg>
  `;
  cadPreviewLabel.textContent = `${number(x, " mm")} x ${number(y, " mm")} x ${number(z, " mm")}`;
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
    ? `Selected file: ${file.name}. Run estimation when ready.`
    : "Upload CAD. Alloy will be detected automatically when metadata is available.";
});

alloyType.addEventListener("change", () => {
  previewAlloy.textContent = alloyType.value === "auto"
    ? "Auto"
    : alloyType.options[alloyType.selectedIndex].textContent;
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

    costTotal.textContent = money(data.cost.per_part_cost_inr);
    costAlloy.textContent = `${data.cost.alloy.replaceAll("_", " ")} - ${data.cost.alloy_source}`;
    heroCastingWeight.textContent = number(data.cost.weight_g, " g");
    drawCadPreview(data.geometry.dimensions_mm || {});

    geometryGrid.innerHTML = [
      metric("Surface area", number(data.geometry.surface_area_mm2 / 100, " cm2")),
      metric("Projected area", number(data.geometry.projected_area_mm2, " mm2")),
      metric("Casting weight", number(data.cost.weight_g, " g"))
    ].join("");

    const summaryBreakdown = data.cost.summary_breakdown_inr || {};
    const summaryHtml = Object.entries(summaryBreakdown)
      .map(([label, value]) => `
        <div class="cost-line">
          <span>${label}</span>
          <strong>${money(value)}</strong>
        </div>
      `).join("");

    costBreakdown.innerHTML = summaryHtml;

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
