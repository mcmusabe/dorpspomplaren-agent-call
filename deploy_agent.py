"""
Script om de Retell AI agent te deployen voor De Dorpspomp & Dieks IJssalon
DEMO MODE: Minimale configuratie voor testen
"""

import json
import os
from retell import Retell
from config import (
    RETELL_API_KEY,
    EXISTING_AGENT_ID,
    VOICE_CONFIG,
    LLM_CONFIG,
    WEBHOOK_URL as CONFIG_WEBHOOK_URL
)
from prompts import SYSTEM_PROMPT, BEGIN_MESSAGE
from tools import get_states_with_tools, get_tools_config

# Lees WEBHOOK_URL uit env var, fallback naar config.py
WEBHOOK_URL = os.getenv("RETELL_WEBHOOK_URL") or CONFIG_WEBHOOK_URL

# Log WEBHOOK_URL source
if os.getenv("RETELL_WEBHOOK_URL"):
    print(f"📡 WEBHOOK_URL from RETELL_WEBHOOK_URL env var: {WEBHOOK_URL}")
elif CONFIG_WEBHOOK_URL:
    print(f"📡 WEBHOOK_URL from config.py: {WEBHOOK_URL}")
else:
    print(f"📡 WEBHOOK_URL: None (geen webhook beschikbaar)")

# PRODUCTION MODE: Full state machine met alle tools
USE_SIMPLE_STATE_MACHINE = True  # Gebruik de 3-state machine (greeting, ordering, confirm)

# Agent ID bestand voor persistentie
AGENT_ID_FILE = "agent_id.txt"

def load_agent_id():
    """Lees agent ID uit bestand als het bestaat"""
    if os.path.exists(AGENT_ID_FILE):
        try:
            with open(AGENT_ID_FILE, 'r') as f:
                agent_id = f.read().strip()
                if agent_id:
                    return agent_id
        except Exception as e:
            print(f"⚠️  Kon agent_id.txt niet lezen: {e}")
    return None

def save_agent_id(agent_id):
    """Sla agent ID op in bestand"""
    try:
        with open(AGENT_ID_FILE, 'w') as f:
            f.write(agent_id)
        print(f"💾 Agent ID opgeslagen in {AGENT_ID_FILE}")
    except Exception as e:
        print(f"⚠️  Kon agent_id niet opslaan: {e}")

def pick_voice_id(client):
    """Kies een voice_id voor de agent

    Prioriteit:
    1. VOICE_CONFIG["voice_id"] from config.py (hardcoded)
    2. RETELL_VOICE_ID environment variable
    3. Eerste voice uit Retell List Voices API

    Geen hardcoded fallback - moet altijd een geldige voice_id zijn.
    """
    # Check config first (hardcoded voice)
    from config import VOICE_CONFIG
    if VOICE_CONFIG.get("voice_id"):
        print(f"🎤 Voice ID from config.py: {VOICE_CONFIG['voice_id']}")
        return VOICE_CONFIG["voice_id"]

    # Check environment variable
    env_voice_id = os.getenv("RETELL_VOICE_ID")
    if env_voice_id:
        print(f"🎤 Voice ID from RETELL_VOICE_ID env: {env_voice_id}")
        return env_voice_id
    
    # Get first voice from Retell API
    try:
        voices_response = client.voice.list()
        # Handle both dict and object responses
        if hasattr(voices_response, 'voices'):
            voices = voices_response.voices
        elif isinstance(voices_response, dict):
            voices = voices_response.get('voices', [])
        else:
            voices = list(voices_response) if hasattr(voices_response, '__iter__') else []
        
        if voices and len(voices) > 0:
            # Get voice_id from first voice
            first_voice = voices[0]
            if hasattr(first_voice, 'voice_id'):
                voice_id = first_voice.voice_id
            elif isinstance(first_voice, dict):
                voice_id = first_voice.get('voice_id')
            else:
                voice_id = str(first_voice)
            
            print(f"🎤 Voice ID from Retell API (first available): {voice_id}")
            return voice_id
        else:
            raise ValueError("No voices found in Retell API response")
    except Exception as e:
        print(f"❌ FOUT: Kon geen voice_id ophalen van Retell API: {e}")
        print(f"   Zet RETELL_VOICE_ID env var of run: python3 list_voices.py")
        raise RuntimeError(f"Kan geen voice_id ophalen: {e}")

def get_general_tools_demo():
    """Retourneer ALLEEN end_call tool voor DEMO MODE"""
    tools = [
        {
            "type": "end_call",
            "name": "end_call",
            "description": "Beëindig het gesprek netjes."
        }
    ]
    
    # Assert voor veiligheid
    assert len(tools) == 1, f"DEMO MODE: general_tools moet exact 1 tool bevatten, heeft {len(tools)}"
    assert tools[0]["type"] == "end_call", f"DEMO MODE: general_tools[0] moet type 'end_call' zijn, is '{tools[0]['type']}'"
    
    return tools

def get_order_tool(webhook_url):
    """Retourneer send_order tool voor gebruik in state (niet in general_tools)
    
    Retell accepteert custom tools in states met HTTP endpoint configuratie.
    We gebruiken het Retell custom tool schema met url en method.
    
    Format:
    {
      "customer_name": "<string or empty>",
      "phone": "<string or empty>",
      "pickup_time": "HH:MM",
      "items": [
        {"name": "<item>", "qty": <integer>, "notes": "<optional>"}
      ],
      "extra_notes": "<optional>"
    }
    """
    if not webhook_url:
        return None
    
    # Retell custom tool schema voor HTTP endpoints in states
    tool = {
        "type": "custom",
        "name": "send_order",
        "description": "Verstuur een bestelling naar het bedrijf via email. Gebruik deze tool ALLEEN wanneer de klant de bestelling heeft bevestigd na de samenvatting. Format: customer_name (string/empty), phone (string/empty), pickup_time (HH:MM), items (array met name, qty integer, notes optional), extra_notes (optional).",
        "url": f"{webhook_url}/order",
        "method": "POST",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Naam van de klant (string of leeg string)"
                },
                "phone": {
                    "type": "string",
                    "description": "Telefoonnummer van de klant (string of leeg string)"
                },
                "pickup_time": {
                    "type": "string",
                    "description": "Afhaaltijd in format HH:MM (bijvoorbeeld: 19:00, 19:30). Altijd HH:MM format.",
                    "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
                },
                "items": {
                    "type": "array",
                    "description": "Array van bestelde items. Mag NOOIT leeg zijn. Minimaal 1 item vereist.",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Naam van het item (bijvoorbeeld: 'Friet', 'Frikandel', 'Hamburger')"
                            },
                            "qty": {
                                "type": "integer",
                                "description": "Aantal van dit item. Altijd een INTEGER (1, 2, 3, etc.). Minimum 1.",
                                "minimum": 1
                            },
                            "notes": {
                                "type": "string",
                                "description": "Speciale opmerkingen voor dit item (optioneel, bijvoorbeeld: 'zonder mayonaise', 'extra ketchup')"
                            }
                        },
                        "required": ["name", "qty"]
                    }
                },
                "extra_notes": {
                    "type": "string",
                    "description": "Extra opmerkingen voor de hele bestelling (optioneel)"
                }
            },
            "required": ["items", "pickup_time"]
        },
        "speak_during_execution": False,
        "speak_after_execution": True
    }
    
    return tool

def _get_llm_config(client):
    """Gedeelde configuratie voor create en update - voorkomt duplicatie"""
    
    print("🔧 DEMO MODE ON: end_call only, text model")
    
    # Print webhook URL status
    if os.getenv("RETELL_WEBHOOK_URL"):
        print(f"📡 WEBHOOK_URL from RETELL_WEBHOOK_URL env: {WEBHOOK_URL}")
    elif CONFIG_WEBHOOK_URL:
        print(f"📡 WEBHOOK_URL from config.py: {WEBHOOK_URL}")
    else:
        print(f"📡 WEBHOOK_URL: None (geen webhook beschikbaar)")
    
    # Forceer minimale general_tools
    tools = get_general_tools_demo()
    print(f"  → general_tools count: {len(tools)}")
    print(f"  → general_tools[0].type: {tools[0]['type']}")
    
    # Get order tool (alleen als webhook_url beschikbaar is)
    order_tool = get_order_tool(WEBHOOK_URL)
    order_state_tools = []
    if order_tool:
        order_state_tools = [order_tool]
        print(f"✅ send_order tool actief in 'order' state")
        # Log tool object (zonder secrets)
        tool_log = json.dumps({
            "type": order_tool.get("type"),
            "name": order_tool.get("name"),
            "description": order_tool.get("description"),
            "url": order_tool.get("url"),
            "method": order_tool.get("method"),
            "speak_during_execution": order_tool.get("speak_during_execution"),
            "speak_after_execution": order_tool.get("speak_after_execution")
        }, indent=2, ensure_ascii=False)
        print(f"  → Order state tool config:")
        for line in tool_log.split('\n'):
            print(f"     {line}")
    else:
        print(f"⚠️  send_order tool NIET beschikbaar (geen WEBHOOK_URL)")
    
    # States met flow (greeting -> info/order)
    order_state_prompt = """Neem de bestelling op. Mensen bestellen vaak rommelig - dit is normaal!

PROCES:
1) Verzamel alle items (ook als chaotisch)
2) Vraag altijd naar afhaaltijd als die nog ontbreekt
3) Geef een volledige samenvatting: items + tijd
4) Vraag bevestiging: "Klopt dit zo?"

"""
    
    if order_tool:
        order_state_prompt += """HARD RULES (MOET):
- Als send_order tool aanwezig is: gebruik hem DIRECT zodra de klant "ja/klopt" zegt na de samenvatting.
- Zeg NOOIT "ik kan dit niet automatisch verwerken" zolang send_order bestaat.
- Na "ja/klopt" → roep send_order aan met items + pickup_time.

SEND_ORDER FORMAT (EXACT):
{
  "customer_name": "<string or empty>",
  "phone": "<string or empty>",
  "pickup_time": "HH:MM",  // Altijd HH:MM format (bijv: 19:00, 19:30)
  "items": [
    {"name": "<item>", "qty": <integer>, "notes": "<optional>"}
  ],  // items mag NOOIT leeg zijn, minimaal 1 item
  "extra_notes": "<optional>"
}

BELANGRIJK:
- qty is ALTIJD een INTEGER (1, 2, 3, niet "een" of "twee")
- pickup_time ALTIJD HH:MM format (19:00, 19:30, niet "7 uur" of "half 8")
- items array mag NOOIT leeg zijn (minimaal 1 item)
- Zeg pas "bestelling is doorgegeven" NA een succesvolle tool response.
- Als tool call faalt: zeg eerlijk dat het systeem faalt en dat je het handmatig doorgeeft.
"""
    else:
        order_state_prompt += """LET OP:
- send_order tool is niet beschikbaar. Zeg: "Ik heb je bestelling genoteerd en geef het handmatig door."
"""
    
    states = [
        {
            "name": "greeting",
            "state_prompt": "Je begint vriendelijk: 'Hoi, je spreekt met de Dorpspomp. Waar kan ik je mee helpen?' Luister naar wat de klant nodig heeft.",
            "edges": [
                {"destination_state_name": "info", "description": "Klant vraagt informatie (openingstijden, adres, menu)"},
                {"destination_state_name": "order", "description": "Klant wil een bestelling plaatsen"}
            ]
        },
        {
            "name": "info",
            "state_prompt": "Beantwoord vragen over openingstijden, adres of menu. Wees kort en vriendelijk. Openingstijden: ma/di gesloten, wo/do 11:30-19:30, vr-zo 11:30-20:00. Adres: Holterweg 1, Laren (Gld).",
            "edges": [
                {"destination_state_name": "order", "description": "Klant wil nu een bestelling plaatsen"},
                {"destination_state_name": "greeting", "description": "Klant heeft geen verdere vragen"}
            ]
        },
        {
            "name": "order",
            "state_prompt": order_state_prompt,
            "edges": [
                {"destination_state_name": "greeting", "description": "Bestelling is afgerond of klant wil iets anders"}
            ],
            "tools": order_state_tools  # Alleen send_order tool als webhook beschikbaar is
        }
    ]
    
    # Gebruik TEXT model (geen s2s_model)
    print("  → Model type: TEXT (gpt-4o-mini)")
    print("  → s2s_model: NIET gebruikt")
    print("  → States: greeting → info/order (starting_state: greeting)")
    if order_state_tools:
        print(f"  → Order state heeft {len(order_state_tools)} tool(s): send_order")
    else:
        print(f"  → Order state heeft geen tools (webhook niet beschikbaar)")
    
    return tools, states

def create_retell_llm(client):
    """Maak een nieuwe Retell LLM aan met state machine configuratie"""

    if not USE_SIMPLE_STATE_MACHINE:
        tools, states = _get_llm_config(client)
        
        llm_response = client.llm.create(
            model="gpt-4o-mini",  # TEXT model, geen s2s_model
            model_temperature=0.2,
            general_prompt=SYSTEM_PROMPT,
            start_speaker="agent",
            begin_message=BEGIN_MESSAGE,
            begin_after_user_silence_ms=1500,  # Extra tijd zodat agent klant ALTIJD laat uitpraten (was 1200ms)
            general_tools=tools,  # Alleen end_call
            states=states,
            starting_state="greeting"  # Start met greeting state
        )
    else:
        # SIMPLE STATE MACHINE: 3 states (greeting, ordering, confirm)
        print("🚀 SIMPLE STATE MACHINE: 3-state flow with wijzigen support")
        states = get_states_with_tools(WEBHOOK_URL)
        tools = get_tools_config(WEBHOOK_URL)

        # Extract only general tools (end_call)
        general_tools = [t for t in tools if t.get("type") == "end_call"]

        print(f"\n📊 STATE MACHINE SETUP:")
        print(f"   Total states: {len(states)}")
        print(f"   States: {', '.join([s['name'] for s in states])}")
        for state in states:
            state_tools = state.get("tools", [])
            print(f"   - {state['name']}: {len(state_tools)} tools")
        print()

        llm_response = client.llm.create(
            model=LLM_CONFIG["model"],
            model_temperature=LLM_CONFIG["model_temperature"],
            general_prompt=SYSTEM_PROMPT,
            start_speaker="agent",
            begin_message=BEGIN_MESSAGE,
            begin_after_user_silence_ms=700,
            general_tools=general_tools,
            states=states,
            starting_state="greeting"
        )
    
    print(f"✓ LLM created: {llm_response.llm_id}")
    return llm_response.llm_id, llm_response.version

def update_retell_llm(client, llm_id, version):
    """Update een bestaande Retell LLM met state machine configuratie"""

    if not USE_SIMPLE_STATE_MACHINE:
        tools, states = _get_llm_config(client)
        
        llm_response = client.llm.update(
            llm_id=llm_id,
            model="gpt-4o-mini",  # TEXT model, geen s2s_model
            model_temperature=0.2,
            general_prompt=SYSTEM_PROMPT,
            start_speaker="agent",
            begin_message=BEGIN_MESSAGE,
            begin_after_user_silence_ms=1500,  # Extra tijd zodat agent klant ALTIJD laat uitpraten (was 1200ms)
            general_tools=tools,
            states=states,
            starting_state="greeting"  # Start met greeting state
        )
    else:
        # SIMPLE STATE MACHINE: 3 states (greeting, ordering, confirm)
        print("🚀 SIMPLE STATE MACHINE: 3-state flow with wijzigen support")
        states = get_states_with_tools(WEBHOOK_URL)
        tools = get_tools_config(WEBHOOK_URL)

        # Extract only general tools (end_call)
        general_tools = [t for t in tools if t.get("type") == "end_call"]

        print(f"\n📊 STATE MACHINE SETUP:")
        print(f"   Total states: {len(states)}")
        print(f"   States: {', '.join([s['name'] for s in states])}")
        for state in states:
            state_tools = state.get("tools", [])
            print(f"   - {state['name']}: {len(state_tools)} tools")
        print()

        llm_response = client.llm.update(
            llm_id=llm_id,
            model=LLM_CONFIG["model"],
            model_temperature=LLM_CONFIG["model_temperature"],
            general_prompt=SYSTEM_PROMPT,
            start_speaker="agent",
            begin_message=BEGIN_MESSAGE,
            begin_after_user_silence_ms=700,
            general_tools=general_tools,
            states=states,
            starting_state="greeting"
        )
    
    print(f"✓ LLM updated: version {llm_response.version}")
    return llm_response.llm_id, llm_response.version

def create_or_update_agent(client, llm_id, llm_version):
    """Maak een nieuwe agent aan of update een bestaande - PRODUCTION MODE"""
    
    # Laad agent ID uit bestand of gebruik EXISTING_AGENT_ID
    agent_id_to_use = load_agent_id() or EXISTING_AGENT_ID
    
    agent_config = {
        "response_engine": {
            "type": "retell-llm",
            "llm_id": llm_id,
            "version": llm_version
        },
        "agent_name": "De Dorpspomp - AI Telefoonassistent",
        "language": "nl-NL",

        # ⚡ RESPONSIVENESS - Laag zodat agent ALTIJD klant laat uitpraten
        "responsiveness": 0.3,  # 0-1: LAAG = wacht langer voor reageren (agent valt niet in de rede)

        # 🎙️ INTERRUPTION - Hoge gevoeligheid zodat klant agent makkelijk kan onderbreken
        "interruption_sensitivity": 0.7,  # 0-1: HOOG = klant kan agent makkelijk onderbreken

        # 🔇 BACKCHANNEL - Uit voor snelheid
        "enable_backchannel": False,  # Geen "uh-huh"

        # 📝 PRONUNCIATION
        "normalize_for_speech": True,  # Cijfers naar woorden

        # ⏱️ REMINDER
        "reminder_trigger_ms": 30000,
        "reminder_max_count": 0,  # Geen reminders

        # ☎️ VOICEMAIL
        "enable_voicemail_detection": True,
        "voicemail_message": "Hoi, je spreekt met De Dorpspomp. Bel terug of bestel online. Tot ziens!",

        # ⏰ TIMEOUTS
        "end_call_after_silence_ms": 20000,  # 20 sec stilte
        "max_call_duration_ms": 600000,  # Max 10 min

        # 🔊 AMBIENT SOUND - Geen achtergrondgeluid
        # Opties: coffee-shop, convention-hall, summer-outdoor, mountain-outdoor, static-noise, call-center
        # We gebruiken None voor geen achtergrondgeluid

        # 🔐 WEBHOOK
        "webhook_url": WEBHOOK_URL if WEBHOOK_URL else None,
    }

    # Pick voice_id (verplicht veld voor agent.create)
    voice_id = pick_voice_id(client)
    agent_config["voice_id"] = voice_id

    # Add voice speed and temperature from config
    from config import VOICE_CONFIG
    if VOICE_CONFIG.get("voice_speed"):
        agent_config["voice_speed"] = VOICE_CONFIG["voice_speed"]
        print(f"🎤 Voice speed: {VOICE_CONFIG['voice_speed']}")
    if VOICE_CONFIG.get("voice_temperature"):
        agent_config["voice_temperature"] = VOICE_CONFIG["voice_temperature"]
        print(f"🎤 Voice temperature: {VOICE_CONFIG['voice_temperature']}")

    # Probeer update als agent ID bekend is
    if agent_id_to_use:
        print(f"🔄 Attempting to update agent {agent_id_to_use}...")
        try:
            agent_response = client.agent.update(
                agent_id=agent_id_to_use,
                **agent_config
            )
            print(f"✓ Agent updated: {agent_id_to_use}")
            return agent_response
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"⚠️  Agent {agent_id_to_use} niet gevonden (404)")
                print("   Creating new agent instead...")
                # Verwijder oude agent_id.txt als die niet bestaat
                if os.path.exists(AGENT_ID_FILE):
                    try:
                        os.remove(AGENT_ID_FILE)
                        print(f"   Removed stale {AGENT_ID_FILE}")
                    except:
                        pass
            else:
                print(f"⚠️  Update failed: {e}")
                print("   Creating new agent instead...")
    
    # Maak nieuwe agent
    print("🆕 Creating new agent...")
    agent_response = client.agent.create(**agent_config)
    
    # Extract agent_id from response (handle both object and dict)
    new_agent_id = None
    if hasattr(agent_response, 'agent_id'):
        new_agent_id = agent_response.agent_id
    elif isinstance(agent_response, dict):
        new_agent_id = agent_response.get('agent_id')
    
    if new_agent_id:
        save_agent_id(new_agent_id)
        print(f"✓ Agent created: {new_agent_id}")
        print(f"\n{'='*60}")
        print(f"📊 AGENT DASHBOARD:")
        print(f"{'='*60}")
        print(f"Agent ID: {new_agent_id}")
        print(f"Dashboard URL: https://dashboard.retellai.com/agents/{new_agent_id}")
        print(f"{'='*60}\n")
    else:
        print("⚠️  Kon agent_id niet extraheren uit response")
    
    return agent_response

def main():
    """Hoofdfunctie om de agent te deployen"""
    
    print("=" * 60)
    print("De Dorpspomp & Dieks IJssalon - Retell AI Agent Deploy")
    if USE_SIMPLE_STATE_MACHINE:
        print("MODE: Simple 3-state machine (greeting → ordering → confirm)")
    else:
        print("MODE: Legacy state machine")
    print("=" * 60)
    print()
    
    # Initialiseer Retell client
    print("✅ Client geïnitialiseerd")
    client = Retell(api_key=RETELL_API_KEY)
    
    try:
        # Laad agent ID uit bestand (primary source)
        saved_agent_id = load_agent_id()
        if saved_agent_id:
            print(f"📁 Agent ID geladen uit {AGENT_ID_FILE}: {saved_agent_id}")
        elif EXISTING_AGENT_ID:
            print(f"📁 Gebruik EXISTING_AGENT_ID uit config.py: {EXISTING_AGENT_ID}")
        else:
            print(f"📁 Geen bestaande agent ID gevonden - nieuwe agent wordt aangemaakt")
        
        # Probeer bestaande LLM op te halen of maak nieuwe
        # saved_agent_id is primary, EXISTING_AGENT_ID is fallback
        agent_id_to_check = saved_agent_id or EXISTING_AGENT_ID
        existing_llm_id = None
        existing_version = 0
        
        if agent_id_to_check:
            try:
                existing_agent = client.agent.retrieve(agent_id=agent_id_to_check)
                print(f"Found existing agent: {agent_id_to_check}")
                
                if hasattr(existing_agent, 'response_engine'):
                    response_engine = existing_agent.response_engine
                else:
                    response_engine = existing_agent.get('response_engine', {})
                
                if isinstance(response_engine, dict):
                    existing_llm_id = response_engine.get("llm_id")
                    existing_version = response_engine.get("version", 0)
                else:
                    existing_llm_id = getattr(response_engine, "llm_id", None)
                    existing_version = getattr(response_engine, "version", 0)
                
                if existing_llm_id:
                    print(f"Found existing LLM: {existing_llm_id}")
                    llm_id, llm_version = update_retell_llm(client, existing_llm_id, existing_version)
                else:
                    print("No existing LLM found, creating new one...")
                    llm_id, llm_version = create_retell_llm(client)
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg or "not found" in error_msg.lower():
                    print(f"Agent {agent_id_to_check} niet gevonden, creating new LLM...")
                else:
                    print(f"Could not retrieve existing agent: {e}")
                    print("Creating new LLM...")
                llm_id, llm_version = create_retell_llm(client)
        else:
            print("No agent ID to check, creating new LLM...")
            llm_id, llm_version = create_retell_llm(client)
        
        print()
        
        # Maak of update agent
        agent_response = create_or_update_agent(client, llm_id, llm_version)
        
        # Extract agent_id from response
        agent_id = None
        if hasattr(agent_response, 'agent_id'):
            agent_id = agent_response.agent_id
        elif isinstance(agent_response, dict):
            agent_id = agent_response.get('agent_id')
        
        print()
        print("=" * 60)
        print("🎉 Deployment successful!")
        print("=" * 60)
        print(f"\n✅ Client geïnitialiseerd")
        print(f"✅ LLM aangemaakt: {llm_id} (version {llm_version})")
        
        if agent_id:
            print(f"✅ Agent ID: {agent_id}")
            print(f"✅ Agent opgeslagen in: {AGENT_ID_FILE}")
            print(f"\n📊 DASHBOARD LINK:")
            print(f"   https://dashboard.retellai.com/agents/{agent_id}")
            print(f"\n💡 TIP: Open deze link in je browser om de agent flow te zien!")
        else:
            print(f"⚠️  Agent ID niet beschikbaar in response")
        
        print("\n" + "=" * 60)
        print("TEST INSTRUCTIES:")
        print("=" * 60)
        print("1. Bel het telefoonnummer dat gekoppeld is aan deze agent")
        print("2. Agent neemt op en praat normaal")
        print("3. Je kunt vragen stellen over openingstijden, adres of menu")
        print("4. Zeg 'tot ziens' om het gesprek te beëindigen")
        print("5. Agent gebruikt end_call tool om netjes op te hangen")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
