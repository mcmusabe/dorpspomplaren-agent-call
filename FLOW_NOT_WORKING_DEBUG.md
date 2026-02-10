# Flow werkt niet tijdens calls - Debugging Guide

## Probleem:
- Flow is zichtbaar in Retell Dashboard ✅
- Maar tijdens calls gebeurt er niets ❌
- Agent gebruikt states niet ❌

## Mogelijke oorzaken:

### 1. States worden niet gebruikt door Retell
**Symptoom:** Flow zichtbaar, maar agent gebruikt states niet tijdens calls

**Oplossing:**
- Check of `starting_state` correct is ingesteld: `"S0_GREETING"` (niet `"greeting"`)
- Check of states correct zijn doorgegeven aan Retell API
- Deploy opnieuw: `python3 deploy_agent.py`

### 2. Agent gebruikt verkeerde LLM versie
**Symptoom:** Oude configuratie wordt gebruikt

**Oplossing:**
- Check in Retell Dashboard → Agent Settings → Response Engine
- Zie welke `llm_id` en `version` gekoppeld zijn
- Deploy opnieuw om nieuwe versie te maken

### 3. Edges (transitions) werken niet
**Symptoom:** Agent blijft in dezelfde state

**Oplossing:**
- Check of edge descriptions duidelijk zijn
- Check of destination states bestaan
- Test met simpele flow eerst (1 state → 1 state)

### 4. Tools worden niet aangeroepen
**Symptoom:** Agent zegt "niet gevonden" zonder search_menu te gebruiken

**Oplossing:**
- Check of tools beschikbaar zijn in de state
- Check webhook logs om te zien of tools worden aangeroepen
- Check of webhook URL correct is

## Debugging Stappen:

### Stap 1: Check of states correct zijn gedeployed
```bash
export RETELL_API_KEY='jouw-key'
python3 deploy_agent.py
```

Je zou moeten zien:
```
📊 STATES DEBUG INFO:
   Total states: 8
   Starting state: S0_GREETING
   State 1: S0_GREETING - 0 tools, 2 edges
   State 2: S1_INFO_ROUTER - 6 tools, 2 edges
   ...
```

### Stap 2: Check Retell Dashboard
1. Ga naar Agent → LLM Settings
2. Check of states zichtbaar zijn
3. Check of `starting_state` = "S0_GREETING"
4. Check of elke state tools heeft

### Stap 3: Test tijdens call
1. Start een test call in Retell Dashboard
2. Kijk in de chat logs welke state actief is
3. Check of tools worden aangeroepen
4. Check webhook logs voor tool calls

### Stap 4: Check webhook
1. Start webhook server: `python3 webhook_order.py`
2. Test call starten
3. Kijk in webhook logs of tools worden aangeroepen
4. Als geen tool calls → agent gebruikt tools niet

## Mogelijke Fixes:

### Fix 1: Starting State naam checken
In `deploy_agent.py` regel 370:
```python
starting_state="S0_GREETING"  # Moet exact overeenkomen met state name
```

### Fix 2: State names moeten exact zijn
Alle state names moeten exact overeenkomen:
- State name: `"S0_GREETING"`
- Starting state: `"S0_GREETING"`
- Edge destination: `"S0_GREETING"`

### Fix 3: Check Retell API versie
Mogelijk is er een format wijziging in Retell API. Check:
- Retell SDK versie
- Retell API documentatie voor states format

### Fix 4: Test met minimale flow
Maak een simpele test flow:
- 1 state: S0_GREETING
- 1 edge: naar S1_INFO_ROUTER
- Test of dit werkt

## Belangrijkste Check:

**Check of de agent de states gebruikt:**
- Tijdens call → kijk in Retell Dashboard chat logs
- Zie je state transitions?
- Zie je tool calls?
- Als NEE → states worden niet gebruikt

**Mogelijke reden:**
- Retell gebruikt states alleen als "Conversation Flow Agent" type
- Of states worden alleen gebruikt als bepaalde configuratie is ingesteld
- Check Retell Dashboard voor "Flow Mode" of "State Machine Mode"
