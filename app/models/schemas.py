from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class Island(str, Enum):
    MALLORCA   = "mallorca"
    MENORCA    = "menorca"
    IBIZA      = "ibiza"
    FORMENTERA = "formentera"

class WeatherCondition(str, Enum):
    SUNNY         = "soleado"
    CLOUDY        = "nublado"
    RAINY         = "lluvioso"
    WINDY         = "ventoso"
    STORMY        = "tormentoso"
    PARTLY_CLOUDY = "parcialmente_nublado"

class ActivityCategory(str, Enum):
    BEACH      = "playa"
    CULTURE    = "cultura"
    NATURE     = "naturaleza"
    GASTRONOMY = "gastronomia"
    SPORTS     = "deportes"
    NIGHTLIFE  = "ocio_nocturno"
    FAMILY     = "familia"
    WELLNESS   = "bienestar"

class TouristPlace(BaseModel):
    id:                   str
    name:                 str
    island:               Island
    category:             ActivityCategory
    description:          str
    latitude:             float
    longitude:            float
    google_rating:        Optional[float] = None
    google_reviews_count: Optional[int]   = None
    caib_category:        Optional[str]   = None
    caib_id:              Optional[str]   = None
    ideal_weather:        List[WeatherCondition] = []
    indoor:               bool = False
    image_url:            Optional[str] = None
    website:              Optional[str] = None

class WeatherData(BaseModel):
    island:      Island
    temperature: float
    feels_like:  float
    humidity:    int
    wind_speed:  float
    condition:   WeatherCondition
    description: str
    forecast:    List[dict] = []

class RecommendationRequest(BaseModel):
    island:              Island
    date:                Optional[str] = None
    category:            Optional[ActivityCategory] = None
    num_recommendations: int = Field(default=5, ge=1, le=20)

class PlaceRecommendation(BaseModel):
    place:         TouristPlace
    score:         float
    weather_match: float
    rating_score:  float
    neural_score:  float
    reason:        str

class RecommendationResponse(BaseModel):
    island:          Island
    weather:         WeatherData
    recommendations: List[PlaceRecommendation]
    generated_at:    str

class LexIntent(BaseModel):
    name:  str
    slots: dict = {}
    state: Optional[str] = None

class LexSessionState(BaseModel):
    intent:            Optional[LexIntent] = None
    sessionAttributes: dict = {}

class LexWebhookRequest(BaseModel):
    sessionId:       str
    inputTranscript: Optional[str] = None
    sessionState:    LexSessionState
    interpretations: Optional[list] = None

class LexMessage(BaseModel):
    contentType: str = "PlainText"
    content:     str

class LexWebhookResponse(BaseModel):
    sessionState: dict
    messages:     List[LexMessage]
