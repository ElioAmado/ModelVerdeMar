"""
Servicio meteorológico usando la API de AEMET OpenData.
Documentación: https://opendata.aemet.es/opendata/api/
"""

import httpx
import os
import logging
from datetime import datetime
from app.models.schemas import WeatherData, WeatherCondition, Island

logger = logging.getLogger(__name__)

AEMET_BASE = "https://opendata.aemet.es/opendata/api"
AEMET_KEY  = os.getenv("AEMET_API_KEY", "TU_CLAVE_AEMET_AQUI")

# Códigos de municipio AEMET para las capitales de Baleares
ISLAND_MUNICIPALITY: dict = {
    Island.MALLORCA:   "07040",  # Palma de Mallorca
    Island.MENORCA:    "07032",  # Maó
    Island.IBIZA:      "07026",  # Eivissa
    Island.FORMENTERA: "07024",  # Sant Francesc Xavier
}

# Mapeo de código SKY AEMET → WeatherCondition
SKY_CODE_MAP: dict = {
    "11": WeatherCondition.SUNNY,
    "12": WeatherCondition.PARTLY_CLOUDY,
    "13": WeatherCondition.PARTLY_CLOUDY,
    "14": WeatherCondition.CLOUDY,
    "15": WeatherCondition.CLOUDY,
    "16": WeatherCondition.CLOUDY,
    "17": WeatherCondition.STORMY,
    "23": WeatherCondition.PARTLY_CLOUDY,
    "24": WeatherCondition.CLOUDY,
    "25": WeatherCondition.RAINY,
    "26": WeatherCondition.RAINY,
    "27": WeatherCondition.STORMY,
    "33": WeatherCondition.PARTLY_CLOUDY,
    "34": WeatherCondition.CLOUDY,
    "35": WeatherCondition.RAINY,
    "36": WeatherCondition.RAINY,
    "43": WeatherCondition.CLOUDY,
    "44": WeatherCondition.RAINY,
    "45": WeatherCondition.RAINY,
    "46": WeatherCondition.STORMY,
    "51": WeatherCondition.RAINY,
    "52": WeatherCondition.RAINY,
    "53": WeatherCondition.STORMY,
    "54": WeatherCondition.STORMY,
    "61": WeatherCondition.RAINY,
    "62": WeatherCondition.STORMY,
    "63": WeatherCondition.STORMY,
    "71": WeatherCondition.STORMY,
    "72": WeatherCondition.STORMY,
    "73": WeatherCondition.STORMY,
    "74": WeatherCondition.STORMY,
    "81": WeatherCondition.STORMY,
    "82": WeatherCondition.STORMY,
    "83": WeatherCondition.STORMY,
}

SKY_DESCRIPTIONS: dict = {
    WeatherCondition.SUNNY:          "Cielo despejado y soleado",
    WeatherCondition.PARTLY_CLOUDY:  "Parcialmente nublado",
    WeatherCondition.CLOUDY:         "Cielo nublado",
    WeatherCondition.WINDY:          "Viento fuerte",
    WeatherCondition.RAINY:          "Lluvia",
    WeatherCondition.STORMY:         "Tormenta",
}


async def get_weather(island: Island) -> WeatherData:
    """
    Obtiene el tiempo actual y previsión de AEMET para una isla de Baleares.
    Si la API no está disponible, retorna datos simulados realistas.
    """
    muni_code = ISLAND_MUNICIPALITY[island]
    headers   = {"api_key": AEMET_KEY, "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1️⃣  Obtener URL de los datos
            meta_url = f"{AEMET_BASE}/prediccion/especifica/municipio/diaria/{muni_code}"
            meta_resp = await client.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            meta = meta_resp.json()

            if meta.get("estado") != 200:
                raise ValueError(f"AEMET error: {meta.get('descripcion')}")

            # 2️⃣  Descargar datos reales
            data_resp = await client.get(meta["datos"])
            data_resp.raise_for_status()
            forecast_list = data_resp.json()

            return _parse_aemet_response(island, forecast_list)

    except Exception as e:
        logger.warning(f"⚠️  AEMET no disponible ({e}). Usando datos simulados.")
        return _simulated_weather(island)


def _parse_aemet_response(island: Island, data: list) -> WeatherData:
    """Parsea la respuesta JSON de AEMET."""
    try:
        prediccion = data[0]["prediccion"]["dia"][0]
        today      = prediccion

        # Temperatura: máxima del día
        temps  = today.get("temperatura", {})
        t_max  = float(temps.get("maxima", 24))
        t_min  = float(temps.get("minima", 18))
        t_mean = (t_max + t_min) / 2

        # Humedad relativa
        hum_data = today.get("humedadRelativa", {})
        humidity = int(hum_data.get("maxima", 65))

        # Viento (velocidad en km/h)
        wind_data  = today.get("viento", [{}])
        wind_speed = float(wind_data[0].get("velocidad", 15)) if wind_data else 15.0

        # Estado del cielo
        sky_data   = today.get("estadoCielo", [{}])
        sky_code   = str(sky_data[0].get("value", "11")).replace("n", "") if sky_data else "11"
        condition  = SKY_CODE_MAP.get(sky_code, WeatherCondition.PARTLY_CLOUDY)

        # Si viento > 40 km/h, puede ser ventoso
        if wind_speed > 40 and condition not in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
            condition = WeatherCondition.WINDY

        # Previsión 3 días
        forecast = []
        for dia in data[0]["prediccion"]["dia"][:3]:
            t  = dia.get("temperatura", {})
            sk = dia.get("estadoCielo", [{}])
            sc = str(sk[0].get("value", "11")).replace("n", "") if sk else "11"
            forecast.append({
                "fecha":       dia.get("fecha", ""),
                "t_max":       t.get("maxima", "-"),
                "t_min":       t.get("minima", "-"),
                "condicion":   SKY_CODE_MAP.get(sc, WeatherCondition.PARTLY_CLOUDY).value,
            })

        return WeatherData(
            island=island,
            temperature=round(t_mean, 1),
            feels_like=round(t_mean - 1.5, 1),
            humidity=humidity,
            wind_speed=wind_speed,
            condition=condition,
            description=SKY_DESCRIPTIONS.get(condition, ""),
            forecast=forecast,
        )

    except Exception as e:
        logger.error(f"Error parseando AEMET: {e}")
        return _simulated_weather(island)


def _simulated_weather(island: Island) -> WeatherData:
    """Datos meteorológicos simulados cuando AEMET no está disponible."""
    month = datetime.now().month
    # Baleares tiene clima mediterráneo: veranos calurosos, inviernos suaves
    if 6 <= month <= 9:    # Verano
        temp, hum, wind = 29.0, 60, 12.0
        condition = WeatherCondition.SUNNY
    elif month in [4, 5, 10]:  # Primavera / Otoño
        temp, hum, wind = 22.0, 65, 18.0
        condition = WeatherCondition.PARTLY_CLOUDY
    else:                   # Invierno
        temp, hum, wind = 14.0, 75, 25.0
        condition = WeatherCondition.CLOUDY

    return WeatherData(
        island=island,
        temperature=temp,
        feels_like=temp - 2,
        humidity=hum,
        wind_speed=wind,
        condition=condition,
        description=f"[Simulado] {SKY_DESCRIPTIONS[condition]}",
        forecast=[
            {"fecha": "Mañana",    "t_max": temp + 1, "t_min": temp - 4, "condicion": condition.value},
            {"fecha": "Pasado",    "t_max": temp + 2, "t_min": temp - 3, "condicion": condition.value},
        ],
    )
