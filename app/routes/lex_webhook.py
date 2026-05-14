
from fastapi import APIRouter, Request
from app.models.schemas import (
    LexWebhookRequest, Island, ActivityCategory
)
from app.services.weather_service import get_weather
from app.services.data_loader import get_all_places
from app.models.schemas import WeatherCondition, WeatherData
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

ISLAND_ALIASES = {
    "mallorca": Island.MALLORCA, "menorca": Island.MENORCA,
    "minorca": Island.MENORCA, "ibiza": Island.IBIZA,
    "eivissa": Island.IBIZA, "formentera": Island.FORMENTERA,
}

CATEGORY_ALIASES = {
    "playa": ActivityCategory.BEACH, "playas": ActivityCategory.BEACH,
    "beach": ActivityCategory.BEACH,
    "cultura": ActivityCategory.CULTURE, "museos": ActivityCategory.CULTURE,
    "monumento": ActivityCategory.CULTURE,
    "naturaleza": ActivityCategory.NATURE, "senderismo": ActivityCategory.NATURE,
    "gastronomia": ActivityCategory.GASTRONOMY, "comer": ActivityCategory.GASTRONOMY,
    "deportes": ActivityCategory.SPORTS, "deporte": ActivityCategory.SPORTS,
    "familia": ActivityCategory.FAMILY, "ninos": ActivityCategory.FAMILY,
    "spa": ActivityCategory.WELLNESS, "relax": ActivityCategory.WELLNESS,
    "bienestar": ActivityCategory.WELLNESS,
    "nocturno": ActivityCategory.NIGHTLIFE, "fiesta": ActivityCategory.NIGHTLIFE,
}

WEATHER_EMOJIS = {
    "soleado": "☀️", "parcialmente_nublado": "⛅", "nublado": "☁️",
    "ventoso": "💨", "lluvioso": "🌧️", "tormentoso": "⛈️",
}

RAINY_KEYWORDS = ["lluvia", "llueve", "llover", "llueva", "tormenta", "mal tiempo", "cubierto", "interior"]
WEATHER_KEYWORDS = ["tiempo", "clima", "meteorolog", "temperatura", "prediccion", "prevision"]
PLACE_KEYWORDS = ["lugares", "sitios", "lista", "muestra", "hay en"]


def _slot_value(slots, key):
    slot = slots.get(key)
    if not slot:
        return None
    v = slot.get("value", {}) or {}
    return v.get("interpretedValue") or v.get("originalValue")


def _make_response(session_state, messages):
    return {
        "sessionState": {**session_state, "dialogAction": {"type": "Close"}},
        "messages": [{"contentType": "PlainText", "content": m} for m in messages],
    }


def _detect_intent(text: str, lex_intent: str) -> str:
    t = text.lower()
    if any(k in t for k in RAINY_KEYWORDS):
        return "rainy"
    if any(k in t for k in WEATHER_KEYWORDS) and "hacer" not in t and "plan" not in t:
        return "weather"
    if any(k in t for k in PLACE_KEYWORDS):
        return "list"
    return "recommend"


@router.post("/webhook", summary="Amazon Lex V2 Fulfillment Webhook")
async def lex_webhook(request: Request, body: LexWebhookRequest):
    intent_name = body.sessionState.intent.name if body.sessionState.intent else "FallbackIntent"
    slots = body.sessionState.intent.slots if body.sessionState.intent else {}
    text = body.inputTranscript or ""
    model = request.app.state.model

    session_state_base = {
        "intent": {"name": intent_name, "state": "Fulfilled", "slots": slots}
    }

    isla_raw = _slot_value(slots, "Island") or "mallorca"
    island = ISLAND_ALIASES.get(isla_raw.lower(), Island.MALLORCA)
    cat_raw = _slot_value(slots, "Category")
    category = CATEGORY_ALIASES.get(cat_raw.lower()) if cat_raw else None

    detected = _detect_intent(text, intent_name)

    # ── LLUVIA: forzar condiciones lluviosas y recomendar solo indoor ─────────
    if detected == "rainy":
        all_places = await get_all_places()
        places = [p for p in all_places if p.island == island]

        # Forzar tiempo lluvioso para que el modelo puntúe bien los indoor
        fake_weather = WeatherData(
            island=island,
            temperature=18.0,
            feels_like=16.0,
            humidity=85,
            wind_speed=25.0,
            condition=WeatherCondition.RAINY,
            description="Lluvia — planes de interior recomendados",
            forecast=[],
        )

        # Priorizar lugares indoor, pero incluir también outdoor con buen score
        indoor_places = [p for p in places if p.indoor]
        if not indoor_places:
            indoor_places = places  # fallback si no hay indoor

        recs = model.predict(fake_weather, indoor_places, top_k=5)

        emoji = "🌧️"
        msg1 = f"{emoji} Con lluvia en {island.value.capitalize()}, te recomiendo planes de interior:"
        lines = []
        for i, r in enumerate(recs, 1):
            stars = "⭐" * round(r.place.google_rating or 4)
            lines.append(
                f"{i}. *{r.place.name}* ({r.place.category.value}) {stars}\n   {r.reason}"
            )
        msg2 = "\n".join(lines) if lines else "No encontré planes de interior registrados."
        return _make_response(session_state_base, [msg1, msg2])

    # ── TIEMPO ────────────────────────────────────────────────────────────────
    if detected == "weather" or intent_name == "GetWeatherInfo":
        weather = await get_weather(island)
        emoji = WEATHER_EMOJIS.get(weather.condition.value, "🌤️")
        msg = (
            f"{emoji} Tiempo actual en {island.value.capitalize()}:\n"
            f"• Condición: {weather.description}\n"
            f"• Temperatura: {weather.temperature}°C (sensación {weather.feels_like}°C)\n"
            f"• Humedad: {weather.humidity}%\n"
            f"• Viento: {weather.wind_speed} km/h"
        )
        if weather.forecast:
            msg += "\n\n📅 Próximos días:"
            for d in weather.forecast[:2]:
                msg += f"\n• {d['fecha']}: {d['condicion']}, {d['t_min']}-{d['t_max']}°C"
        return _make_response(session_state_base, [msg])

    # ── RECOMENDACIONES GENERALES ─────────────────────────────────────────────
    if detected in ("recommend", "list") or intent_name in ("GetVacationRecommendations", "ListPlaces"):
        weather = await get_weather(island)
        all_places = await get_all_places()
        places = [p for p in all_places if p.island == island]
        if category:
            places = [p for p in places if p.category == category]

        recs = model.predict(weather, places, top_k=4)
        emoji = WEATHER_EMOJIS.get(weather.condition.value, "🌤️")
        msg1 = (
            f"{emoji} Tiempo en {island.value.capitalize()}: {weather.condition.value}, "
            f"{weather.temperature}°C."
        )
        lines = [f"🏝️ Top recomendaciones para hoy:"]
        for i, r in enumerate(recs, 1):
            stars = "⭐" * round(r.place.google_rating or 4)
            lines.append(f"{i}. *{r.place.name}* ({r.place.category.value}) {stars}\n   {r.reason}")
        return _make_response(session_state_base, [msg1, "\n".join(lines)])

    # ── FALLBACK ──────────────────────────────────────────────────────────────
    help_msg = (
        "🏖️ Puedo ayudarte con:\n"
        "• ¿Qué puedo hacer en Mallorca hoy?\n"
        "• ¿Qué tiempo hace en Menorca?\n"
        "• Planes con lluvia en Ibiza\n"
        "• Muéstrame playas en Formentera\n\n"
        "¿Qué isla te interesa? 🌴"
    )
    return _make_response(session_state_base, [help_msg])
