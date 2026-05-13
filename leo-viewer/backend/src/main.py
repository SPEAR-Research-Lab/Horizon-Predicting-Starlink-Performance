"""
LEO Viewer Backend - FastAPI application.

Serves the paper website, API endpoints for predictions/satellites/ground stations,
and runs a daily prediction pipeline refresh.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pytz

from .__init__ import logger
from .endpoints import router as api_router

WEBSITE_DIR = Path(__file__).parent.parent.parent.parent / "website"


def run_prediction_pipeline() -> None:
    from .enrich_with_weather import enrich_weather, INPUT_FILES as WEATHER_INPUTS
    from .enrich_with_satellites import enrich_with_sat_density, INPUT_FILES as SAT_INPUTS
    from .predict import predict_file, INPUT_FILES as PREDICT_INPUTS
    from .predicts_json import export_hex_json, export_dot_json, RESOLUTION_FILES, DOT_PREDICTIONS_FILE
    from .__init__ import data_dir

    FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"

    try:
        for fname in WEATHER_INPUTS:
            inpath = data_dir / fname
            if inpath.exists():
                outpath = data_dir / fname.replace(".csv", "_weather.csv")
                enrich_weather(inpath, outpath)

        for fname in SAT_INPUTS:
            inpath = data_dir / fname
            if inpath.exists():
                outpath = data_dir / fname.replace("_weather.csv", "_weather_satellites.csv")
                enrich_with_sat_density(inpath, outpath)

        for fname in PREDICT_INPUTS:
            inpath = data_dir / fname
            if inpath.exists():
                outpath = data_dir / fname.replace(".csv", "_predictions.csv")
                predict_file(inpath, outpath)

        for res, fname in RESOLUTION_FILES.items():
            csv_path = data_dir / fname
            if csv_path.exists():
                export_hex_json(csv_path, FRONTEND_PUBLIC / f"predicted_hex_res{res}.json")

        dot_csv = data_dir / DOT_PREDICTIONS_FILE
        if dot_csv.exists():
            export_dot_json(dot_csv, FRONTEND_PUBLIC / "dot_predictions.json")

        logger.info("Prediction pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    scheduler.add_job(run_prediction_pipeline, CronTrigger(hour=4, minute=0))
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if WEBSITE_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def serve_website():
        return FileResponse(WEBSITE_DIR / "index.html")

    app.mount("/website", StaticFiles(directory=str(WEBSITE_DIR)), name="website")

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    @app.get("/app", include_in_schema=False)
    async def serve_app():
        return FileResponse(FRONTEND_DIST / "index.html")

    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="app")
