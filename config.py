"""
Configuratie voor De Dorpspomp & Dieks IJssalon Retell AI Agent
"""

import os

# Retell AI API Key (lees uit env var)
RETELL_API_KEY = os.getenv("RETELL_API_KEY")
if not RETELL_API_KEY:
    raise ValueError("RETELL_API_KEY environment variable is required. Set it with: export RETELL_API_KEY='your-key'")

# Agent ID (None - gebruik altijd agent_id.txt als primary)
EXISTING_AGENT_ID = None

# Business informatie
BUSINESS_INFO = {
    "name": "De Dorpspomp & Dieks IJssalon",
    "address": "Holterweg 1, Laren (Gld)",
    "phone": None,  # Wordt later geconfigureerd
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

# Voice configuratie (Nederlandse stem)
# VASTE STEM: ElevenLabs Jennifer - Pleasant Dutch
VOICE_CONFIG = {
    "voice_id": "custom_voice_470fad3ff3b1a70182d936760d",  # ElevenLabs Jennifer - Pleasant Dutch
    "voice_speed": 1.1,  # Normaal tempo voor verstaanbaarheid (was 1.3, te snel)
    "voice_temperature": 0.5,  # Laag voor consistentie
}

# LLM configuratie - GEOPTIMALISEERD
LLM_CONFIG = {
    "model": "gpt-4o-mini",  # Snel model, goede balans tussen snelheid en kwaliteit
    "model_temperature": 0.2,  # Laag voor consistentie (0.3 → 0.2)
    "tool_call_strict_mode": False,  # Flexibel voor tool calls
    "max_tokens": 400,  # VERHOOGD: 200 → 400 (voorkom afgesneden responses)
}

# Webhook URL (optioneel - voor custom tools)
WEBHOOK_URL = "https://725e16cb0b97.ngrok-free.app"  # ngrok tunnel naar lokale webhook server

