# Setup Order Webhook - Bestellingen via Email

## Probleem
De agent neemt bestellingen op maar verstuurt ze niet naar de webhook, dus geen email wordt verstuurd.

## Oplossing
1. Start de webhook server (lokaal of via ngrok)
2. Configureer de webhook URL in `config.py`
3. Deploy de agent opnieuw

## Stap 1: Start Webhook Server

### Optie A: Lokaal met ngrok (voor testen)

**Terminal 1 - Start webhook:**
```bash
python3 webhook_order.py
```

**Terminal 2 - Start ngrok:**
```bash
ngrok http 8000
```

Kopieer de HTTPS URL (bijv. `https://abc123.ngrok.io`)

### Optie B: Cloud deployment (voor productie)
Deploy `webhook_order.py` naar Render, Railway, of Heroku.

## Stap 2: Configureer Webhook URL

Open `config.py` en pas aan:

```python
# Webhook URL (optioneel - voor custom tools)
WEBHOOK_URL = "https://your-ngrok-url.ngrok.io"  # Of je cloud URL
```

**Voor lokaal met ngrok:**
```python
WEBHOOK_URL = "https://abc123.ngrok.io"  # Vervang met je ngrok URL
```

## Stap 3: Deploy Agent Opnieuw

```bash
python3 deploy_agent.py
```

## Stap 4: Test

1. Bel de agent
2. Plaats een test bestelling
3. Controleer of email aankomt op `orders@dorpspomp.nl`

## Hoe het werkt

1. Klant plaatst bestelling → Agent neemt op
2. Klant bevestigt → Agent gebruikt `send_order` tool
3. Tool stuurt POST naar `{WEBHOOK_URL}/order`
4. Webhook server ontvangt bestelling
5. Email wordt verstuurd naar `orders@dorpspomp.nl`

## Troubleshooting

### Geen email ontvangen?
- Controleer of webhook server draait: `curl http://localhost:8000/health`
- Controleer ngrok status (als lokaal)
- Controleer `.env` bestand met Gmail credentials
- Check spam folder

### Agent gebruikt tool niet?
- Controleer of `WEBHOOK_URL` correct is in `config.py`
- Deploy agent opnieuw: `python3 deploy_agent.py`
- Check Retell dashboard logs

### Webhook server errors?
- Controleer Gmail credentials in `.env`
- Test webhook handmatig: `./test_order_webhook.sh`
- Check server logs

