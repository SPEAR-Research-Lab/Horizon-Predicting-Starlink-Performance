from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from .logger import LogUtils

router = APIRouter()

FRONTEND_PUBLIC = Path(__file__).parent.parent.parent / "frontend" / "public"


@LogUtils.log_function
@router.get("/api/health")
def root(_: Request) -> str:
    return "LEO Viewer API"


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
