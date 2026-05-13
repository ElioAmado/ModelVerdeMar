from fastapi import APIRouter
from app.models.schemas import Island
from app.services.weather_service import get_weather

router = APIRouter()

@router.get("/{island}", summary="Tiempo actual en isla")
async def weather_by_island(island: Island):
    return await get_weather(island)
