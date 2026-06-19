from fastapi import APIRouter
router = APIRouter()

@router.post("/vector")
async def vector_search():
    return {"detail": "Phase 4 — not yet implemented"}
