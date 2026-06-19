from fastapi import APIRouter
router = APIRouter()

@router.post("/query")
async def chat_query():
    return {"detail": "Phase 7 — not yet implemented"}
