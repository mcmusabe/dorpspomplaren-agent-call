# 🎯 DEMO CHECKLIST - 12:00 UUR

**Agent Status**: ✅ LIVE
**Agent ID**: agent_5c757c39c9a255626773ce7ba3
**Dashboard**: https://dashboard.retellai.com/agents/agent_5c757c39c9a255626773ce7ba3

---

## ⚠️ BEKEND PROBLEEM - BELANGRIJK!

**De agent kan items NIET betrouwbaar onthouden in de tool call.**

Dit betekent:
- ✅ Gesprek werkt perfect (menu validatie, synoniemen, prijzen vertellen)
- ✅ Email komt aan met bestelnummer
- ❌ **MAAR**: Email bevat "HANDMATIG TE BEPALEN" in plaats van echte items

### Oplossing voor demo:
**Luister het gesprek terug in Retell dashboard** om te horen wat klant bestelde:
1. Open: https://dashboard.retellai.com/
2. Klik op de call
3. Luister transcript terug
4. Noteer items handmatig

---

## ✅ WAT WERKT WEL:

### 1. Menu Validatie ✅
- Agent checkt ALTIJD of item in menu staat
- Synoniemen werken: "patat" = "friet", "kroket" gevonden
- "Bier" wordt afgewezen (niet in menu)

### 2. Prijzen ✅
- Agent vertelt prijzen: "Friet, €2,80. Nog iets?"
- Agent kent alle menu items + prijzen
- Search functie werkt perfect

### 3. Openingstijden ✅
- Agent valideert afhaaltijd
- "We sluiten om 19:30. Eerder ophalen?"
- Biedt alternatieve tijden aan

### 4. Gesprek Flow ✅
- Natuurlijk Nederlands
- Korte, directe zinnen
- Snelle responses (voice speed 1.2x)
- Jennifer stem (ElevenLabs)

### 5. Email Notificatie ✅
- Email komt aan bij jou
- Bevat bestelnummer (DRP...)
- Bevat timestamp
- **MAAR**: Items zijn placeholder

---

## 📋 PRE-DEMO CHECKLIST

### Servers (START DEZE!):
```bash
# Terminal 1: Webhook Server
cd "/Users/c/Documents/dorpspomplaren agent call"
python3 webhook_order.py

# Terminal 2: Ngrok (als niet al draait)
ngrok http 8000
```

### Checklist:
- [ ] Webhook server draait (localhost:8000)
- [ ] Ngrok tunnel actief (`https://237729bb1e8f.ngrok-free.app`)
- [ ] Agent ID correct: `agent_5c757c39c9a255626773ce7ba3`
- [ ] Email ontvangst getest
- [ ] Dashboard open in browser

---

## 🎬 DEMO SCENARIOS

### Scenario 1: Simpele Bestelling (BESTE VOOR DEMO)
```
Klant: "Hallo"
Agent: "Hoi, de Dorpspomp. Waarmee?"

Klant: "Ik wil bestellen"
Agent: "Prima! Wat wil je?"

Klant: "Patat met mayonaise en een cola"
Agent: "Friet met mayonaise, €3,55. Nog iets?"
Agent: "Cola, €3,00. Nog iets?"

Klant: "Nee"
Agent: "Wanneer ophalen?"

Klant: "Om 12:30"
Agent: [checks tijd] "12:30 is goed. Klopt dat?"

Klant: "Ja"
Agent: "Top, je bestelling is genoteerd!"
```

**RESULTAAT**:
- ✅ Gesprek klinkt natuurlijk
- ✅ Prijzen worden verteld
- ✅ Synoniemen werken (patat → friet)
- ✅ Email komt aan
- ⚠️ Check transcript voor echte items

### Scenario 2: Item NIET in Menu (Laat zien hoe validation werkt)
```
Klant: "Hebben jullie bier?"
Agent: "Sorry, we hebben geen bier."
```

### Scenario 3: Buiten Openingstijden
```
Klant: "Ik wil bestellen voor 22:00"
Agent: "We sluiten om 19:30. Kun je het eerder ophalen?"
```

---

## 🔧 ALS IETS FOUT GAAT

### Agent zegt "Het systeem werkt niet":
1. Check webhook logs in terminal
2. Check ngrok URL in config.py
3. Herstart webhook server
4. Redeploy agent: `python3 deploy_agent.py`

### Agent lag/stopt midden in zin:
- ✅ **GEFIXT**: max_tokens verhoogd naar 300

### Agent accepteert items die niet bestaan:
- Agent zou dit NIET moeten doen (search_menu validation)
- Check logs om te zien of search_menu wordt aangeroepen

### Email komt niet aan:
- Check GMAIL_USER + GMAIL_APP_PASSWORD in .env
- Check webhook logs voor email errors

---

## 💡 DEMO TIPS

### DO's:
1. ✅ Laat natuurlijk gesprek zien (patat, kroketje)
2. ✅ Laat prijzen zien ("Agent vertelt direct de prijs!")
3. ✅ Laat menu validatie zien ("Bier? Nee!")
4. ✅ Laat openingstijden validatie zien
5. ✅ Leg uit: "Items worden nog handmatig genoteerd via transcript"

### DON'Ts:
1. ❌ Niet te lang gesprek (max 2 min)
2. ❌ Niet te veel items bestellen (houdt het simpel)
3. ❌ Verwacht niet dat items automatisch in email staan

---

## 🎯 DEMO PITCH

**WAT WERKT**:
> "De agent herkent natuurlijk Nederlands (patat = friet), valideert menu items in real-time, vertelt prijzen, en checkt openingstijden. Het gesprek is snel, natuurlijk, en professioneel."

**WAT NOG KOMT**:
> "Op dit moment noteer je items handmatig via het transcript. In de volgende versie komt automatische item tracking zodat de email direct de complete bestelling bevat."

---

## 📞 SUPPORT

**Agent Dashboard**: https://dashboard.retellai.com/agents/agent_5c757c39c9a255626773ce7ba3
**Ngrok URL**: https://237729bb1e8f.ngrok-free.app
**Webhook URL**: http://localhost:8000

**Model**: GPT-4o (beste kwaliteit)
**Voice**: Jennifer - Pleasant Dutch
**Speed**: 1.2x (20% sneller voor natuurlijker gesprek)

---

## ✅ LAATSTE CHECK

- [ ] Servers draaien
- [ ] Test call gedaan
- [ ] Email ontvangen
- [ ] Transcript gecheckt
- [ ] Dashboard open
- [ ] READY FOR DEMO! 🚀

**Succes met de demo om 12:00!** 🎉
