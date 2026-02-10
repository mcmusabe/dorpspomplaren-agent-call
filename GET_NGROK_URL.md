# Hoe krijg je de ngrok URL?

## Stap 1: Start ngrok (in een nieuwe terminal)

```bash
ngrok http 8000
```

## Stap 2: Kopieer de HTTPS URL

Je ziet output zoals:
```
Session Status                online
Account                       [jouw account]
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

**Kopieer de HTTPS URL:** `https://abc123.ngrok.io`

## Stap 3: Configureer in config.py

Open `config.py` en pas aan:
```python
WEBHOOK_URL = "https://abc123.ngrok.io"  # Vervang met jouw ngrok URL
```

## Stap 4: Deploy agent

```bash
python3 deploy_agent.py
```

## Test de webhook

Test of de webhook bereikbaar is via ngrok:
```bash
curl https://abc123.ngrok.io/health
```

Je zou moeten zien: `{"status":"ok","service":"dorpspomp-order-webhook"}`

## Belangrijk

- Laat ngrok draaien terwijl je de agent test
- Als je ngrok stopt, verandert de URL (tenzij je een betaald account hebt)
- Voor productie: gebruik een vaste URL (betaalde ngrok of cloud deployment)

