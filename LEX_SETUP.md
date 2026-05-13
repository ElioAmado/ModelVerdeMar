# Configuración Amazon Lex V2 — Baleares Vacation Bot

## 1. Crear el bot en AWS Console

1. Ir a **Amazon Lex V2** → Create bot
   - Bot name: `BalearesVacationBot`
   - IAM permissions: Create a role
   - Idioma: **Español (España)**

---

## 2. Intents a crear

### Intent: `GetVacationRecommendations`
**Utterances de ejemplo:**
- ¿Qué puedo hacer en {Island}?
- Recomiéndame planes para {Island}
- ¿Qué hacer hoy en {Island}?
- Quiero ir a la {Category} en {Island}
- Planes para {Island} con lluvia
- ¿Qué ver en {Island}?

**Slots:**
| Nombre   | Tipo              | Prompt                        | Obligatorio |
|----------|-------------------|-------------------------------|-------------|
| Island   | AMAZON.City       | ¿En qué isla estás?           | Sí          |
| Category | Custom:ActivityType | ¿Qué tipo de plan buscas?   | No          |

---

### Intent: `GetWeatherInfo`
**Utterances:**
- ¿Qué tiempo hace en {Island}?
- ¿Lloverá en {Island}?
- Previsión meteorológica en {Island}
- ¿Cómo estará el tiempo en {Island}?

**Slots:**
| Nombre | Tipo        | Prompt              | Obligatorio |
|--------|-------------|---------------------|-------------|
| Island | AMAZON.City | ¿Para qué isla?     | Sí          |

---

### Intent: `ListPlaces`
**Utterances:**
- Muéstrame playas en {Island}
- ¿Qué museos hay en {Island}?
- Lugares de {Category} en {Island}
- Sitios turísticos en {Island}

**Slots:**
| Nombre   | Tipo              | Prompt                   | Obligatorio |
|----------|-------------------|--------------------------|-------------|
| Island   | AMAZON.City       | ¿En qué isla?            | Sí          |
| Category | Custom:ActivityType | ¿Qué tipo de lugar?    | No          |

---

## 3. Slot type personalizado: `ActivityType`

Crear slot type `ActivityType` con valores:
- playa (sinónimos: beach, playas, bañarse, nadar)
- cultura (sinónimos: museos, monumentos, historia, arte)
- naturaleza (sinónimos: senderismo, montaña, parques)
- gastronomia (sinónimos: restaurantes, comer, tapas)
- deportes (sinónimos: golf, náutica, ciclismo)
- familia (sinónimos: niños, parques, zoo)
- bienestar (sinónimos: spa, relax, wellness)
- ocio_nocturno (sinónimos: fiesta, discoteca, bares)

---

## 4. Fulfillment → Lambda / Webhook

En cada intent, en la sección **Fulfillment**:
1. Activar: "Use a Lambda function or a service endpoint"
2. Endpoint type: **HTTPS**
3. URL: `https://TU-FASTAPI-URL/api/lex/webhook`

O bien crear una Lambda que llame al endpoint FastAPI.

---

## 5. Canal Web Chat

1. En el bot, ir a **Channels** → **Web**
2. Copiar el snippet JavaScript generado
3. Añadirlo al `chatbot/index.html` en la sección del script
4. O usar directamente el iframe de Lex

### Snippet ejemplo (sustituye por el tuyo):
```html
<script>
  window.AmazonLexChatbot = {
    BotId: "TU_BOT_ID",
    BotAliasId: "TSTALIASID",
    LocaleId: "es_ES",
    Region: "eu-west-1"
  };
</script>
<script src="https://d1esqy3y27cn7.cloudfront.net/lex-web-ui/lex-web-ui-loader.min.js"></script>
```

---

## 6. Variables de sesión útiles

Puedes pasar la isla seleccionada como atributo de sesión desde el chatbot web:
```javascript
sessionAttributes: {
  selectedIsland: document.getElementById('islandSelect').value
}
```

Y en la Lambda/webhook, leerlo de `body.sessionState.sessionAttributes.selectedIsland`.
