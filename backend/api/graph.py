from fastapi import APIRouter
router = APIRouter()

@router.get("/graph")
async def get_graph():
    return {"detail": "Phase 5 — not yet implemented"}
