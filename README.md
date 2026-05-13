# 🏖️ Baleares Vacation Recommender

Sistema completo de recomendación vacacional para las Islas Baleares con IA, tiempo real y chatbot.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CHATBOT WEB                               │
│   HTML/CSS/JS  ←──────────────────────────────────────────────  │
│   (chatbot/index.html)                                           │
└──────────────────────┬──────────────────────────────────────────┘
                       │  HTTPS
           ┌───────────▼──────────────┐
           │     AMAZON LEX V2         │
           │  (NLU + Slot filling)     │
           │  es_ES                    │
           └───────────┬──────────────┘
                       │  Webhook (HTTPS POST)
┌──────────────────────▼──────────────────────────────────────────┐
│                   FASTAPI BACKEND                                 │
│                                                                  │
│  /api/lex/webhook          ← Fulfillment de Amazon Lex          │
│  /api/recommendations/     ← Recomendaciones IA                 │
│  /api/weather/{island}     ← Tiempo AEMET                       │
│  /api/places/              ← CRUD lugares turísticos            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MODELO NEURONAL (NumPy)                    │    │
│  │                                                         │    │
│  │  Input (21 dims):                                       │    │
│  │    weather_condition (6) + temp + hum + wind (3)        │    │
│  │    + category (8) + island (4) + rating + reviews (2)   │    │
│  │    + weather_match (1)                                  │    │
│  │                                                         │    │
│  │  Arquitectura: FC(21→64) → ReLU → FC(64→32)             │    │
│  │              → ReLU → FC(32→1) → Sigmoid                │    │
│  │                                                         │    │
│  │  Training: SGD + Backprop manual, 300 epochs            │    │
│  │  Ground truth: reglas de dominio meteorológicas         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │  AEMET API   │   │  CAIB Dades  │   │  Google Maps     │    │
│  │  (tiempo     │   │  Obertes     │   │  Places API      │    │
│  │   real)      │   │  (lugares)   │   │  (ratings)       │    │
│  └──────────────┘   └──────────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Estructura de archivos

```
baleares-vacation/
├── app/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── neural_model.py        # Red neuronal NumPy
│   ├── routes/
│   │   ├── recommendations.py     # POST /api/recommendations/
│   │   ├── places.py              # GET /api/places/
│   │   ├── weather.py             # GET /api/weather/{island}
│   │   └── lex_webhook.py         # POST /api/lex/webhook
│   ├── services/
│   │   ├── weather_service.py     # Cliente AEMET
│   │   ├── data_loader.py         # CAIB + Google Maps loader
│   │   └── model_service.py       # Wrapper modelo
│   └── data/
│       └── places.json            # Cache lugares (generado en startup)
├── chatbot/
│   └── index.html                 # Interfaz web del chatbot
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── LEX_SETUP.md                   # Guía configuración Amazon Lex
```

## Instalación y arranque

### Local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env
# → Editar .env con tus claves AEMET y Google Maps

# 3. Arrancar FastAPI
uvicorn app.main:app --reload

# 4. Abrir el chatbot
# Abrir chatbot/index.html en el navegador
# o servir con: python -m http.server 3000 --directory chatbot
```

### Docker

```bash
docker-compose up --build
# API:     http://localhost:8000
# Chatbot: http://localhost:80
# Docs:    http://localhost:8000/docs
```

## Claves de API necesarias

### AEMET OpenData (gratuita)
1. Ir a https://opendata.aemet.es/centrodedescargas/inicio
2. Solicitar API Key (automático, llega por email)
3. Añadir en `.env`: `AEMET_API_KEY=tu_clave`

### Google Maps Places API
1. Consola: https://console.cloud.google.com/
2. Activar "Places API"
3. Crear credencial → API Key
4. Añadir en `.env`: `GOOGLE_MAPS_API_KEY=tu_clave`
> ⚠️ Google Maps es de pago. El sistema funciona sin ella (usa ratings estáticos).

### Amazon Lex V2
Ver `LEX_SETUP.md` para la configuración completa del bot.

## Endpoints API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/recommendations/` | Recomendaciones IA según tiempo |
| GET | `/api/weather/{island}` | Tiempo actual AEMET |
| GET | `/api/places/` | Listar lugares turísticos |
| GET | `/api/places/{id}` | Detalle de un lugar |
| POST | `/api/lex/webhook` | Fulfillment Amazon Lex V2 |
| GET | `/docs` | Swagger UI |

## Ejemplo de uso

```bash
# Recomendaciones para Mallorca hoy
curl -X POST http://localhost:8000/api/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{"island": "mallorca", "num_recommendations": 5}'

# Tiempo en Menorca
curl http://localhost:8000/api/weather/menorca

# Playas de Ibiza
curl "http://localhost:8000/api/places/?island=ibiza&category=playa"
```

## Funcionamiento del modelo neuronal

1. **Datos**: 26 lugares turísticos de Baleares (CAIB + estáticos) con categoría, coordenadas, rating Google
2. **Features de entrada** (21 dimensiones):
   - Condición meteorológica (one-hot × 6)
   - Temperatura, humedad, viento (3)
   - Categoría de lugar (one-hot × 8)
   - Isla (one-hot × 4)
   - Rating Google normalizado, nº reseñas normalizado (2)
   - Match clima ideal (1 binario)
3. **Arquitectura**: 21 → 64 (ReLU) → 32 (ReLU) → 1 (Sigmoid)
4. **Entrenamiento**: ~3.000 pares sintéticos generados con reglas de dominio (sol+playa=alto, lluvia+interior=alto, etc.)
5. **Score final**: 50% modelo neuronal + 30% match clima + 20% rating Google

## Fuentes de datos

- **AEMET OpenData**: https://opendata.aemet.es — tiempo real gratuito
- **CAIB Dades Obertes**: https://catalegdades.caib.cat — catálogo turístico oficial Baleares
- **Google Maps Places API**: ratings y número de reseñas de turistas reales
