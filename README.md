# AlloyQuote Studio

Advanced CAD-driven HPDC costing, alloy intelligence, market pricing, and quote explanation platform.

AlloyQuote Studio turns uploaded CAD files into manufacturing-ready cost intelligence. It extracts real geometry, infers manufacturing assumptions, calculates per-part HPDC cost, applies alloy and location pricing, visualizes the result, and lets users ask AlloyBot questions about both general manufacturing topics and the exact uploaded quote.

Default production branch: `adv`

Live deployment target used during development: `http://16.16.146.164`

---

## What It Does

- Upload CAD files such as STEP, STP, IGES, STL, OBJ, PLY, GLB, GLTF, 3MF, OFF, and DAE.
- Extract real geometry: bounding box, volume, surface area, projected area, topology, and integrity.
- Render an actual extracted STL mesh when available.
- Show real CAD diagnostics when a renderable mesh is unavailable, instead of fake placeholders.
- Infer HPDC assumptions such as alloy, annual volume, slider complexity, finishing/port cost, and plant location.
- Calculate material, machine/labour, tooling amortization, finishing, and total per-part cost.
- Apply market and location-aware alloy pricing.
- Display location-wise manufacturing price tables.
- Provide ECharts/D3 powered market intelligence and sparklines.
- Use AlloyBot as an efficient all-purpose assistant with uploaded-report context access.
- Deploy as a Dockerized full-stack app behind nginx on AWS EC2.

---

## Architecture

```txt
Browser
  |
  |  Next.js UI
  v
hpdc-frontend container
  |
  |  /api/* through same-origin nginx proxy
  v
hpdc-nginx container :80
  |
  |---- /      -> frontend:3000
  |
  |---- /api/ -> backend:5000
                 |
                 | FastAPI
                 v
              CAD + pricing + AI pipeline
```

Production services:

| Service | Container | Purpose |
|---|---|---|
| Frontend | `hpdc-frontend` | Next.js app, CAD report UI, market page, AlloyBot UI |
| Backend | `hpdc-backend` | FastAPI API, CAD analysis, cost engine, market data, AI chat |
| Reverse proxy | `hpdc-nginx` | Public port `80`, routes frontend and API traffic |
| Upload volume | `./uploads` | Stores uploaded CAD files for estimate history |

---

## Frontend

Location: `frontend/`

Stack:

- Next.js 16
- React 19
- TypeScript
- Framer Motion
- Three.js / React Three Fiber / Drei
- ECharts
- D3.js
- Axios
- Lucide icons

Important modules:

| File | Role |
|---|---|
| `frontend/app/components/AgentPane.tsx` | CAD upload, manufacturing inputs, geolocation plant selection |
| `frontend/app/components/DashboardHUD.tsx` | Main quote report and AlloyBot context assembly |
| `frontend/app/components/CADViewer.tsx` | Real mesh viewer and CAD diagnostics reader |
| `frontend/app/components/AlloyBot.tsx` | Floating chatbot UI and animated Pikachu-style assistant |
| `frontend/app/market/page.tsx` | Market intelligence page using ECharts and D3 |
| `frontend/app/components/AppShell.tsx` | App shell, navigation, theme handling |
| `frontend/app/globals.css` | Global design system, animations, bot effects, charts, dark/light styles |

Theme behavior:

- Light theme is default.
- Theme key: `hpdc-theme-v2`
- Users can still switch between light and dark modes.

---

## Backend

Location: `backend/`

Stack:

- FastAPI
- Uvicorn
- Pydantic
- CadQuery OCP / OpenCascade
- GMSH
- Trimesh
- NumPy
- Requests

Important modules:

| File | Role |
|---|---|
| `backend/main.py` | API routes, upload processing, chat endpoint, market endpoints |
| `backend/logic/cad_analyzer.py` | CAD parsing, mesh extraction, preview STL generation |
| `backend/logic/step_engine_ocp.py` | Precise STEP/IGES analysis with OCP/GMSH fallback |
| `backend/logic/cost_engine.py` | HPDC cost calculation |
| `backend/logic/prediction_engine.py` | Manufacturing assumption inference |
| `backend/logic/market_fetcher.py` | Alloy prices, FX rates, location price tables |
| `backend/logic/ai_integrations.py` | AI provider status and quote insight generation |
| `backend/logic/db.py` | Local estimate/history persistence |

---

## CAD Analysis Pipeline

```txt
Uploaded CAD
  |
  v
Format validation
  |
  v
STEP/STP material keyword scan
  |
  v
Precise B-Rep analysis with OCP
  |
  | fallback
  v
GMSH / Trimesh mesh analysis
  |
  v
Geometry traits
  |
  v
Preview mesh export when possible
```

Extracted traits:

- Dimensions in mm
- Volume
- Surface area
- Projected area
- Topology: solids, faces, edges, vertices
- Validation: manifold status and integrity score
- Base64 STL preview mesh when available

The UI does not show synthetic CAD placeholders. If the backend cannot return a renderable mesh, the CAD preview becomes a real diagnostics reader based on extracted values.

---

## Costing Pipeline

```txt
CAD traits
  |
  v
Manufacturing inference
  |
  v
Market and location pricing
  |
  v
HPDC cost model
  |
  v
Quote report + charts + AlloyBot context
```

The cost engine estimates:

- Material cost
- Machine and labour cost
- Die/tool amortization
- Finishing / port cost
- Tooling estimate
- Machine tonnage
- Cycle time
- Shots per hour
- Per-part total cost
- Expected cost fluctuation

---

## Market And Location Intelligence

The backend provides:

- Current base metal rates when configured.
- Reference pricing fallback when live provider data is unavailable.
- FX rates.
- Regional premiums.
- Freight estimates.
- Location-adjusted alloy price per kg.
- Location-wise price tables for manufacturing comparison.

The frontend supports location/geolocation driven selection and displays clearer dark/light readable country and plant data.

---

## AlloyBot

AlloyBot is powered by Groq through:

```txt
POST /api/chat
```

Current default model:

```txt
llama-3.3-70b-versatile
```

AlloyBot behavior:

- Works as an efficient all-purpose assistant.
- Answers general questions about engineering, CAD, HPDC, alloys, pricing, and manufacturing.
- When a quote exists, the frontend sends a compact uploaded-report context to the backend.
- The backend gives that context to Groq as the highest-priority source for file/quote questions.
- The bot can answer questions like:
  - What did I upload?
  - What alloy was used?
  - Why is this the unit cost?
  - Which geometry values were extracted?
  - What should I change to reduce cost?
  - Which assumptions were inferred?

Context sent to AlloyBot includes:

- Uploaded file name
- Geometry engine
- Dimensions
- Volume
- Surface area
- Projected area
- Topology
- Integrity score
- Alloy
- Cost breakdown
- Machine selection
- Location
- Market price
- Manufacturing assumptions
- Risks and recommendations

The chatbot UI includes a Pikachu-style animated assistant, context-active indicator, and electric thinking effects while it replies.

---

## AI And External Providers

Environment-backed providers:

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | AlloyBot and quote insight LLM access |
| `GROQ_MODEL` | Groq model name, default `llama-3.3-70b-versatile` |
| `HUGGINGFACE_TOKEN` | Future Hugging Face model/embedding/reranker integrations |
| `ZERVE_API_KEY` | Optional AI provider integration |
| `FIRECRAWL_API_KEY` | Web/data extraction workflows |
| `TINYFISH_API_KEY` | External intelligence/data provider |
| `METALS_API_KEY` | Live metals pricing if configured |

Recommended Hugging Face additions:

- `Qwen/Qwen3-4B-Instruct-2507` for fallback chat.
- `jinaai/jina-embeddings-v5-text-small-retrieval` for alloy/material document retrieval.
- `BAAI/bge-reranker-v2-m3` for reranking retrieved technical sources.

On a small EC2 instance, run large models through Hugging Face Inference API or endpoints, not locally.

---

## API Surface

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend health check |
| `POST` | `/api/agent/process` | Upload CAD and generate full quote report |
| `POST` | `/api/chat` | AlloyBot chat with optional uploaded-report context |
| `GET` | `/api/market-data` | Current metals, locations, FX, price tables |
| `GET` | `/api/market-data/fx-rates` | FX rates and currency labels |
| `GET` | `/api/ai/status` | AI provider status |
| `GET` | `/api/history` | Saved estimate history |
| `DELETE` | `/api/history/{estimate_id}` | Delete saved estimate |
| `GET` | `/api/market-history` | Market history |

---

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

For local frontend development, set:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

For production behind nginx, leave `NEXT_PUBLIC_API_URL` empty so the frontend uses same-origin `/api/*`.

---

## Docker Production

Production compose file:

```txt
docker-compose.prod.yml
```

Run:

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

Check containers:

```bash
docker ps
```

Check health:

```bash
curl http://localhost/health
curl http://localhost/api/health
```

The production nginx config routes:

```txt
/      -> frontend:3000
/api/  -> backend:5000
```

---

## AWS EC2 Deployment

Current deployment style:

- Amazon Linux EC2
- Docker + docker-compose
- Public nginx on port `80`
- Private frontend/backend containers
- SSH key: `metalsnew`
- App directory: `/home/ec2-user/app`

Typical deploy commands:

```bash
scp -i E:/metalsnew.pem -r backend frontend docker-compose.prod.yml nginx.conf ec2-user@16.16.146.164:/home/ec2-user/app/

ssh -i E:/metalsnew.pem ec2-user@16.16.146.164
cd /home/ec2-user/app
docker-compose -f docker-compose.prod.yml build backend frontend
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend frontend nginx
curl http://localhost/api/health
```

The app is exposed through:

```txt
http://16.16.146.164
```

---

## Git Workflow

Default branch:

```txt
adv
```

Recommended workflow:

```bash
git checkout adv
git pull origin adv
# make changes
npm run build --prefix frontend
python -m py_compile backend/main.py
git add .
git commit -m "Describe change"
git push origin adv
```

---

## Validation Checklist

Before deploying:

```bash
cd frontend
npm run build
```

```bash
python -m py_compile backend/main.py
```

After deploying:

```bash
curl http://16.16.146.164/health
curl http://16.16.146.164/api/health
```

Optional chat context smoke test:

```bash
curl -X POST http://16.16.146.164/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What file did I upload?","context":{"file":"demo.step","cost":{"total_unit_cost_usd":1.23},"market":{"alloy":"Aluminum_A380"}}}'
```

Expected behavior: AlloyBot references `demo.step`, the cost, and the alloy from the supplied context.

---

## Notes And Constraints

- Do not run large Hugging Face models locally on a `t3.small`; use hosted inference/endpoints.
- Keep `NEXT_PUBLIC_API_URL` empty in Docker production so nginx can proxy `/api`.
- CAD rendering is always based on actual extracted mesh data.
- If no renderable mesh is returned, the UI shows measured diagnostics instead of a fake part.
- The `METALS_API_KEY` should be set for live metals provider use; otherwise the app falls back to reference pricing.

