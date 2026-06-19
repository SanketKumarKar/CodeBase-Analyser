from fastapi import APIRouter
router = APIRouter()

@router.get("/history")
async def memory_history():
    return {"detail": "Phase 6 — not yet implemented"}
