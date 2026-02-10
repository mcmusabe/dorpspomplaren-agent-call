"""
Voorbeeld webhook server implementatie voor Retell AI tools
Deze server implementeert alle custom tools voor de Dorpspomp agent

Gebruik: python webhook_example.py
Of deploy naar een cloud service zoals Render, Railway, of Vercel
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
from menu import MENU, search_item, get_item_price, format_price
from opening_hours import is_open_now, is_pickup_time_valid, get_next_opening

app = Flask(__name__)

# Simpele in-memory data store (in productie: gebruik database)
cart_store = {}  # {call_id: {items: [], pickup_time: None}}

# Convert MENU dictionary to flat list for compatibility
menu_items = []
for category, items in MENU.items():
    for item_name, price in items.items():
        if price is not None:  # Skip items without price
            menu_items.append({
                "id": item_name.lower().replace(" ", "_"),
                "name": item_name.title(),
                "price": price,
                "category": category
            })

BUSINESS_INFO = {
    "name": "De Dorpspomp & Dieks IJssalon",
    "address": "Holterweg 1, Laren (Gld)",
    "phone": None,
}

OPENING_HOURS = {
    "monday": {"open": None, "close": None, "closed": True},
    "tuesday": {"open": None, "close": None, "closed": True},
    "wednesday": {"open": "11:30", "close": "19:30", "closed": False},
    "thursday": {"open": "11:30", "close": "19:30", "closed": False},
    "friday": {"open": "11:30", "close": "20:00", "closed": False},
    "saturday": {"open": "11:30", "close": "20:00", "closed": False},
    "sunday": {"open": "11:30", "close": "20:00", "closed": False},
}

def get_call_id():
    """Haal call ID op uit request headers"""
    return request.headers.get("X-Retell-Call-ID", "default")

@app.route("/tools/business_info", methods=["GET"])
def get_business_info():
    """Retourneer bedrijfsinformatie"""
    return jsonify({
        "name": BUSINESS_INFO["name"],
        "address": BUSINESS_INFO["address"],
        "opening_hours": OPENING_HOURS
    })

@app.route("/tools/hours", methods=["GET"])
def get_hours():
    """Retourneer openingstijden en check of nu open"""
    # Check if currently open
    status = is_open_now()

    return jsonify({
        "currently_open": status.get("open", False),
        "status_message": status.get("reason", "Open"),
        "closes_at": status.get("closes_at"),
        "next_open": status.get("next_open"),
        "opens_at": status.get("opens_at")
    })

@app.route("/tools/check_pickup_time", methods=["GET"])
def check_pickup_time():
    """Check of een afhaaltijd geldig is"""
    pickup_time = request.args.get("pickup_time", "")

    if not pickup_time:
        return jsonify({"error": "pickup_time parameter required"}), 400

    result = is_pickup_time_valid(pickup_time)

    return jsonify({
        "valid": result["valid"],
        "message": result["reason"]
    })

@app.route("/tools/menu", methods=["GET"])
def get_menu():
    """Retourneer menu, optioneel gefilterd op categorie"""
    category = request.args.get("category")
    
    if category:
        items = [item for item in menu_items if item["category"] == category]
    else:
        items = menu_items
    
    return jsonify({
        "items": items,
        "total": len(items)
    })

@app.route("/tools/search_menu", methods=["GET"])
def search_menu_endpoint():
    """Zoek in het menu - gebruikt menu.py search_item functie"""
    query = request.args.get("query", "").lower()

    if not query:
        return jsonify({"items": [], "total": 0, "query": ""})

    # Gebruik de search_item functie uit menu.py
    results = search_item(query)

    # Als geen resultaten, return empty
    if not results:
        return jsonify({
            "items": [],
            "total": 0,
            "query": query,
            "message": f"Geen resultaten gevonden voor '{query}'"
        })

    # Format results voor Retell agent
    formatted_results = []
    for item in results:
        formatted_results.append({
            "name": item["name"],
            "price": item["price"],
            "price_formatted": format_price(item["price"]),
            "category": item["category"]
        })

    return jsonify({
        "items": formatted_results,
        "total": len(formatted_results),
        "query": query
    })

@app.route("/tools/add_to_cart", methods=["POST"])
def add_to_cart():
    """Voeg item toe aan winkelwagen"""
    data = request.json or {}
    call_id = get_call_id()
    
    if call_id not in cart_store:
        cart_store[call_id] = {"items": [], "pickup_time": None}
    
    item_name = data.get("item", "")
    quantity = int(data.get("quantity", 1))
    
    # Zoek item in menu
    menu_item = next((m for m in menu_items if m["name"].lower() == item_name.lower() or m["id"] == item_name.lower()), None)
    
    if not menu_item:
        return jsonify({"error": "Item niet gevonden", "item": item_name}), 404
    
    # Voeg toe aan cart
    cart_item = {
        "id": menu_item["id"],
        "name": menu_item["name"],
        "price": menu_item["price"],
        "quantity": quantity
    }
    
    cart_store[call_id]["items"].append(cart_item)
    
    return jsonify({
        "success": True,
        "item": cart_item,
        "cart_total": len(cart_store[call_id]["items"])
    })

@app.route("/tools/update_cart", methods=["POST"])
def update_cart():
    """Update winkelwagen item"""
    data = request.json or {}
    call_id = get_call_id()
    
    if call_id not in cart_store:
        return jsonify({"error": "Geen winkelwagen gevonden"}), 404
    
    item_id = data.get("item_id")
    quantity = int(data.get("quantity", 1))
    
    for item in cart_store[call_id]["items"]:
        if item["id"] == item_id:
            item["quantity"] = quantity
            return jsonify({"success": True, "item": item})
    
    return jsonify({"error": "Item niet gevonden in winkelwagen"}), 404

@app.route("/tools/remove_from_cart", methods=["POST"])
def remove_from_cart():
    """Verwijder item uit winkelwagen"""
    data = request.json or {}
    call_id = get_call_id()
    
    if call_id not in cart_store:
        return jsonify({"error": "Geen winkelwagen gevonden"}), 404
    
    item_id = data.get("item_id")
    
    cart_store[call_id]["items"] = [
        item for item in cart_store[call_id]["items"]
        if item["id"] != item_id
    ]
    
    return jsonify({"success": True, "cart_total": len(cart_store[call_id]["items"])})

@app.route("/tools/cart", methods=["GET"])
def get_cart():
    """Haal huidige winkelwagen op"""
    call_id = get_call_id()
    
    if call_id not in cart_store:
        cart_store[call_id] = {"items": [], "pickup_time": None}
    
    cart = cart_store[call_id]
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    
    return jsonify({
        "items": cart["items"],
        "pickup_time": cart["pickup_time"],
        "total": round(total, 2),
        "item_count": len(cart["items"])
    })

@app.route("/tools/calculate_total", methods=["GET"])
def calculate_total():
    """Bereken totaalprijs"""
    call_id = get_call_id()
    
    if call_id not in cart_store:
        return jsonify({"total": 0.0, "item_count": 0})
    
    cart = cart_store[call_id]
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    
    return jsonify({
        "total": round(total, 2),
        "item_count": len(cart["items"])
    })

@app.route("/tools/confirm_order", methods=["POST"])
def confirm_order():
    """Bevestig bestelling"""
    data = request.json or {}
    call_id = get_call_id()
    
    if call_id not in cart_store:
        return jsonify({"error": "Geen winkelwagen gevonden"}), 404
    
    pickup_time = data.get("pickup_time", "")
    cart_store[call_id]["pickup_time"] = pickup_time
    
    cart = cart_store[call_id]
    total = sum(item["price"] * item["quantity"] for item in cart["items"])
    
    # In productie: sla bestelling op in database
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return jsonify({
        "success": True,
        "order_id": order_id,
        "items": cart["items"],
        "pickup_time": pickup_time,
        "total": round(total, 2)
    })

@app.route("/tools/handoff", methods=["POST"])
def handoff():
    """Handoff naar medewerker"""
    data = request.json or {}
    call_id = get_call_id()
    
    reason = data.get("reason", "Klant vraagt om medewerker")
    summary = data.get("summary", "")
    
    # In productie: log handoff en bereid voor op doorverbinden
    return jsonify({
        "success": True,
        "reason": reason,
        "summary": summary,
        "message": "Doorverbinden naar medewerker..."
    })

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "dorpspomp-retell-webhook"})

if __name__ == "__main__":
    print("Starting webhook server on http://localhost:5000")
    print("Endpoints available:")
    print("  GET  /tools/business_info")
    print("  GET  /tools/hours?date=YYYY-MM-DD")
    print("  GET  /tools/menu?category=...")
    print("  GET  /tools/search_menu?query=...")
    print("  POST /tools/add_to_cart")
    print("  POST /tools/update_cart")
    print("  POST /tools/remove_from_cart")
    print("  GET  /tools/cart")
    print("  GET  /tools/calculate_total")
    print("  POST /tools/confirm_order")
    print("  POST /tools/handoff")
    print("  GET  /health")
    app.run(host="0.0.0.0", port=5000, debug=True)

