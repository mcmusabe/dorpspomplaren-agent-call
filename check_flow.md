# Flow Visibility Checklist

## ✅ States zijn correct geformatteerd
- 8 states aanwezig
- Alle tools hebben parameters
- Alle edges zijn geldig

## 📍 Waar vind je de Flow in Retell Dashboard?

1. **Ga naar je agent dashboard:**
   ```
   https://dashboard.retellai.com/agents/{agent_id}
   ```

2. **Zoek de Flow tab:**
   - **Optie 1:** Klik op tab "Flow" of "States" bovenaan
   - **Optie 2:** Ga naar "LLM Settings" → scroll naar "States" sectie
   - **Optie 3:** Ga naar "Configuration" → "Flow"
   - **Optie 4:** Klik op "Edit" bij de LLM → zie "States" sectie

3. **Als de flow leeg is:**
   - Deploy de agent opnieuw: `python3 deploy_agent.py`
   - Refresh de pagina (Ctrl+R / Cmd+R)
   - Check of je de juiste agent versie bekijkt
   - Open browser console (F12) voor errors

## 🔍 Debug: Check of states zijn doorgegeven

Na `python3 deploy_agent.py` zou je moeten zien:
```
📊 STATES DEBUG INFO:
   Total states: 8
   Starting state: S0_GREETING
   State 1: S0_GREETING - 0 tools, 2 edges
   State 2: S1_INFO_ROUTER - 6 tools, 2 edges
   ...
```

Als je deze output NIET ziet, dan worden de states niet correct doorgegeven.

## 🎯 Expected Flow Structure

```
S0_GREETING (Starting State)
  ├─→ S1_INFO_ROUTER
  └─→ S2_ORDER_START
       ├─→ S3_TAKE_ORDER
       │    ├─→ S4_MENU_HELP
       │    └─→ S5_RECAP
       │         └─→ S6_CONFIRM
       └─→ S4_MENU_HELP
            └─→ S7_HANDOFF
```

## ⚠️ Als flow nog steeds niet zichtbaar is:

1. Check Retell API versie - misschien is er een format wijziging
2. Check of states parameter wordt geaccepteerd door Retell SDK
3. Probeer een simpele state eerst (1 state met 1 edge) om te testen
4. Check Retell dashboard logs voor errors
