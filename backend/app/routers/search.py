"""app/routers/search.py"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchRequest, SearchResponse
from app.services.search_service import run_search
from app.core.index_manager import IndexManager

router = APIRouter()

@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    if not IndexManager.is_ready():
        raise HTTPException(503, "Vector index not loaded. Run build_index.py first.")
    return await run_search(request)
