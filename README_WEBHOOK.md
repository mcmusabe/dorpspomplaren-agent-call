# Order Webhook - FastAPI Email Service

FastAPI webhook die bestellingen ontvangt en via email verstuurt naar het bedrijf.

## Setup

### 1. Gmail App Password aanmaken

1. Ga naar je Google Account: https://myaccount.google.com/
2. Security → 2-Step Verification (moet aan staan)
3. App passwords → Select app: "Mail" → Select device: "Other" → "Dorpspomp Webhook"
4. Kopieer het gegenereerde wachtwoord (16 karakters)

### 2. Environment Variables instellen

Maak een `.env` bestand (of gebruik `.env.example` als template):

```bash
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
ORDER_TO_EMAIL=orders@dorpspomp.nl  # Optioneel: anders gebruikt het GMAIL_USER
```

### 3. Dependencies installeren

```bash
pip install fastapi uvicorn pydantic
```

Of gebruik requirements.txt:
```bash
pip install -r requirements.txt
```

## Run

### Development (met auto-reload)

```bash
python webhook_order.py
```

Of met uvicorn direct:
```bash
uvicorn webhook_order:app --reload --port 8000
```

### Production

```bash
uvicorn webhook_order:app --host 0.0.0.0 --port 8000
```

## Testen

### Unix/Mac

```bash
chmod +x test_order_webhook.sh
./test_order_webhook.sh
```

### Windows PowerShell

```powershell
.\test_order_webhook.ps1
```

### Manual curl (Unix/Mac)

```bash
curl -X POST http://127.0.0.1:8000/order \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Klant",
    "phone": "0612345678",
    "pickup_time": "18:20",
    "items": [
      {"name": "Friet medium", "qty": 2}
    ]
  }'
```

### Manual curl (Windows CMD)

```cmd
curl -X POST http://127.0.0.1:8000/order ^
  -H "Content-Type: application/json" ^
  -d "{\"customer_name\":\"Test\",\"phone\":\"06...\",\"pickup_time\":\"18:20\",\"items\":[{\"name\":\"Friet medium\",\"qty\":2}]}"
```

## API Endpoints

### POST /order

Ontvangt een bestelling en verstuurt deze via email.

**Request Body:**
```json
{
  "customer_name": "Jan Jansen",
  "phone": "0612345678",
  "pickup_time": "18:30",
  "items": [
    {
      "name": "Friet medium",
      "qty": 2,
      "notes": "Zonder zout"
    },
    {
      "name": "Frikandel",
      "qty": 1
    }
  ],
  "extra_notes": "Graag snel klaar"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "dorpspomp-order-webhook"
}
```

## Email Format

De email die verstuurd wordt ziet er zo uit:

```
Nieuwe BESTELLING (TEST)
Tijd: 2024-01-15 18:20:30

Naam: Jan Jansen
Telefoon: 0612345678
Afhaaltijd: 18:30

Items:
- 2x Friet medium
- 1x Frikandel

Opmerking: Graag snel klaar
```

## Deployment

### Lokale Development met ngrok

1. Start de webhook server:
```bash
python webhook_order.py
```

2. In andere terminal, start ngrok:
```bash
ngrok http 8000
```

3. Gebruik de ngrok URL (bijv. `https://abc123.ngrok.io`) in je Retell agent configuratie.

### Cloud Deployment

Deploy naar:
- **Render**: https://render.com
- **Railway**: https://railway.app
- **Fly.io**: https://fly.io
- **Heroku**: https://heroku.com

Zorg dat environment variables correct zijn ingesteld in je cloud platform.

## Integratie met Retell Agent

Wanneer je de volledige agent configuratie gebruikt (niet de minimale test setup), kun je deze webhook integreren:

1. Update `config.py`:
```python
WEBHOOK_URL = "https://your-webhook-url.com"
```

2. De agent kan dan bestellingen bevestigen via de `/order` endpoint.

## Troubleshooting

### "Missing GMAIL_USER or GMAIL_APP_PASSWORD"
- Controleer of `.env` bestand bestaat
- Controleer of environment variables correct zijn ingesteld
- Gebruik `python-dotenv` om `.env` te laden (optioneel)

### Email wordt niet verstuurd
- Controleer of Gmail App Password correct is
- Controleer spam folder
- Test met een simpele curl request eerst

### Port al in gebruik
- Wijzig poort in `webhook_order.py` of gebruik `--port 8001` met uvicorn

