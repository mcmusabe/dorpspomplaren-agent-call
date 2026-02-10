# ngrok Authenticatie Setup

## Stap 1: Maak een gratis ngrok account

1. Ga naar: https://dashboard.ngrok.com/signup
2. Maak een gratis account (email + wachtwoord)
3. Bevestig je email

## Stap 2: Haal je authtoken op

1. Log in op: https://dashboard.ngrok.com/get-started/your-authtoken
2. Kopieer je authtoken (ziet eruit als: `2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz_5A6B7C8D9E0F`)

## Stap 3: Authenticeer ngrok

Run dit commando (vervang met jouw authtoken):

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN_HIER
```

## Stap 4: Test

```bash
ngrok http 8000
```

Je zou nu een URL moeten zien zoals: `https://abc123.ngrok.io`

## Alternatief: Cloudflare Tunnel (geen account nodig)

Als je geen ngrok account wilt maken, gebruik Cloudflare Tunnel:

```bash
# Installeer cloudflared
brew install cloudflared

# Start tunnel (geen account nodig!)
cloudflared tunnel --url http://localhost:8000
```

Dit geeft je direct een publieke URL zonder account.

