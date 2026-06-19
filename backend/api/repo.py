# Stub routers — implemented in later phases.
# Imported by main.py; each returns 501 until the phase is built.

from fastapi import APIRouter

router = APIRouter()


@router.post("/upload")
async def upload_repo():
    return {"detail": "Phase 2 — not yet implemented"}


@router.get("/status/{job_id}")
async def repo_status(job_id: str):
    return {"detail": "Phase 2 — not yet implemented"}
