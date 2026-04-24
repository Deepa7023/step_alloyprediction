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

let o3dViewer = null;

function drawCadPreview(dimensions, fileName = "", savedFilename = "") {
  cadPreviewLabel.textContent = fileName
    ? `${fileName} · Real 3D Preview`
    : `Waiting for CAD file`;

  if (!savedFilename) return;

  const fileUrl = `/uploads/${savedFilename}`;
  
  if (!o3dViewer) {
    cadPreview.innerHTML = '';
    OV.SetExternalLibLocation('https://cdn.jsdelivr.net/npm/online-3d-viewer@0.14.0/libs');
    OV.Init3DViewerElements();
    o3dViewer = new OV.EmbeddedViewer(cadPreview, {
        camera: new OV.Camera (
            new OV.Coord3D (2.0, 2.0, 2.0),
            new OV.Coord3D (0.0, 0.0, 0.0),
            new OV.Coord3D (0.0, 1.0, 0.0)
        ),
        backgroundColor: new OV.RGBAColor (248, 250, 252, 255),
        edgeSettings: new OV.EdgeSettings (true, new OV.RGBColor (15, 23, 42), 1)
    });
  }

  o3dViewer.LoadModelFromUrlList([fileUrl]);
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
    drawCadPreview(
      data.geometry.dimensions_mm || {},
      data.file || "",
      data.saved_filename || ""
    );

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
