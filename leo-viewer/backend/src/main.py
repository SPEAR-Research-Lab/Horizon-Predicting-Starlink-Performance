import subprocess
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
    scripts = [
        "leo-viewer/backend/src/enrich_with_weather.py",
        "leo-viewer/backend/src/enrich_with_satellites.py",
        "leo-viewer/backend/src/predict.py",
        "leo-viewer/backend/src/predicts_json.py",
    ]
    for script in scripts:
        logger.info(f"Running: {script}")
        result = subprocess.run(["python", "-m", script.replace("/", ".").replace(".py", "")], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"{script} failed: {result.stderr}")
            return
        logger.info(f"{script} completed")


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

# Serve the paper website at root
if WEBSITE_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def serve_website():
        return FileResponse(WEBSITE_DIR / "index.html")

    app.mount("/website", StaticFiles(directory=str(WEBSITE_DIR)), name="website")
