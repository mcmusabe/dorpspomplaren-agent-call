"""
Script om de VAPI assistant te deployen - Voice Ordering Demo
"""

import json
import os
import requests
from vapi_config import (
    VAPI_PRIVATE_KEY,
    VAPI_API_URL,
    VAPI_VOICE_CONFIG,
    VAPI_MODEL_CONFIG,
    VAPI_TRANSCRIBER_CONFIG,
    WEBHOOK_URL,
    VAPI_ASSISTANT_ID_FILE
)
from vapi_prompts import get_dynamic_system_prompt, VAPI_FIRST_MESSAGE, get_voicemail_message
from vapi_tools import get_vapi_tools, get_vapi_end_call_tool


def load_assistant_id():
    """Lees assistant ID uit bestand als het bestaat"""
    if os.path.exists(VAPI_ASSISTANT_ID_FILE):
        try:
            with open(VAPI_ASSISTANT_ID_FILE, 'r') as f:
                assistant_id = f.read().strip()
                if assistant_id:
                    return assistant_id
        except Exception as e:
            print(f"Kon {VAPI_ASSISTANT_ID_FILE} niet lezen: {e}")
    return None


def save_assistant_id(assistant_id):
    """Sla assistant ID op in bestand"""
    try:
        with open(VAPI_ASSISTANT_ID_FILE, 'w') as f:
            f.write(assistant_id)
        print(f"Assistant ID opgeslagen in {VAPI_ASSISTANT_ID_FILE}")
    except Exception as e:
        print(f"Kon assistant_id niet opslaan: {e}")


def get_headers():
    """Retourneer headers voor VAPI API requests"""
    return {
        "Authorization": f"Bearer {VAPI_PRIVATE_KEY}",
        "Content-Type": "application/json"
    }


def list_voices():
    """Lijst beschikbare voices van VAPI"""
    print("\nBeschikbare voices ophalen...")

    # VAPI heeft geen directe voice list API - we gebruiken ElevenLabs voices
    # Voor nu gebruiken we de geconfigureerde voice
    print(f"Geconfigureerde voice: {VAPI_VOICE_CONFIG}")
    return VAPI_VOICE_CONFIG


def create_assistant():
    """Maak een nieuwe VAPI assistant aan"""
    print("Nieuwe VAPI assistant aanmaken...")

    # Haal tools op
    tools = get_vapi_tools(WEBHOOK_URL)
    end_call_tool = get_vapi_end_call_tool()
    all_tools = tools + [end_call_tool]

    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Aantal tools: {len(all_tools)}")

    # Build assistant configuration
    assistant_config = {
        "name": "Voice Ordering Demo - AI Assistent",

        # Transcriber (spraak naar tekst) - PROFESSIONEEL NEDERLANDS
        "transcriber": {
            "provider": VAPI_TRANSCRIBER_CONFIG["provider"],
            "model": VAPI_TRANSCRIBER_CONFIG["model"],
            "language": VAPI_TRANSCRIBER_CONFIG["language"],
            "smartFormat": True,
            # Keywords voor betere herkenning van snackbar termen
            "keywords": [
                "friet:2", "patat:2", "patatje:2",
                "kroket:2", "frikandel:2", "kaassoufle:2",
                "cola:2", "fanta:2", "sprite:2",
                "mayonaise:2", "ketchup:2", "curry:2",
                "speciaal:2", "oorlog:2", "sate:2"
            ]
        },

        # Background Speech Denoising - Gebalanceerd
        "backgroundSpeechDenoisingPlan": {
            "smartDenoisingPlan": {
                "enabled": True
            }
        },

        # Model (LLM)
        "model": {
            "provider": VAPI_MODEL_CONFIG["provider"],
            "model": VAPI_MODEL_CONFIG["model"],
            "temperature": VAPI_MODEL_CONFIG["temperature"],
            "maxTokens": VAPI_MODEL_CONFIG["maxTokens"],
            "messages": [
                {
                    "role": "system",
                    "content": get_dynamic_system_prompt()
                }
            ],
            "tools": all_tools
        },

        # Voice (tekst naar spraak) - SNELLE Nederlandse stem
        "voice": {
            "provider": VAPI_VOICE_CONFIG["provider"],
            "voiceId": VAPI_VOICE_CONFIG["voiceId"],
            "model": VAPI_VOICE_CONFIG.get("model", "eleven_turbo_v2_5"),
            "language": VAPI_VOICE_CONFIG.get("language", "nl"),
            "stability": VAPI_VOICE_CONFIG["stability"],
            "similarityBoost": VAPI_VOICE_CONFIG["similarityBoost"],
            "style": VAPI_VOICE_CONFIG.get("style", 0.5),
            "useSpeakerBoost": VAPI_VOICE_CONFIG.get("useSpeakerBoost", True),
            "optimizeStreamingLatency": VAPI_VOICE_CONFIG.get("optimizeStreamingLatency", 3),
            "speed": VAPI_VOICE_CONFIG.get("speed", 1.1)
        },

        # Eerste bericht
        "firstMessage": VAPI_FIRST_MESSAGE,

        # Server URL voor webhooks
        "serverUrl": WEBHOOK_URL,

        # Voicemail detectie
        "voicemailDetection": {
            "enabled": True,
            "provider": "twilio"
        },
        "voicemailMessage": get_voicemail_message(),

        # === PROFESSIONELE VOICE PIPELINE VOOR NEDERLANDS ===
        
        # Conversation settings
        "silenceTimeoutSeconds": 25,        # Genoeg tijd om te denken
        "maxDurationSeconds": 300,          # 5 min max
        "backgroundSound": "off",

        # Response settings
        "responseDelaySeconds": 0,          # Geen delay
        "llmRequestDelaySeconds": 0,        # Geen delay
        "interruptionsEnabled": True,       # Klant kan onderbreken
        "backchannelingEnabled": False,     # Geen "hmm" tussendoor
        "hipaaEnabled": False,
        
        # Start Speaking Plan - Voor NEDERLANDS (text-based endpointing)
        # LiveKit werkt alleen voor Engels, dus we gebruiken transcriptionEndpointingPlan
        "startSpeakingPlan": {
            "waitSeconds": 0.3,             # 300ms wachten na spraak stopt
            "transcriptionEndpointingPlan": {
                "onPunctuationSeconds": 0.1,      # Snel na interpunctie
                "onNoPunctuationSeconds": 1.2,    # Langer wachten zonder interpunctie
                "onNumberSeconds": 0.8            # Extra tijd voor nummers (hoeveelheden)
            }
        },
        
        # Stop Speaking Plan - Interrupt detectie
        "stopSpeakingPlan": {
            "numWords": 0,                  # VAD-based (snelste)
            "voiceSeconds": 0.2,            # 200ms voice activity voor interrupt
            "backoffSeconds": 0.8           # 800ms rust na interrupt
        },

        # End call phrases - Nederlandse uitdrukkingen
        "endCallPhrases": [
            "doei",
            "tot zo",
            "tot ziens",
            "bedankt",
            "dankjewel",
            "dag"
        ],

        # Metadata
        "metadata": {
            "business": "Voice Ordering Demo",
            "location": "Demo",
            "platform": "vapi"
        }
    }

    # API call
    response = requests.post(
        f"{VAPI_API_URL}/assistant",
        headers=get_headers(),
        json=assistant_config
    )

    if response.status_code == 201:
        data = response.json()
        assistant_id = data.get("id")
        print(f"Assistant aangemaakt: {assistant_id}")
        save_assistant_id(assistant_id)
        return data
    else:
        print(f"Fout bij aanmaken assistant: {response.status_code}")
        print(response.text)
        raise Exception(f"Failed to create assistant: {response.text}")


def update_assistant(assistant_id):
    """Update een bestaande VAPI assistant"""
    print(f"VAPI assistant updaten: {assistant_id}...")

    # Haal tools op
    tools = get_vapi_tools(WEBHOOK_URL)
    end_call_tool = get_vapi_end_call_tool()
    all_tools = tools + [end_call_tool]

    # Build update configuration - PROFESSIONEEL NEDERLANDS
    update_config = {
        "name": "Voice Ordering Demo - AI Assistent",

        # Transcriber - PROFESSIONEEL voor Nederlands
        "transcriber": {
            "provider": VAPI_TRANSCRIBER_CONFIG["provider"],
            "model": VAPI_TRANSCRIBER_CONFIG["model"],
            "language": VAPI_TRANSCRIBER_CONFIG["language"],
            "smartFormat": True,
            # Keywords voor betere herkenning van snackbar termen
            "keywords": [
                "friet:2", "patat:2", "patatje:2",
                "kroket:2", "frikandel:2", "kaassoufle:2",
                "cola:2", "fanta:2", "sprite:2",
                "mayonaise:2", "ketchup:2", "curry:2",
                "speciaal:2", "oorlog:2", "sate:2"
            ]
        },

        # Background Speech Denoising
        "backgroundSpeechDenoisingPlan": {
            "smartDenoisingPlan": {
                "enabled": True
            }
        },

        "model": {
            "provider": VAPI_MODEL_CONFIG["provider"],
            "model": VAPI_MODEL_CONFIG["model"],
            "temperature": VAPI_MODEL_CONFIG["temperature"],
            "maxTokens": VAPI_MODEL_CONFIG["maxTokens"],
            "messages": [
                {
                    "role": "system",
                    "content": get_dynamic_system_prompt()
                }
            ],
            "tools": all_tools
        },

        # Voice - Nederlandse stem
        "voice": {
            "provider": VAPI_VOICE_CONFIG["provider"],
            "voiceId": VAPI_VOICE_CONFIG["voiceId"],
            "model": VAPI_VOICE_CONFIG.get("model", "eleven_turbo_v2_5"),
            "language": VAPI_VOICE_CONFIG.get("language", "nl"),
            "stability": VAPI_VOICE_CONFIG["stability"],
            "similarityBoost": VAPI_VOICE_CONFIG["similarityBoost"],
            "style": VAPI_VOICE_CONFIG.get("style", 0.3),
            "useSpeakerBoost": VAPI_VOICE_CONFIG.get("useSpeakerBoost", False),
            "optimizeStreamingLatency": VAPI_VOICE_CONFIG.get("optimizeStreamingLatency", 4),
            "speed": VAPI_VOICE_CONFIG.get("speed", 1.15)
        },

        "firstMessage": VAPI_FIRST_MESSAGE,
        "serverUrl": WEBHOOK_URL,
        "voicemailMessage": get_voicemail_message(),

        # === PROFESSIONELE VOICE PIPELINE VOOR NEDERLANDS ===
        "silenceTimeoutSeconds": 25,
        "maxDurationSeconds": 300,
        "responseDelaySeconds": 0,
        "llmRequestDelaySeconds": 0,
        "interruptionsEnabled": True,
        "backchannelingEnabled": False,
        
        # Start Speaking Plan - Voor NEDERLANDS
        "startSpeakingPlan": {
            "waitSeconds": 0.3,
            "transcriptionEndpointingPlan": {
                "onPunctuationSeconds": 0.1,
                "onNoPunctuationSeconds": 1.2,
                "onNumberSeconds": 0.8
            }
        },
        
        # Stop Speaking Plan
        "stopSpeakingPlan": {
            "numWords": 0,
            "voiceSeconds": 0.2,
            "backoffSeconds": 0.8
        },
        
        "endCallPhrases": [
            "doei",
            "tot zo",
            "tot ziens",
            "bedankt",
            "dankjewel",
            "dag"
        ],

        # === NEDERLANDSE ANALYSE PLAN ===
        "analysisPlan": {
            "summaryPlan": {
                "enabled": True,
                "messages": [
                    {
                        "role": "system",
                        "content": "Schrijf een korte samenvatting in het NEDERLANDS. Vermeld: klantnaam, bestelde items, afhaaltijd, totaalbedrag. Max 3 zinnen."
                    }
                ]
            },
            "structuredDataPlan": {
                "enabled": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "klantnaam": {"type": "string", "description": "Naam van de klant"},
                        "afhaaltijd": {"type": "string", "description": "Afhaaltijd HH:MM"},
                        "items": {"type": "array", "items": {"type": "string"}, "description": "Bestelde items"},
                        "totaal": {"type": "number", "description": "Totaalbedrag in euro"}
                    }
                }
            },
            "successEvaluationPlan": {
                "enabled": True,
                "rubric": "NumericScale",
                "messages": [
                    {
                        "role": "system",
                        "content": "Beoordeel in het Nederlands of de bestelling succesvol is. 10 = perfect (naam, items, tijd), 1 = mislukt."
                    }
                ]
            }
        },

        # End call message in het Nederlands
        "endCallMessage": "Bedankt! Tot zo!"
    }

    # API call
    response = requests.patch(
        f"{VAPI_API_URL}/assistant/{assistant_id}",
        headers=get_headers(),
        json=update_config
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Assistant geupdate: {assistant_id}")
        return data
    else:
        print(f"Fout bij updaten assistant: {response.status_code}")
        print(response.text)
        raise Exception(f"Failed to update assistant: {response.text}")


def get_assistant(assistant_id):
    """Haal assistant details op"""
    response = requests.get(
        f"{VAPI_API_URL}/assistant/{assistant_id}",
        headers=get_headers()
    )

    if response.status_code == 200:
        return response.json()
    else:
        return None


def create_or_update_assistant():
    """Maak nieuwe of update bestaande assistant"""
    existing_id = load_assistant_id()

    if existing_id:
        print(f"Bestaande assistant gevonden: {existing_id}")

        # Check of assistant nog bestaat
        existing = get_assistant(existing_id)
        if existing:
            return update_assistant(existing_id)
        else:
            print("Assistant niet meer gevonden, nieuwe aanmaken...")

    return create_assistant()


def main():
    """Hoofdfunctie om de VAPI assistant te deployen"""

    print("=" * 60)
    print("Voice Ordering Demo - VAPI Assistant Deploy")
    print("=" * 60)
    print()

    # Check API key
    if not VAPI_PRIVATE_KEY or VAPI_PRIVATE_KEY == "your-private-key-here":
        print("FOUT: VAPI_PRIVATE_KEY niet geconfigureerd!")
        print("Zet je VAPI API key in vapi_config.py of als environment variable.")
        return 1

    print(f"VAPI API Key: {VAPI_PRIVATE_KEY[:8]}...{VAPI_PRIVATE_KEY[-4:]}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print()

    try:
        # Deploy assistant
        result = create_or_update_assistant()

        assistant_id = result.get("id")

        print()
        print("=" * 60)
        print("VAPI Assistant Deployment Succesvol!")
        print("=" * 60)
        print()
        print(f"Assistant ID: {assistant_id}")
        print(f"Assistant Name: {result.get('name')}")
        print()
        print("VAPI Dashboard:")
        print(f"  https://dashboard.vapi.ai/assistants/{assistant_id}")
        print()
        print("Om te testen:")
        print("  1. Ga naar het VAPI dashboard")
        print("  2. Koppel een telefoonnummer aan deze assistant")
        print("  3. Bel het nummer en test de bestelling")
        print()
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nFOUT: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
