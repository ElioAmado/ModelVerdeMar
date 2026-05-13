"""
Modelo Neuronal de Recomendación Vacacional
Arquitectura: Red neuronal feedforward con embeddings de lugar + features meteorológicas.
Entrenado con datos sintéticos enriquecidos con ratings de Google Maps y categorías CAIB.
"""

import numpy as np
import json
import os
import logging
from typing import List, Tuple, Dict, Optional
from app.models.schemas import (
    TouristPlace, WeatherData, WeatherCondition, ActivityCategory, PlaceRecommendation
)

logger = logging.getLogger(__name__)

# ── Constantes de arquitectura ─────────────────────────────────────────────────
WEATHER_DIM  = 8    # features meteorológicas
PLACE_DIM    = 12   # features de lugar
HIDDEN_DIM_1 = 64
HIDDEN_DIM_2 = 32
OUTPUT_DIM   = 1    # score de recomendación

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "places.json")


# ── Funciones de activación ────────────────────────────────────────────────────

def relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)

def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / e.sum()


# ── Encoders ──────────────────────────────────────────────────────────────────

WEATHER_ENCODING: Dict[str, int] = {
    WeatherCondition.SUNNY:          0,
    WeatherCondition.PARTLY_CLOUDY:  1,
    WeatherCondition.CLOUDY:         2,
    WeatherCondition.WINDY:          3,
    WeatherCondition.RAINY:          4,
    WeatherCondition.STORMY:         5,
}

CATEGORY_ENCODING: Dict[str, int] = {
    ActivityCategory.BEACH:      0,
    ActivityCategory.CULTURE:    1,
    ActivityCategory.NATURE:     2,
    ActivityCategory.GASTRONOMY: 3,
    ActivityCategory.SPORTS:     4,
    ActivityCategory.NIGHTLIFE:  5,
    ActivityCategory.FAMILY:     6,
    ActivityCategory.WELLNESS:   7,
}

ISLAND_ENCODING: Dict[str, int] = {
    "mallorca":   0,
    "menorca":    1,
    "ibiza":      2,
    "formentera": 3,
}

def encode_weather(weather: WeatherData) -> np.ndarray:
    """Convierte WeatherData en vector numérico normalizado."""
    cond_oh = np.zeros(6)
    cond_oh[WEATHER_ENCODING.get(weather.condition, 0)] = 1.0

    features = np.array([
        (weather.temperature - 10) / 30,       # norm. ~[-1, 1]
        weather.humidity / 100,
        min(weather.wind_speed / 60, 1.0),
    ])
    return np.concatenate([cond_oh, features])   # dim=9... slice to WEATHER_DIM


def encode_place(place: TouristPlace) -> np.ndarray:
    """Convierte TouristPlace en vector numérico."""
    cat_oh = np.zeros(8)
    cat_oh[CATEGORY_ENCODING.get(place.category, 0)] = 1.0

    island_oh = np.zeros(4)
    island_oh[ISLAND_ENCODING.get(place.island, 0)] = 1.0

    rating_norm = (place.google_rating or 3.5) / 5.0
    reviews_norm = min((place.google_reviews_count or 0) / 5000, 1.0)
    indoor_f = 1.0 if place.indoor else 0.0

    # Compatibility vector: 1 if weather condition is in ideal_weather
    # (se rellena dinámicamente en forward pass con weather)
    extra = np.array([rating_norm, reviews_norm, indoor_f])
    return np.concatenate([cat_oh, island_oh, extra])  # dim=15... slice to PLACE_DIM


class VacationRecommenderModel:
    """
    Red neuronal NumPy pura para recomendar lugares en Baleares.
    Entrenada con supervised learning sobre pares (weather, place) → score.
    """

    def __init__(self):
        self.trained = False
        self._init_weights()

    def _init_weights(self):
        """Inicialización He para pesos."""
        np.random.seed(42)
        input_dim = WEATHER_DIM + PLACE_DIM + 1  # +1 weather_match manual
        self.W1 = np.random.randn(input_dim,    HIDDEN_DIM_1) * np.sqrt(2 / input_dim)
        self.b1 = np.zeros(HIDDEN_DIM_1)
        self.W2 = np.random.randn(HIDDEN_DIM_1, HIDDEN_DIM_2) * np.sqrt(2 / HIDDEN_DIM_1)
        self.b2 = np.zeros(HIDDEN_DIM_2)
        self.W3 = np.random.randn(HIDDEN_DIM_2, OUTPUT_DIM)   * np.sqrt(2 / HIDDEN_DIM_2)
        self.b3 = np.zeros(OUTPUT_DIM)

    def _forward(self, x: np.ndarray) -> float:
        h1 = relu(x @ self.W1 + self.b1)
        h2 = relu(h1 @ self.W2 + self.b2)
        out = sigmoid(h2 @ self.W3 + self.b3)
        return float(out[0])

    def _build_input(self, weather: WeatherData, place: TouristPlace) -> np.ndarray:
        wv = encode_weather(weather)[:WEATHER_DIM]
        pv = encode_place(place)[:PLACE_DIM]
        weather_match = 1.0 if weather.condition in place.ideal_weather else 0.0
        return np.concatenate([wv, pv, [weather_match]])

    def _generate_training_data(
        self, places: List[TouristPlace]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Genera datos de entrenamiento sintéticos con reglas de dominio:
        - playas → tiempo soleado puntúa alto
        - cultura / gastronomía → cualquier tiempo puntúa bien
        - indoor → lluvia no penaliza
        - ratings Google altos → boost
        """
        X, y = [], []
        conditions = list(WeatherCondition)
        temperatures = [18, 22, 25, 28, 32, 35]
        humidities   = [40, 55, 65, 75, 85]
        winds        = [5, 10, 20, 35, 50]

        for place in places:
            for cond in conditions:
                for temp in temperatures:
                    for hum in [55, 75]:
                        w = WeatherData(
                            island=place.island,
                            temperature=temp,
                            feels_like=temp - 2,
                            humidity=hum,
                            wind_speed=15,
                            condition=cond,
                            description="",
                        )
                        score = self._rule_based_score(place, w)
                        x_vec = self._build_input(w, place)
                        X.append(x_vec)
                        y.append(score)

        return np.array(X), np.array(y)

    def _rule_based_score(self, place: TouristPlace, weather: WeatherData) -> float:
        """Score basado en reglas de dominio (ground truth para entrenamiento)."""
        score = 0.5

        # Match clima ideal
        if weather.condition in place.ideal_weather:
            score += 0.25

        # Penalizaciones por mal tiempo en exteriores
        if not place.indoor:
            if weather.condition == WeatherCondition.STORMY:
                score -= 0.35
            elif weather.condition == WeatherCondition.RAINY:
                score -= 0.20
            elif weather.condition == WeatherCondition.WINDY:
                if place.category == ActivityCategory.BEACH:
                    score -= 0.15

        # Bonus indoor con lluvia
        if place.indoor and weather.condition in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
            score += 0.20

        # Boost por ratings Google
        rating = place.google_rating or 3.5
        score += (rating - 3.5) / 10  # [-0.15, +0.15]

        # Temperatura ideal para playa: 24-32°C
        if place.category == ActivityCategory.BEACH:
            if 24 <= weather.temperature <= 32:
                score += 0.15
            elif weather.temperature < 18:
                score -= 0.25

        return float(np.clip(score, 0.0, 1.0))

    async def train(self, epochs: int = 300, lr: float = 0.01):
        """Entrena la red con descenso de gradiente (backprop manual)."""
        try:
            with open(DATA_PATH) as f:
                raw = json.load(f)
            places = [TouristPlace(**p) for p in raw]
        except Exception as e:
            logger.warning(f"No se pudieron cargar places.json: {e}. Usando datos mínimos.")
            places = _minimal_places()

        X, y = self._generate_training_data(places)
        logger.info(f"Entrenando con {len(X)} muestras durante {epochs} epochs...")

        for epoch in range(epochs):
            # Forward pass
            H1   = relu(X @ self.W1 + self.b1)          # (N, 64)
            H2   = relu(H1 @ self.W2 + self.b2)          # (N, 32)
            pred = sigmoid(H2 @ self.W3 + self.b3)[:, 0] # (N,)

            # Loss MSE
            diff = pred - y                               # (N,)
            loss = float(np.mean(diff ** 2))

            # Backprop
            dL_dpred = 2 * diff / len(y)                 # (N,)
            dL_dout  = dL_dpred * pred * (1 - pred)      # sigmoid'
            dL_dout  = dL_dout[:, None]                  # (N,1)

            dW3 = H2.T @ dL_dout
            db3 = dL_dout.sum(axis=0)

            dH2 = (dL_dout @ self.W3.T) * (H2 > 0)
            dW2 = H1.T @ dH2
            db2 = dH2.sum(axis=0)

            dH1 = (dH2 @ self.W2.T) * (H1 > 0)
            dW1 = X.T @ dH1
            db1 = dH1.sum(axis=0)

            # Gradient clipping
            for grad in [dW1, dW2, dW3]:
                np.clip(grad, -1.0, 1.0, out=grad)

            self.W1 -= lr * dW1;  self.b1 -= lr * db1
            self.W2 -= lr * dW2;  self.b2 -= lr * db2
            self.W3 -= lr * dW3;  self.b3 -= lr * db3

            if epoch % 50 == 0:
                logger.info(f"  Epoch {epoch:3d} | Loss: {loss:.4f}")

        self.trained = True
        logger.info("✅ Entrenamiento completado.")

    def predict(
        self, weather: WeatherData, places: List[TouristPlace], top_k: int = 10
    ) -> List[PlaceRecommendation]:
        """Devuelve los top_k lugares recomendados para las condiciones dadas."""
        results = []
        for place in places:
            x = self._build_input(weather, place)
            neural_score  = self._forward(x)
            weather_match = 1.0 if weather.condition in place.ideal_weather else max(0.2, 1.0 - 0.3 * (
                1 if weather.condition in [WeatherCondition.RAINY, WeatherCondition.STORMY] else 0
            ))
            rating_score  = (place.google_rating or 3.5) / 5.0
            combined      = 0.5 * neural_score + 0.3 * weather_match + 0.2 * rating_score

            reason = _build_reason(place, weather, neural_score, weather_match)

            results.append(PlaceRecommendation(
                place=place,
                score=round(combined, 3),
                weather_match=round(weather_match, 3),
                rating_score=round(rating_score, 3),
                neural_score=round(neural_score, 3),
                reason=reason,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_reason(place: TouristPlace, weather: WeatherData, ns: float, wm: float) -> str:
    cond = weather.condition
    cat  = place.category
    reasons = []

    if cond in place.ideal_weather:
        reasons.append(f"condiciones ideales ({cond.value}) para este lugar")
    if place.indoor and cond in [WeatherCondition.RAINY, WeatherCondition.STORMY]:
        reasons.append("actividad cubierta perfecta para el tiempo actual")
    if cat == ActivityCategory.BEACH and cond == WeatherCondition.SUNNY:
        reasons.append(f"temperatura de {weather.temperature}°C perfecta para la playa")
    if cat == ActivityCategory.CULTURE:
        reasons.append("la cultura no tiene mal tiempo")
    if (place.google_rating or 0) >= 4.5:
        reasons.append(f"valoración excelente en Google ({place.google_rating}⭐)")
    if not reasons:
        reasons.append("buena opción para las condiciones actuales")

    return "; ".join(reasons).capitalize() + "."


def _minimal_places() -> List[TouristPlace]:
    """Lugares mínimos de fallback si no hay JSON."""
    from app.models.schemas import Island
    return [
        TouristPlace(id="es_trenc", name="Playa Es Trenc", island=Island.MALLORCA,
                     category=ActivityCategory.BEACH, description="Playa virgen al sur de Mallorca",
                     latitude=39.35, longitude=2.97, google_rating=4.7, google_reviews_count=12000,
                     ideal_weather=[WeatherCondition.SUNNY, WeatherCondition.PARTLY_CLOUDY], indoor=False),
        TouristPlace(id="catedral_palma", name="Catedral de Palma", island=Island.MALLORCA,
                     category=ActivityCategory.CULTURE, description="Gótico medieval imponente",
                     latitude=39.567, longitude=2.648, google_rating=4.6, google_reviews_count=55000,
                     ideal_weather=list(WeatherCondition), indoor=True),
    ]
