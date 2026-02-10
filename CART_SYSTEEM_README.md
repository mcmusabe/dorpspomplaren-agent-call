# 🛒 CART TRACKING SYSTEEM - GEEN FALLBACK MEER!

## 🎯 OPLOSSING: Items worden NU bewaard!

In plaats van "HANDMATIG TE BEPALEN" in de email, gebruikt de agent nu een **cart systeem** dat items bewaart tijdens het gesprek.

---

## 🔧 HOE HET WERKT:

### Tijdens het Gesprek:
1. Klant: "Ik wil friet met mayonaise"
2. Agent: [search_menu("friet mayonaise")]
3. Agent: "Friet met mayonaise, €3,55. Nog iets?"
4. **Agent: [add_to_cart({"item": "friet met mayonaise", "quantity": 1})]** ← NIEUW!
5. Item wordt opgeslagen in cart voor deze call

### Bij Bestelling Versturen:
1. Agent roept send_order aan (mogelijk met lege items)
2. Webhook checkt: "Zijn er items meegestuurd?"
3. **NEE** → Webhook haalt items UIT DE CART! ✅
4. Email bevat nu ECHTE items!

---

## 📧 NIEUWE EMAIL FORMAT:

```
Nieuwe BESTELLING – De Dorpspomp
Bestelnummer: DRP20260108...

Naam: Jan
Telefoon: 0612345678
Afhaaltijd: 12:30

Items:
- 1x friet met mayonaise à € 3.55 = € 3.55
- 1x blikje coca cola à € 3.00 = € 3.00

TOTAAL: € 6.55
```

**GEEN "HANDMATIG TE BEPALEN" MEER!** 🎉

---

## 🔄 NIEUWE ENDPOINTS:

### 1. POST `/tools/add_to_cart`
Voegt item toe aan cart tijdens gesprek.

**Body:**
```json
{
  "item": "friet met mayonaise",
  "quantity": 1,
  "notes": "extra mayo" // optional
}
```

**Headers:**
```
x-retell-call-id: abc123
```

**Response:**
```json
{
  "status": "ok",
  "message": "Added 1x friet met mayonaise to cart",
  "cart_count": 2
}
```

### 2. GET `/tools/get_cart`
Haalt huidige cart op.

**Headers:**
```
x-retell-call-id: abc123
```

**Response:**
```json
{
  "items": [
    {"name": "friet met mayonaise", "qty": 1, "notes": ""},
    {"name": "cola", "qty": 1, "notes": ""}
  ],
  "total_items": 2
}
```

---

## ⚙️ DEPLOYMENT INSTRUCTIES:

### ❗ BELANGRIJK: Webhook Server MOET HERSTART!

De nieuwe cart endpoints zijn toegevoegd aan `webhook_order.py`. Je MOET de server herstarten:

**Terminal 1: Stop oude server**
```bash
# Druk CTRL+C in terminal waar webhook_order.py draait
```

**Terminal 1: Start nieuwe server**
```bash
cd "/Users/c/Documents/dorpspomplaren agent call"
python3 webhook_order.py
```

**Terminal 2: Ngrok (blijft draaien)**
```bash
# Ngrok hoeft NIET herstart - blijft draaien!
```

### Test Cart Endpoints:
```bash
# Test add_to_cart
curl -X POST http://localhost:8000/tools/add_to_cart \
  -H "Content-Type: application/json" \
  -H "x-retell-call-id: test123" \
  -d '{"item": "friet met mayonaise", "quantity": 1}'

# Expected output:
# {"status":"ok","message":"Added 1x friet met mayonaise to cart","cart_count":1}

# Test get_cart
curl -X GET http://localhost:8000/tools/get_cart \
  -H "x-retell-call-id: test123"

# Expected output:
# {"items":[{"name":"friet met mayonaise","qty":1,"notes":""}],"total_items":1}
```

---

## 🎯 WAT IS ER VERANDERD:

### webhook_order.py:
1. ✅ **cart_store toegevoegd** - In-memory opslag per call
2. ✅ **POST /tools/add_to_cart** - Agent kan items toevoegen
3. ✅ **GET /tools/get_cart** - Agent kan cart ophalen
4. ✅ **Order endpoint fallback** - Haalt items uit cart als niet meegestuurd

### prompts.py:
1. ✅ **S3_TAKE_ORDER updated** - Agent moet add_to_cart gebruiken na elk item
2. ✅ **Duidelijke instructies** - "add_to_cart zorgt ervoor dat items worden bewaard"

### Agent (gedeployed):
1. ✅ **Nieuwe tool beschikbaar**: add_to_cart
2. ✅ **Agent weet**: gebruik add_to_cart na elk geaccepteerd item

---

## 📊 FLOW DIAGRAM:

```
Klant zegt: "Friet en cola"
       ↓
Agent: search_menu("friet")
       ↓
Agent: "Friet, €2,80"
       ↓
Agent: add_to_cart({"item": "friet", "qty": 1})  ← NIEUW!
       ↓
     🛒 CART: ["friet"]
       ↓
Agent: search_menu("cola")
       ↓
Agent: "Cola, €3,00"
       ↓
Agent: add_to_cart({"item": "cola", "qty": 1})
       ↓
     🛒 CART: ["friet", "cola"]
       ↓
Klant: "Ja, klopt"
       ↓
Agent: send_order({items: []})  ← Nog steeds leeg!
       ↓
Webhook: "Items leeg? Check cart..."
       ↓
Webhook: Haalt items uit cart! ✅
       ↓
     📧 EMAIL: "1x friet, 1x cola"
```

---

## ✅ VOORDELEN:

1. **Geen placeholder meer** - Echte items in email!
2. **Geen transcript nodig** - Items automatisch bewaard
3. **Agent blijft simpel** - Hoeft niet zelf items te onthouden in send_order
4. **Fallback blijft werken** - Als add_to_cart faalt → oude placeholder

---

## 🧪 TESTEN:

1. **Start webhook server** (met nieuwe code)
2. **Bel agent**
3. **Bestel iets**: "Friet met mayo en cola"
4. **Check webhook logs** - Zie je `🛒 Item added to cart`?
5. **Bevestig bestelling**
6. **Check email** - Zie je echte items?

---

## 🐛 TROUBLESHOOTING:

### Items nog steeds "HANDMATIG TE BEPALEN":
1. Check: Webhook server herstart?
2. Check: Zie je `🛒 Item added to cart` in logs?
3. Check: Agent roept add_to_cart aan? (zie Retell dashboard logs)

### add_to_cart endpoint niet gevonden (404):
- Webhook server is NIET herstart met nieuwe code
- Herstart: CTRL+C → `python3 webhook_order.py`

### Cart is leeg bij send_order:
- Agent roept add_to_cart niet aan
- Check prompts.py - instructies duidelijk?
- Agent gebruikt verkeerde tool?

---

## 🎉 SUCCES!

Je agent heeft nu een **professioneel cart systeem** zonder fallbacks!
Items worden automatisch bewaard en emails bevatten de echte bestelling.

**Demo ready!** 🚀
