"""
Baleares Vacation Recommender - FastAPI Backend
Integra: Modelo Neuronal + AEMET + CAIB Dades Obertes + Google Maps
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from app.routes import recommendations, places, weather, lex_webhook
from app.services.model_service import VacationRecommenderModel
from app.services.data_loader import load_initial_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: cargar datos y entrenar modelo."""
    logger.info("🏖️  Iniciando Baleares Vacation Recommender...")
    await load_initial_data()
    model = VacationRecommenderModel()
    await model.train()
    app.state.model = model
    logger.info("✅ Modelo entrenado y listo.")
    yield
    logger.info("🛑 Apagando servidor...")


app = FastAPI(
    title="Baleares Vacation Recommender",
    description="API para recomendar actividades en Baleares según el tiempo meteorológico",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recomendaciones"])
app.include_router(places.router,          prefix="/api/places",          tags=["Lugares"])
app.include_router(weather.router,         prefix="/api/weather",         tags=["Meteorología"])
app.include_router(lex_webhook.router,     prefix="/api/lex",             tags=["Amazon Lex Webhook"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Baleares Vacation Recommender"}
