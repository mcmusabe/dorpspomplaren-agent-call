# ngrok Installatie Instructies

## Optie 1: Homebrew (Aanbevolen voor Mac)

```bash
brew install ngrok/ngrok/ngrok
```

## Optie 2: Direct Download

1. Ga naar: https://ngrok.com/download
2. Download voor macOS
3. Pak uit en verplaats naar `/usr/local/bin`:
```bash
# Na downloaden:
unzip ngrok.zip
sudo mv ngrok /usr/local/bin/
```

## Optie 3: Via npm (als je Node.js hebt)

```bash
npm install -g ngrok
```

## Na installatie

1. Maak een gratis account op https://ngrok.com
2. Kopieer je authtoken
3. Authenticeer:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

## Gebruik

```bash
ngrok http 8000
```

Dit geeft je een publieke URL zoals: `https://abc123.ngrok.io`

## Alternatief: Cloudflare Tunnel (gratis, geen account nodig)

Als je geen ngrok wilt gebruiken:

```bash
# Installeer cloudflared
brew install cloudflared

# Start tunnel
cloudflared tunnel --url http://localhost:8000
```

## Alternatief: Lokale test zonder ngrok

Voor lokale test kun je ook:
1. Webhook server lokaal draaien
2. Retell webhook URL tijdelijk leeg laten
3. Test bestellingen handmatig via `./test_order_webhook.sh`

