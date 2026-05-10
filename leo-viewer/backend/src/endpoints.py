import csv
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from .__init__ import data_dir, logger
from .custom_types import GroundStation, GroundStationList, SatelliteList
from .logger import LogUtils
from .sat_locations import calculate_satellites

router = APIRouter()

FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"


@LogUtils.log_function
@router.get("/api/health")
def root(_: Request) -> str:
    return "LEO Viewer API"


@LogUtils.log_function
@router.get("/satellites")
def get_satellites(req: Request) -> SatelliteList:
    from datetime import datetime

    import pytz

    date_hour = req.query_params.get("date_hour")
    if date_hour:
        dt = datetime.strptime(date_hour, "%Y-%m-%d:%H")
        return calculate_satellites(pytz.UTC.localize(dt))
    return calculate_satellites()


@LogUtils.log_function
@router.get("/groundstations")
def get_groundstations(_: Request) -> GroundStationList:
    gs_file = data_dir / "ground_stations.csv"
    with open(gs_file, "r") as f:
        data = list(csv.DictReader(f, delimiter=";"))
        return [GroundStation(gs["name"], float(gs["lat"]), float(gs["long"])) for gs in data]


@LogUtils.log_function
@router.get("/api/predictions/city")
def get_dot_predictions(_: Request) -> FileResponse:
    dot_file = FRONTEND_PUBLIC / "dot_predictions.json"
    return FileResponse(dot_file, headers={"Cache-Control": "no-store"})


@LogUtils.log_function
@router.get("/api/predictions/grids")
def get_grid_predictions(req: Request) -> FileResponse:
    resolution = int(req.query_params.get("resolution", "2"))
    if resolution not in (2, 3, 4):
        resolution = 2
    hex_file = FRONTEND_PUBLIC / f"predicted_hex_res{resolution}.json"
    return FileResponse(hex_file, headers={"Cache-Control": "no-store"})
