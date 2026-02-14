"""
VAPI configuratie voor algemene bestel-demo
"""

import os

# VAPI API Keys
VAPI_PRIVATE_KEY = os.getenv("VAPI_PRIVATE_KEY", "7fe9f0d0-7916-47b4-8b23-a387adf65304")
VAPI_PUBLIC_KEY = os.getenv("VAPI_PUBLIC_KEY", "66ce61e6-4711-4e6d-a4b8-2c1f87f339ba")

# VAPI API Base URL
VAPI_API_URL = "https://api.vapi.ai"

# Business informatie (gedeeld met Retell)
BUSINESS_INFO = {
    "name": "Algemene Bestel Demo",
    "address": "Demo locatie",
    "phone": None,
    "opening_hours": {
        "monday": {"open": None, "close": None, "closed": True},
        "tuesday": {"open": None, "close": None, "closed": True},
        "wednesday": {"open": "11:30", "close": "19:30", "closed": False},
        "thursday": {"open": "11:30", "close": "19:30", "closed": False},
        "friday": {"open": "11:30", "close": "20:00", "closed": False},
        "saturday": {"open": "11:30", "close": "20:00", "closed": False},
        "sunday": {"open": "11:30", "close": "20:00", "closed": False},
    }
}

# Voice configuratie voor VAPI (ElevenLabs)
VAPI_VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "XJa38TJgDqYhj5mYbSJA",
    "model": "eleven_turbo_v2_5",
    "language": "nl",
    "stability": 0.72,
    "similarityBoost": 0.86,
    "style": 0.15,
    "useSpeakerBoost": False,
    "optimizeStreamingLatency": 2,
    "speed": 0.98
}

# Model configuratie - balans tussen snelheid en natuurlijkheid
VAPI_MODEL_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "maxTokens": 100
}

# Transcriber configuratie (spraak naar tekst) - PROFESSIONEEL voor Nederlands
VAPI_TRANSCRIBER_CONFIG = {
    "provider": "deepgram",
    "model": "nova-2",              # Beste model voor niet-Engels
    "language": "nl",               # Nederlands
    "smartFormat": True,            # Slimme formattering (nummers, etc)
    "languageDetectionEnabled": False,  # Forceer Nederlands
    "punctuate": True,              # Automatische interpunctie
    "profanityFilter": False,       # Geen filter - accurater
    "redact": False,                # Geen redactie
    "diarize": False,               # Geen speaker diarization nodig
    "numerals": True,               # Nummers als cijfers (3 ipv "drie")
    "utteranceEndMs": 700,
    "vadTurnoff": 350
}

# Webhook URL - Railway deployment (PRODUCTIE)
WEBHOOK_URL = os.getenv("VAPI_WEBHOOK_URL") or os.getenv("RETELL_WEBHOOK_URL") or "https://dorpspomp-webhook-production.up.railway.app"

# Verify webhook URL is correct
if "railway.app" not in WEBHOOK_URL:
    print(f"⚠️  WARNING: WEBHOOK_URL does not point to Railway: {WEBHOOK_URL}")

# Assistant ID bestand voor persistentie
VAPI_ASSISTANT_ID_FILE = "vapi_assistant_id.txt"
