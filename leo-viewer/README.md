# LEO Viewer

Real-time Starlink performance prediction viewer. Displays predicted latency and throughput on an interactive map using H3 hexagonal grids with zoom-adaptive resolution.

## Architecture

- **Frontend:** Vue 3 + MapLibre GL + h3-js (hexagon rendering)
- **Backend:** FastAPI serving predictions as JSON, with a scheduled pipeline for daily data refresh

### Prediction Pipeline

1. `generate_hex_centers.py` — generates hex center coordinates for H3 resolutions 2, 3, and 4
2. `enrich_with_weather.py` — fetches weather forecasts from Open-Meteo (temperature, precipitation, cloud cover, wind speed)
3. `enrich_with_satellites.py` — computes Starlink satellite density from TLE data
4. `predict.py` — runs ensemble models (Random Forest + Gradient Boosting) for latency and throughput
5. `predicts_json.py` — converts predictions to JSON with color coding for the frontend

### Zoom-Adaptive Hexagons

The grid map automatically adjusts hexagon resolution based on zoom level:
- **Zoom < 4:** H3 resolution 2 (~1,200 km hexagons)
- **Zoom 4-6:** H3 resolution 3 (~460 km hexagons)
- **Zoom > 6:** H3 resolution 4 (~175 km hexagons)

Higher-resolution data is lazy-loaded on demand and only visible hexagons are rendered for performance.

## Setup

### Backend

```bash
cd leo-viewer/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Model Files

The trained model files are too large for git. Place them in `leo-viewer/backend/models/`:
- `ensemble_model_filtered_percentile_0-75_3m_rf_weight_50_download_latency_ms.joblib`
- `ensemble_model_filtered_isolation_forest_0-75_11m_rf_weight_40_download_throughput_mbps.joblib`

#### Generate Prediction Data

```bash
cd leo-viewer/backend
python -m src.generate_hex_centers
python -m src.enrich_with_weather
python -m src.enrich_with_satellites
python -m src.predict
python -m src.predicts_json
```

#### Run Backend

```bash
cd leo-viewer/backend
uvicorn src.main:app --reload
```

### Frontend

```bash
cd leo-viewer/frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Views

- **Grid Map:** H3 hexagonal grid showing predicted network quality with zoom-adaptive resolution
- **Dot Map:** City-level point predictions

## Dependencies

### Backend
- FastAPI, uvicorn, pandas, scikit-learn, joblib
- h3, skyfield, sgp4, geopy (satellite and geo computations)
- requests (Open-Meteo API)

### Frontend
- Vue 3, MapLibre GL, h3-js, Turf.js
