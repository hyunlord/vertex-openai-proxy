from fastapi import APIRouter

from app.runtime.controller import runtime_controller

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    snapshot = runtime_controller.snapshot()
    return {
        "status": "ok",
        "runtime_mode": snapshot["mode"],
        "degraded": snapshot["mode"] == "degraded",
        "adaptive_mode_enabled": snapshot["adaptive_mode_enabled"],
        "in_flight": snapshot["in_flight"],
    }
