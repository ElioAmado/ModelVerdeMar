from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.models.schemas import Island, ActivityCategory
from app.services.data_loader import get_all_places

router = APIRouter()

@router.get("/", summary="Listar lugares")
async def list_places(
    island: Optional[Island] = Query(None),
    category: Optional[ActivityCategory] = Query(None),
    min_rating: Optional[float] = Query(None, ge=1, le=5),
):
    places = await get_all_places()
    if island:     places = [p for p in places if p.island == island]
    if category:   places = [p for p in places if p.category == category]
    if min_rating: places = [p for p in places if (p.google_rating or 0) >= min_rating]
    return places

@router.get("/{place_id}", summary="Detalle de lugar")
async def get_place(place_id: str):
    places = await get_all_places()
    for p in places:
        if p.id == place_id: return p
    raise HTTPException(404, f"Lugar '{place_id}' no encontrado")
