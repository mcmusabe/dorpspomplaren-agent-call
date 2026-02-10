# Retell AI Conversation Flow Builder - Handleiding

## Wat is het verschil?

### Huidige methode (API/Code):
- States worden gedefinieerd in `tools.py`
- Via `deploy_agent.py` naar Retell API gestuurd
- States zijn zichtbaar in dashboard maar **niet bewerkbaar**
- Je moet code aanpassen en opnieuw deployen

### Conversation Flow Builder (Visueel):
- Visuele nodes/blokken in Retell Dashboard
- Direct bewerkbaar zonder code
- Transitions visueel configureren
- Waarschijnlijk "Conversation Flow Agent" type

## Hoe check je of je Conversation Flow kunt gebruiken?

### Stap 1: Check Agent Type
1. Ga naar Retell Dashboard: https://dashboard.retellai.com/agents
2. Klik op je agent
3. Kijk naar "Agent Type" of "Response Engine Type"
4. Check of er een optie is voor "Conversation Flow" of "Visual Flow"

### Stap 2: Check LLM Settings
1. Ga naar je Agent → "LLM Settings" of "Edit LLM"
2. Kijk of er een tab is voor "Flow" of "Conversation Flow"
3. Of een knop "Switch to Visual Flow Builder"

### Stap 3: Check Agent Creation
1. Ga naar "Create New Agent"
2. Kijk of er een optie is voor "Conversation Flow Agent"
3. Of een keuze tussen "LLM Agent" en "Flow Agent"

## Mogelijke oplossingen:

### Optie 1: Nieuwe Agent aanmaken in Conversation Flow mode
Als Retell AI een aparte "Conversation Flow Agent" type heeft:
1. Maak een nieuwe agent aan in Retell Dashboard
2. Kies "Conversation Flow" of "Visual Flow" mode
3. Bouw de flow visueel met nodes
4. Configureer tools via de visuele interface

### Optie 2: States exporteren en importeren
Als Retell AI export/import ondersteunt:
1. Exporteer huidige states uit Retell Dashboard
2. Importeer in Conversation Flow builder
3. Bewerk visueel verder

### Optie 3: Handmatig overzetten
1. Open Retell Dashboard Conversation Flow builder
2. Maak nodes voor elke state (S0_GREETING, S1_INFO_ROUTER, etc.)
3. Configureer transitions (edges) visueel
4. Voeg tools toe aan elke node
5. Test de flow

## Wat moet je doen?

### Check eerst in Retell Dashboard:
1. **Ga naar je Agent Settings**
2. **Kijk of er een "Flow" tab is** (naast "Settings", "Analytics", etc.)
3. **Of ga naar "LLM Settings" → "Flow" of "Conversation Flow"**
4. **Check of er een knop is "Switch to Visual Builder"**

### Als je Conversation Flow builder ziet:
1. **Maak een nieuwe node voor elke state:**
   - S0_GREETING (Welkom)
   - S1_INFO_ROUTER (Informatie)
   - S2_ORDER_START (Bestelling starten)
   - S3_TAKE_ORDER (Items opnemen)
   - S4_MENU_HELP (Menu hulp)
   - S5_RECAP (Samenvatting)
   - S6_CONFIRM (Bevestigen)
   - S7_HANDOFF (Doorverbinden)

2. **Configureer transitions tussen nodes:**
   - S0_GREETING → S1_INFO_ROUTER (als klant info vraagt)
   - S0_GREETING → S2_ORDER_START (als klant wil bestellen)
   - S2_ORDER_START → S3_TAKE_ORDER (als klant items noemt)
   - etc.

3. **Voeg tools toe aan elke node:**
   - S3_TAKE_ORDER: search_menu, add_to_cart, get_cart
   - S5_RECAP: get_cart, calculate_total
   - etc.

## Voordelen van Conversation Flow Builder:

✅ **Visueel overzicht** - Je ziet de hele flow in één oogopslag
✅ **Direct bewerkbaar** - Geen code nodig, direct in dashboard
✅ **Makkelijker te debuggen** - Zie direct welke node actief is
✅ **Betere controle** - Rigide transitions, minder "creatieve" LLM

## Nadelen:

❌ **Minder flexibel** - Moeilijker voor complexe logica
❌ **Geen versie controle** - Geen git, alleen dashboard
❌ **Moeilijker te automatiseren** - Geen API voor flow builder (waarschijnlijk)

## Aanbeveling:

Voor dit project (bestelling-opname met rommelige input):
- **Blijf bij States via API** als je flexibiliteit nodig hebt
- **Gebruik Conversation Flow** als je rigide controle wilt en minder flexibiliteit nodig hebt

Maar test eerst of Conversation Flow beter werkt voor jouw use-case!
