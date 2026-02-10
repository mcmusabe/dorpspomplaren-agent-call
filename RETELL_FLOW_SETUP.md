# Retell Flow/States Koppeling - Waar te vinden

## Waar wordt de Flow/States gekoppeld aan de Agent?

### Optie 1: Via LLM Settings (Aanbevolen)

1. **Ga naar je Agent Dashboard:**
   ```
   https://dashboard.retellai.com/agents/{agent_id}
   ```

2. **Klik op "LLM Settings" of "Edit LLM"**
   - Dit staat meestal bovenaan of in het menu links

3. **Scroll naar "States" sectie:**
   - Je zou een sectie moeten zien met "States" of "State Machine"
   - Hier worden de states gedefinieerd die je in `tools.py` hebt gemaakt

4. **Check of states zijn geladen:**
   - Je zou alle 8 states moeten zien: S0_GREETING, S1_INFO_ROUTER, etc.
   - Elke state heeft een prompt en edges (transitions)

### Optie 2: Via Agent Configuration

1. **Ga naar je Agent Dashboard**
2. **Klik op "Configuration" of "Settings"**
3. **Zoek naar "Response Engine" of "LLM Configuration"**
4. **Check of "States" zijn ingesteld:**
   - Er zou een "States" tab of sectie moeten zijn
   - Of een "Flow" visualisatie

### Optie 3: Via API/Code (Huidige methode)

De states worden automatisch gekoppeld via `deploy_agent.py`:
- In `deploy_agent.py` regel 343: `states = get_states_with_tools(WEBHOOK_URL)`
- In `deploy_agent.py` regel 357: `states=states` wordt doorgegeven aan `client.llm.create()`

Dit betekent dat de states worden gekoppeld aan de **LLM**, niet direct aan de agent.

### Belangrijk: States zijn gekoppeld aan LLM, niet Agent!

In Retell:
- **LLM** = De AI model configuratie (met states, prompts, tools)
- **Agent** = De telefoon/voice configuratie (met voice_id, language, etc.)
- De Agent verwijst naar een LLM via `response_engine.llm_id`

### Check of States correct zijn gekoppeld:

1. **Ga naar LLM Settings:**
   - In agent dashboard → "LLM Settings" of "Edit LLM"
   - Of direct: `https://dashboard.retellai.com/llms/{llm_id}`

2. **Check "States" sectie:**
   - Je zou alle 8 states moeten zien
   - Elke state heeft:
     - Name (bijv. "S0_GREETING")
     - State Prompt
     - Edges (transitions naar andere states)
     - Tools (welke tools beschikbaar zijn in die state)

3. **Check "Starting State":**
   - Er zou een "Starting State" moeten zijn ingesteld op "S0_GREETING"

### Als States niet zichtbaar zijn:

1. **Deploy opnieuw:**
   ```bash
   export RETELL_API_KEY='jouw-key'
   python3 deploy_agent.py
   ```

2. **Check de debug output:**
   - Je zou moeten zien: "📊 STATES DEBUG INFO: Total states: 8"
   - Dit betekent dat states correct worden doorgegeven

3. **Check Retell Dashboard:**
   - Refresh de pagina (Ctrl+R / Cmd+R)
   - Check of je de juiste LLM versie bekijkt
   - Check browser console (F12) voor errors

### Screenshot locaties:

**Voor States/Flow:**
- Agent Dashboard → "LLM Settings" → "States" tab
- Of: Agent Dashboard → "Configuration" → "Flow" visualisatie
- Of: Direct LLM pagina → "States" sectie

**Voor Agent → LLM koppeling:**
- Agent Dashboard → "Response Engine" → zie `llm_id` en `version`
- Dit toont welke LLM (en dus welke states) gekoppeld zijn aan de agent
