# De Dorpspomp & Dieks IJssalon - Retell AI Voice Agent

Voice AI agent voor het aannemen van telefoontjes bij De Dorpspomp & Dieks IJssalon in Laren (Gelderland).

## Functies

De agent kan helpen met:
1. **Openingstijden** - Informatie over wanneer het bedrijf open is
2. **Adres & Locatie** - Waar het bedrijf zich bevindt
3. **Menu & Prijzen** - Informatie over het menu
4. **Afhaalbestellingen** - Bestellingen opnemen voor afhalen
5. **Online Bestellen** - Uitleg over online bestellen
6. **Doorverbinden** - Doorverbinden naar medewerker wanneer nodig

## Agent Persona

- **Naam**: Dorpspomp telefoonassistent
- **Taal**: Nederlands (standaard)
- **Spreekstijl**: Vriendelijk, kort, duidelijk
- **Maximaal 1 vraag tegelijk**
- **Nooit gokken of aannames maken**
- **Natuurlijk, rustig en professioneel**

## Openingstijden

- **Maandag & dinsdag**: Gesloten
- **Woensdag & donderdag**: 11:30 – 19:30
- **Vrijdag t/m zondag**: 11:30 – 20:00

## Adres

Holterweg 1, Laren (Gld)

## Installatie

1. Installeer dependencies:
```bash
pip install -r requirements.txt
```

2. Configureer de API key in `config.py`:
```python
RETELL_API_KEY = "key_f9c58d68e11080d312710669ad1c"
```

3. (Optioneel) Configureer webhook URL voor custom tools:
```python
WEBHOOK_URL = "https://your-webhook-url.com/retell"
```

## Quick Start

### Basis Deployment (zonder webhook)

1. Installeer dependencies:
```bash
pip install -r requirements.txt
```

2. Deploy de agent:
```bash
python deploy_agent.py
```

De agent werkt nu zonder webhook - menu en bestellingen worden via natuurlijke taal afgehandeld.

### Deployment met Webhook (aanbevolen voor productie)

1. Start de webhook server (lokaal of deploy naar cloud):
```bash
python webhook_example.py
```

2. Gebruik een tool zoals [ngrok](https://ngrok.com/) om de lokale server publiek toegankelijk te maken:
```bash
ngrok http 5000
```

3. Update `config.py` met de webhook URL:
```python
WEBHOOK_URL = "https://your-ngrok-url.ngrok.io"
```

4. Deploy de agent:
```bash
python deploy_agent.py
```

## Deployment

Run het deployment script:
```bash
python deploy_agent.py
```

Dit script zal:
1. Een Retell LLM aanmaken/updaten met de juiste prompts en state machine
2. Een agent aanmaken/updaten met Nederlandse voice configuratie
3. Alle tools en states configureren

## State Machine

De agent gebruikt een state machine met de volgende states:

- **S0_GREETING**: Begroeting en routing
- **S1_INFO_ROUTER**: Informatie vragen (openingstijden, adres, menu)
- **S2_ORDER_START**: Start bestelling opnemen
- **S3_TAKE_ORDER**: Items opnemen
- **S4_MENU_HELP**: Hulp bij menu keuze
- **S5_RECAP**: Samenvatting geven
- **S6_CONFIRM**: Bestelling bevestigen
- **S7_HANDOFF**: Doorverbinden naar medewerker

## Tools

De agent heeft toegang tot de volgende tools (indien webhook geconfigureerd):

- `get_business_info` - Bedrijfsinformatie ophalen
- `get_hours` - Openingstijden voor specifieke datum
- `get_menu` - Menu ophalen (optioneel gefilterd)
- `search_menu` - Zoeken in menu
- `add_to_cart` - Item toevoegen aan winkelwagen
- `update_cart` - Winkelwagen item updaten
- `remove_from_cart` - Item verwijderen uit winkelwagen
- `get_cart` - Huidige winkelwagen ophalen
- `calculate_total` - Totaalprijs berekenen
- `confirm_order` - Bestelling bevestigen
- `handoff_to_human` - Doorverbinden naar medewerker

## Webhook Server

Een voorbeeld webhook server is beschikbaar in `webhook_example.py`. Deze implementeert alle benodigde endpoints voor de custom tools.

### Lokale Development

```bash
python webhook_example.py
```

De server draait op `http://localhost:5000`. Gebruik ngrok om deze publiek toegankelijk te maken:

```bash
ngrok http 5000
```

### Cloud Deployment

Deploy de webhook server naar een cloud service zoals:
- **Render**: https://render.com
- **Railway**: https://railway.app
- **Vercel**: https://vercel.com (met Flask adapter)
- **Heroku**: https://heroku.com

Zorg ervoor dat de webhook URL publiek toegankelijk is en HTTPS gebruikt.

### Webhook Endpoints

De webhook server moet de volgende endpoints ondersteunen:

- `GET /tools/business_info` - Bedrijfsinformatie
- `GET /tools/hours?date=YYYY-MM-DD` - Openingstijden
- `GET /tools/menu?category=...` - Menu ophalen
- `GET /tools/search_menu?query=...` - Menu zoeken
- `POST /tools/add_to_cart` - Item toevoegen
- `POST /tools/update_cart` - Item updaten
- `POST /tools/remove_from_cart` - Item verwijderen
- `GET /tools/cart` - Winkelwagen ophalen
- `GET /tools/calculate_total` - Totaal berekenen
- `POST /tools/confirm_order` - Bestelling bevestigen
- `POST /tools/handoff` - Doorverbinden

Zonder webhook zal de agent alleen de basis tools gebruiken (end_call) en zal het menu/bestellingen via natuurlijke taal worden afgehandeld.

## Configuratie Aanpassen

### Voice Aanpassen

In `config.py`:
```python
VOICE_CONFIG = {
    "voice_id": "11labs-Nicole",  # Andere stem kiezen
    "voice_model": "eleven_multilingual_v2",
    "voice_speed": 1.0,
    "voice_temperature": 0.7,
}
```

### Prompts Aanpassen

Bewerk `prompts.py` om de prompts en state prompts aan te passen.

### Tools Aanpassen

Bewerk `tools.py` om tools toe te voegen of te wijzigen.

## Testen

Na deployment kun je de agent testen via:
- Retell Dashboard: https://dashboard.retellai.com/agents/{agent_id}
- Telefoonnummer configureren in het dashboard
- Test calls maken via het dashboard

## Troubleshooting

### Agent spreekt Engels
- Controleer of `language: "nl-NL"` is ingesteld in zowel LLM als agent configuratie
- Controleer of de voice model Nederlands ondersteunt (`eleven_multilingual_v2`)

### Tools werken niet
- Controleer of webhook URL correct is geconfigureerd
- Controleer of webhook server actief is en endpoints correct implementeert
- Zonder webhook werken alleen basis tools (end_call)

### Agent maakt fouten
- Verlaag `model_temperature` voor meer accurate antwoorden
- Controleer of prompts duidelijk zijn
- Gebruik `tool_call_strict_mode: true` voor strikte tool calls

## Licentie

Privé project voor De Dorpspomp & Dieks IJssalon.

