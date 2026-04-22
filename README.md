# STEP Alloy Prediction Simple

Simple Flask app for CAD geometry extraction and HPDC per-part costing.

This branch intentionally removes the advanced dashboard pieces:

- Agent-decided assumptions
- CAD preview
- Machine and market section
- Cost and market charts
- Location-wise price table
- AI quote notes
- Price source
- Chatbot

## Kept Main Sections

1. Geometry Extracted From CAD
2. Per Part Cost Breakdown (₹)

## Local Run

```bash
pip install -r requirements.txt
python -m simple_app.app
```

Open:

```txt
http://localhost:5000
```

## Render Deploy

Render can use the included `render.yaml`, or these settings:

```txt
Build command: pip install -r requirements.txt
Start command: gunicorn simple_app.app:app --bind 0.0.0.0:$PORT
```

Health check:

```txt
/api/health
```

## App Structure

```txt
simple_app/
  app.py
  logic/
    cad_analyzer.py
    cost_engine.py
    step_engine_ocp.py
  static/
    app.js
    styles.css
  templates/
    index.html
```
