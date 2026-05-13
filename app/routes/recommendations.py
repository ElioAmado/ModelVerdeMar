from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from app.models.schemas import RecommendationRequest
from app.services.weather_service import get_weather
from app.services.data_loader import get_all_places

router = APIRouter()

@router.post("/", summary="Obtener recomendaciones")
async def get_recommendations(request: Request, body: RecommendationRequest):
    model = request.app.state.model
    if not model.trained:
        raise HTTPException(503, "Modelo aun no entrenado.")
    weather = await get_weather(body.island)
    all_places = await get_all_places()
    places = [p for p in all_places if p.island == body.island]
    if body.category:
        places = [p for p in places if p.category == body.category]
    if not places:
        raise HTTPException(404, f"No hay lugares para {body.island.value}")
    recommendations = model.predict(weather, places, top_k=body.num_recommendations)
    return {"island": body.island, "weather": weather, "recommendations": recommendations, "generated_at": datetime.now().isoformat()}
