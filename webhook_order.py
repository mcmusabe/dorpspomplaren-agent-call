from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import re
import html
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from menu import calculate_order_total, format_price, format_price_spoken, search_item, smart_search_item, get_item_price, get_item_with_price, MENU
from opening_hours import is_open_now, is_pickup_time_valid, get_next_opening, now_nl

# Thread pool voor async email
_email_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="email_")

# Environment check voor production/development mode
IS_PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"
LOG_LEVEL = logging.WARNING if IS_PRODUCTION else logging.INFO

# Setup logging - minder verbose in production
_log_handlers = [logging.StreamHandler()]
try:
    _log_handlers.append(logging.FileHandler('webhook_order.log'))
except OSError:
    pass  # Read-only filesystem (Vercel)

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s' if IS_PRODUCTION else '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=_log_handlers
)
logger = logging.getLogger(__name__)


def debug_log(message: str):
    """Log alleen in development mode"""
    if not IS_PRODUCTION:
        logger.info(message)


def debug_print(message: str):
    """Print alleen in development mode"""
    if not IS_PRODUCTION:
        print(message)

# Call analytics tracker
call_analytics = {}

# Business informatie (lokaal gedefinieerd om niet afhankelijk te zijn van RETELL_API_KEY)
BUSINESS_INFO = {
    "name": "De Dorpspomp & Dieks IJssalon",
    "address": "Holterweg 1, Laren (Gld)",
    "phone": None,
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

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 In-memory cart store - Items worden hier bewaard tijdens het gesprek
# Format: {call_id: {"items": [...], "customer_name": str, "phone": str, "pickup_time": str, "created_at": datetime}}
cart_store: Dict[str, Dict] = {}
cart_store_lock = threading.Lock()

# Cart cleanup configuratie
CART_EXPIRY_MINUTES = 60  # Carts ouder dan 60 min worden verwijderd
_last_cleanup = now_nl()

# Velden die we nooit aan de spraakagent willen tonen
VOICE_HIDDEN_PRICE_KEYS = {
    "price",
    "price_formatted",
    "price_spoken",
    "total",
    "total_formatted",
    "total_spoken",
    "formatted_total",
    "spoken_total",
    "subtotal",
    "price_per_item",
}


def _cleanup_old_carts():
    """Verwijder verlopen carts (ouder dan CART_EXPIRY_MINUTES)"""
    global _last_cleanup

    now = now_nl()

    # Alleen cleanup elke 5 minuten
    if (now - _last_cleanup).total_seconds() < 300:
        return

    _last_cleanup = now
    expiry_threshold = now - timedelta(minutes=CART_EXPIRY_MINUTES)

    with cart_store_lock:
        expired_keys = [
            key for key, cart in cart_store.items()
            if cart.get("created_at", now) < expiry_threshold
        ]

        for key in expired_keys:
            del cart_store[key]

        if expired_keys:
            logger.info(f"🧹 Cleaned up {len(expired_keys)} expired carts")

def detect_platform(request: Request, body: Dict[str, Any] = None) -> str:
    """
    Detecteer of request van VAPI of Retell komt

    VAPI kenmerken:
    - Header: x-vapi-secret
    - Body: message.type, toolCallList, call.id

    Retell kenmerken:
    - Header: x-retell-call-id
    - Body: args wrapper, tool_call wrapper
    """
    # Check headers eerst
    if request.headers.get("x-vapi-secret"):
        return "vapi"
    if request.headers.get("x-retell-call-id"):
        return "retell"

    # Check body structure
    if body:
        # VAPI heeft message.type of toolCallList
        if "message" in body and isinstance(body["message"], dict):
            if "type" in body["message"] or "toolCallList" in body["message"]:
                return "vapi"
        # VAPI call object
        if "call" in body and isinstance(body["call"], dict):
            if "id" in body["call"]:
                return "vapi"

    # Default naar retell
    return "retell"


def get_call_id(request: Request, platform: str = None, body: Dict[str, Any] = None) -> str:
    """
    Haal call ID op, rekening houdend met platform

    Retell: x-retell-call-id header
    VAPI: call.id in body of x-vapi-call-id header
    """
    # Accepteer VAPI call-id header altijd (ook op generieke /tools/* endpoints)
    vapi_call_id = request.headers.get("x-vapi-call-id")
    if vapi_call_id:
        return vapi_call_id

    if platform == "vapi":
        # VAPI: probeer body
        if body and "call" in body:
            call_obj = body.get("call", {})
            if isinstance(call_obj, dict) and "id" in call_obj:
                return call_obj["id"]
        return "vapi-unknown"

    # Retell (default)
    return request.headers.get("x-retell-call-id", "unknown")


def coerce_quantity(raw_qty: Any, default: int = 1) -> int:
    """Maak quantity robuust voor ints/strings zoals '3', '3x', 'drie'."""
    if isinstance(raw_qty, bool):
        return default
    if isinstance(raw_qty, int):
        return max(1, raw_qty)
    if isinstance(raw_qty, float):
        return max(1, int(raw_qty))
    if isinstance(raw_qty, str):
        text = raw_qty.strip().lower()
        if not text:
            return default

        word_map = {
            "een": 1, "eentje": 1,
            "twee": 2, "drie": 3, "vier": 4, "vijf": 5,
            "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10
        }
        if text in word_map:
            return word_map[text]

        match = re.search(r"\d+", text)
        if match:
            try:
                return max(1, int(match.group(0)))
            except Exception:
                return default
    return default


def coerce_price(raw_price: Any, default: float = 0.0) -> float:
    """Maak prijs veilig numeriek voor totaalsommen."""
    try:
        if raw_price is None:
            return default
        return float(raw_price)
    except Exception:
        return default


def normalize_cart_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normaliseer qty/price velden zodat cart-berekeningen niet crashen."""
    normalized: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        qty = coerce_quantity(item.get("qty", item.get("quantity", 1)))
        price = coerce_price(item.get("price", 0.0))
        normalized.append({**item, "qty": qty, "price": price})
    return normalized


def compute_cart_total(items: List[Dict[str, Any]]) -> float:
    """Bereken cart totaal met genormaliseerde waarden."""
    return sum(coerce_price(item.get("price", 0.0)) * coerce_quantity(item.get("qty", 1)) for item in items)


def strip_voice_price_fields(value: Any) -> Any:
    """Verwijder prijsgerelateerde velden uit payloads die naar VAPI teruggaan."""
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key in VOICE_HIDDEN_PRICE_KEYS:
                continue
            sanitized[key] = strip_voice_price_fields(item)
        return sanitized
    if isinstance(value, list):
        return [strip_voice_price_fields(item) for item in value]
    return value


def sanitize_string(text: str, max_length: int = 200) -> str:
    """Sanitize user input om email injection te voorkomen"""
    if not text:
        return ""
    # Remove control characters and newlines (email injection prevention)
    text = re.sub(r'[\r\n\t]', ' ', str(text))
    # HTML escape voor veiligheid
    text = html.escape(text)
    # Trim tot max length
    return text[:max_length].strip()

def validate_phone(phone: str) -> bool:
    """Valideer Nederlands telefoonnummer (basis validatie)"""
    if not phone:
        return True  # Phone is optional
    # Remove spaces and dashes
    clean = phone.replace(" ", "").replace("-", "").replace("+31", "0")
    # Check if it's a valid Dutch number (10 digits starting with 0, or mobile)
    return clean.isdigit() and len(clean) == 10 and clean[0] == "0"

def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliseer Retell tool payload naar verwacht format
    
    Retell stuurt in 3 verschillende formaten:
    1. Direct: {"customer_name": "...", "items": [...]}
    2. Wrapped: {"args": {"customer_name": "...", "items": [...]}}
    3. Arguments string: {"arguments": "{\"customer_name\":\"...\",\"items\":[...]}"}
    
    Deze functie normaliseert naar:
    {
      "customer_name": string or "",
      "phone": string or "",
      "pickup_time": "HH:MM",
      "items": [{"name": str, "qty": int, "notes": str or None}],
      "extra_notes": string or None
    }
    """
    # Handle 3 different formats:
    
    # Format 1: Check for "args" wrapper
    if "args" in payload and isinstance(payload["args"], dict):
        payload = payload["args"]
    
    # Format 2: Check for "tool_call" wrapper
    elif "tool_call" in payload:
        if "arguments" in payload["tool_call"]:
            args = payload["tool_call"]["arguments"]
            if isinstance(args, str):
                try:
                    payload = json.loads(args)
                except:
                    payload = {}
            elif isinstance(args, dict):
                payload = args
        else:
            payload = payload.get("tool_call", {})
    
    # Format 3: Check for "arguments" (string or dict)
    elif "arguments" in payload:
        args = payload["arguments"]
        if isinstance(args, str):
            try:
                payload = json.loads(args)
            except:
                # If parsing fails, try to extract from string
                payload = {}
        elif isinstance(args, dict):
            payload = args
    
    # Now payload should be in direct format
    # Normalize to expected format with sanitization
    normalized = {
        "customer_name": sanitize_string(payload.get("customer_name", "") or "", max_length=100),
        "phone": sanitize_string(payload.get("phone", "") or "", max_length=20),
        "pickup_time": sanitize_string(payload.get("pickup_time", ""), max_length=10),
        "items": [],
        "extra_notes": sanitize_string(payload.get("extra_notes") or "", max_length=500)
    }
    
    # Normalize items
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    
    for item in items:
        if isinstance(item, dict):
            # Convert qty to integer if it's a string
            qty = item.get("qty")
            if isinstance(qty, str):
                try:
                    qty = int(qty)
                except:
                    qty = 1
            elif not isinstance(qty, int):
                qty = 1
            
            normalized["items"].append({
                "name": sanitize_string(str(item.get("name", "")), max_length=100),
                "qty": max(1, qty),  # Ensure at least 1
                "notes": sanitize_string(item.get("notes") or "", max_length=200) if item.get("notes") else None
            })
    
    return normalized

class OrderItem(BaseModel):
    name: str
    qty: int = Field(ge=1)
    notes: Optional[str] = None

class Order(BaseModel):
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    pickup_time: Optional[str] = None
    items: List[OrderItem]
    extra_notes: Optional[str] = None

def _send_email_sync(subject: str, body: str, order_id: str = "unknown") -> bool:
    """Synchrone email verzending (voor gebruik in thread pool)"""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    to_email = os.getenv("ORDER_TO_EMAIL", gmail_user)

    if not gmail_user or not gmail_pass:
        logger.error(f"[{order_id}] Missing GMAIL_USER or GMAIL_APP_PASSWORD")
        return False

    # Remove spaces from app password if present
    gmail_pass = gmail_pass.replace(" ", "")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        logger.info(f"✅ [{order_id}] Email sent successfully")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ [{order_id}] Gmail auth failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ [{order_id}] Email failed: {e}")
        return False


def send_email(subject: str, body: str):
    """Legacy sync versie voor backwards compatibility"""
    return _send_email_sync(subject, body)


async def send_email_async(subject: str, body: str, order_id: str = "unknown") -> bool:
    """
    ASYNC email verzending - blokkeert niet de main thread!
    Gebruikt ThreadPoolExecutor voor SMTP (die blocking is)
    """
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _email_executor,
            _send_email_sync,
            subject,
            body,
            order_id
        )
        return result
    except Exception as e:
        logger.error(f"❌ [{order_id}] Async email error: {e}")
        return False


def send_email_background(subject: str, body: str, order_id: str = "unknown"):
    """
    Fire-and-forget email verzending in background thread.
    Returned DIRECT zonder te wachten op email.
    """
    def _send():
        _send_email_sync(subject, body, order_id)

    _email_executor.submit(_send)
    logger.info(f"📤 [{order_id}] Email queued for background delivery")

@app.post("/order")
async def receive_order(request: Request):
    """Receive order from Retell agent - with logging and normalization"""
    try:
        # Get raw request body for logging
        raw_body = await request.body()
        raw_json = json.loads(raw_body) if raw_body else {}
        
        # RAW JSON PAYLOAD - Log complete payload for debugging
        logger.info("=" * 60)
        logger.info("📥 RAW JSON PAYLOAD (COMPLETE):")
        logger.info(json.dumps(raw_json, indent=2, ensure_ascii=False))
        logger.info("=" * 60)
        
        # Log what Retell sent (only in development)
        if not IS_PRODUCTION:
            print("📥 RETELL PAYLOAD RECEIVED (FILTERED):")
            print("=" * 60)
            log_safe = {
                "customer_name": raw_json.get("customer_name", "N/A"),
                "phone": raw_json.get("phone", "N/A")[:3] + "***" if raw_json.get("phone") else "N/A",
                "pickup_time": raw_json.get("pickup_time", "N/A"),
                "items_count": len(raw_json.get("items", [])),
                "items": raw_json.get("items", []),
                "extra_notes": raw_json.get("extra_notes", "N/A")
            }
            print(json.dumps(log_safe, indent=2, ensure_ascii=False))
            print("=" * 60)

        # Normalize payload (handles Retell quirks)
        normalized = normalize_payload(raw_json)

        if not IS_PRODUCTION:
            print("📦 NORMALIZED PAYLOAD:")
            print(json.dumps({
                "customer_name": normalized.get("customer_name"),
                "phone": normalized.get("phone", "")[:3] + "***" if normalized.get("phone") else "",
                "pickup_time": normalized.get("pickup_time"),
                "items_count": len(normalized.get("items", [])),
                "items": normalized.get("items", [])
            }, indent=2, ensure_ascii=False))
            print("=" * 60)
        
        # Validate normalized payload - FAIL FAST zonder placeholders
        if not normalized.get("items") or len(normalized["items"]) == 0:
            # 🔥 FALLBACK: Haal items UIT DE CART als agent ze niet meestuurt!
            call_id = request.headers.get("x-retell-call-id", "unknown")
            logger.warning(f"⚠️  WARNING: Items array is empty! Checking cart for call [{call_id}]...")

            if call_id in cart_store and cart_store[call_id]["items"]:
                # Items gevonden in cart!
                normalized["items"] = cart_store[call_id]["items"]
                logger.info(f"✅ Found {len(normalized['items'])} items in cart!")
                items_list = [f"{item['qty']}x {item['name']}" for item in normalized['items']]
                logger.info(f"   Items: {items_list}")
            else:
                # Geen items in cart - FAIL expliciet
                logger.error(f"❌ No items in order payload and no cart found for call [{call_id}]")
                raise HTTPException(
                    status_code=400,
                    detail="Geen items in bestelling. De agent moet items meesturen via de cart."
                )

        if not normalized.get("pickup_time") or normalized.get("pickup_time") == "N/A":
            # FAIL expliciet bij ontbrekende tijd
            logger.error(f"⚠️  ERROR: pickup_time missing in order!")
            raise HTTPException(
                status_code=400,
                detail="Afhaaltijd ontbreekt. De agent moet een geldige afhaaltijd vragen (HH:MM format)."
            )

        # Validate phone number if provided
        phone = normalized.get("phone")
        if phone and not validate_phone(phone):
            raise HTTPException(status_code=400, detail="Ongeldig telefoonnummer. Gebruik een Nederlands nummer (bijv. 0612345678)")
        
        # Generate Order ID
        order_id = f"DRP{now_nl().strftime('%Y%m%d%H%M%S')}"

        # Calculate prices
        pricing = calculate_order_total(normalized["items"])

        # Create email body
        lines = []
        lines.append("Nieuwe BESTELLING – De Dorpspomp & Dieks IJssalon")
        lines.append(f"Bestelnummer: {order_id}")
        lines.append(f"Tijd: {now_nl().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Naam: {normalized.get('customer_name') or '-'}")
        lines.append(f"Telefoon: {normalized.get('phone') or '-'}")
        lines.append(f"Afhaaltijd: {normalized.get('pickup_time') or '-'}")
        lines.append("")
        lines.append("Items:")
        for item in pricing["items"]:
            note = ""
            # Find notes from original items
            for orig in normalized["items"]:
                if orig["name"].lower() == item["name"].lower():
                    if orig.get("notes"):
                        note = f" ({orig['notes']})"
                    break

            # Format price info
            if item["price_per_item"] is not None:
                price_info = f" à {format_price(item['price_per_item'])} = {format_price(item['subtotal'])}"
            else:
                price_info = " (prijs onbekend)"

            lines.append(f"- {item['qty']}x {item['name']}{note}{price_info}")

        lines.append("")
        lines.append(f"TOTAAL: {pricing['formatted_total']}")

        if normalized.get("extra_notes"):
            lines.append("")
            lines.append(f"Opmerking: {normalized['extra_notes']}")

        body = "\n".join(lines)

        # 🚀 ASYNC email - blokkeert niet! Order response gaat direct terug
        send_email_background("NIEUWE BESTELLING – De Dorpspomp", body, order_id)

        return {
            "status": "ok",
            "message": "Bestelling ontvangen en e-mail verzonden",
            "order_id": order_id,
            "total": pricing["formatted_total"],
            "email_status": "sent"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ERROR in receive_order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"status": "ok", "service": "De Dorpspomp & Dieks IJssalon - Webhook API", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "dorpspomp-order-webhook"}


@app.post("/")
async def vapi_server_webhook(request: Request):
    """
    VAPI Server URL endpoint - ontvangt alle server events
    
    VAPI stuurt hier events zoals:
    - assistant-request: vraagt om assistant configuratie
    - function-call: tool calls (als geen specifieke tool URL)
    - status-update: call status updates
    - end-of-call-report: call beëindigd
    - tool-calls: tool call requests
    """
    try:
        raw_body = await request.body()
        body = json.loads(raw_body) if raw_body else {}
        
        message = body.get("message", {})
        message_type = message.get("type", "unknown")
        
        logger.info(f"[VAPI Server] Received event: {message_type}")
        
        # Handle tool-calls via server URL
        if message_type == "tool-calls":
            tool_calls = message.get("toolCallList", [])
            results = []
            
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_id = tc.get("id", "unknown")
                params = tc.get("parameters", {})
                
                logger.info(f"[VAPI Server] Tool call: {tool_name} with params: {params}")
                
                # Route naar juiste handler
                if tool_name == "search_menu":
                    query = params.get("query", "")
                    if query:
                        items = smart_search_item(query.lower())
                        formatted = [
                            {
                                "name": i["name"],
                                "price": i["price"],
                                "category": i["category"],
                                "price_formatted": format_price(i["price"]),
                                "price_spoken": format_price_spoken(i["price"])
                            }
                            for i in items
                        ]
                        result = {"items": formatted, "total": len(formatted), "query": query}
                    else:
                        result = {"items": [], "total": 0, "query": "", "message": "Geen zoekterm"}
                    results.append({"toolCallId": tool_id, "result": result})
                    
                elif tool_name == "add_to_cart":
                    call_id = body.get("call", {}).get("id", "vapi-server")
                    item_name = params.get("item", "")
                    qty = coerce_quantity(params.get("quantity", 1))
                    notes = params.get("notes", "")

                    _cleanup_old_carts()

                    with cart_store_lock:
                        if call_id not in cart_store:
                            cart_store[call_id] = {
                                "items": [],
                                "customer_name": "",
                                "phone": "",
                                "pickup_time": "",
                                "created_at": now_nl()
                            }

                    item_data = get_item_with_price(item_name)
                    if not item_data:
                        result = {
                            "status": "not_found",
                            "message": f"'{item_name}' staat niet op het menu. Vraag de klant om het anders te omschrijven."
                        }
                        results.append({"toolCallId": tool_id, "result": result})
                        continue

                    final_name = item_data["name"]
                    price = item_data["price"]

                    with cart_store_lock:
                        found = False
                        for cart_item in cart_store[call_id]["items"]:
                            if cart_item["name"].lower() == final_name.lower():
                                cart_item["qty"] = coerce_quantity(cart_item.get("qty", 1)) + qty
                                found = True
                                break

                        if not found:
                            cart_store[call_id]["items"].append({
                                "name": final_name,
                                "qty": qty,
                                "price": price,
                                "notes": notes if notes else None
                            })

                        cart_store[call_id]["items"] = normalize_cart_items(cart_store[call_id]["items"])
                        cart_items = cart_store[call_id]["items"].copy()

                    result = {
                        "status": "ok",
                        "message": f"{qty}x {final_name} toegevoegd",
                        "item": final_name,
                        "qty": qty,
                        "cart_count": len(cart_items)
                    }
                    results.append({"toolCallId": tool_id, "result": result})

                elif tool_name == "get_cart":
                    call_id = body.get("call", {}).get("id", "vapi-server")
                    cart = cart_store.get(call_id, {"items": []})
                    cart_items = normalize_cart_items(cart.get("items", []))
                    cart_summary = [{"name": i["name"], "qty": i["qty"]} for i in cart_items]
                    result = {
                        "items": cart_summary,
                        "count": len(cart_items),
                        "empty": len(cart_items) == 0
                    }
                    results.append({"toolCallId": tool_id, "result": result})
                    
                else:
                    # Unknown tool
                    results.append({"toolCallId": tool_id, "result": {"error": f"Onbekende tool: {tool_name}"}})
            
            return {"results": strip_voice_price_fields(results)}
        
        # Handle other event types
        elif message_type == "assistant-request":
            # VAPI vraagt om assistant config - niet nodig, we gebruiken dashboard config
            return {"assistant": None}
            
        elif message_type == "status-update":
            status = message.get("status", "")
            logger.info(f"[VAPI Server] Status update: {status}")
            return {"status": "ok"}
            
        elif message_type == "end-of-call-report":
            logger.info(f"[VAPI Server] Call ended")
            return {"status": "ok"}
        
        # Default: acknowledge
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"[VAPI Server] Error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/analytics")
def get_analytics():
    """Return call analytics voor monitoring"""
    summary = {
        "total_calls": len(call_analytics),
        "active_carts": len(cart_store),
        "calls": {}
    }

    for call_id, stats in call_analytics.items():
        summary["calls"][call_id] = {
            "total_searches": len(stats["searches"]),
            "total_cart_adds": len(stats["cart_adds"]),
            "total_errors": len(stats["errors"]),
            "recent_searches": stats["searches"][-5:] if stats["searches"] else [],
            "recent_cart_adds": stats["cart_adds"][-5:] if stats["cart_adds"] else []
        }

    return summary

@app.post("/tools/search_menu")
async def search_menu(request: Request):
    """
    Zoek items in het menu (POST method for Retell compatibility)

    Body:
    {
        "query": "zoekterm"
    }

    Returns:
    - items: Lijst van gevonden items met naam, prijs, categorie
    - total: Aantal resultaten
    - query: De zoekterm die gebruikt is
    """
    call_id = get_call_id(request)

    # Track analytics
    if call_id not in call_analytics:
        call_analytics[call_id] = {"searches": [], "cart_adds": [], "errors": []}

    # Parse body
    data = await request.json()

    # Retell sends query in nested "args" object
    if "args" in data and "query" in data["args"]:
        query = data["args"]["query"]
    else:
        query = data.get("query", "")

    # Track search
    call_analytics[call_id]["searches"].append(query)

    # Log only in development
    debug_log(f"📥 search_menu [{call_id}]: query='{query}'")

    if not query:
        return {
            "items": [],
            "total": 0,
            "query": "",
            "message": "Geen zoekterm opgegeven"
        }

    # Gebruik smart_search_item voor betere resultaten (incl. fuzzy matching)
    results = smart_search_item(query.lower())

    # Als geen resultaten
    if not results:
        return {
            "items": [],
            "total": 0,
            "query": query,
            "message": f"Geen resultaten gevonden voor '{query}'"
        }

    # Format resultaten
    formatted_results = []
    for item in results:
        formatted_results.append({
            "name": item["name"],
            "price": item["price"],
            "price_formatted": format_price(item["price"]),
            "price_spoken": format_price_spoken(item["price"]),
            "category": item["category"]
        })

    return {
        "items": formatted_results,
        "total": len(formatted_results),
        "query": query
    }

@app.post("/tools/add_to_cart")
async def add_to_cart(request: Request):
    """
    Voeg item toe aan cart (wordt bewaard tijdens gesprek)

    Body:
    {
        "item": "friet met mayonaise",
        "quantity": 1,
        "notes": "extra mayonaise" (optional)
    }
    """
    call_id = get_call_id(request)
    
    raw_body = await request.body()
    data = json.loads(raw_body) if raw_body else {}

    debug_log(f"📥 add_to_cart [{call_id}]: {data.get('item', 'unknown')}")

    item_name = data.get("item", "")
    qty = coerce_quantity(data.get("quantity", 1))
    notes = data.get("notes", "")

    item_data = get_item_with_price(item_name)
    if item_data:
        final_name = item_data["name"]
        price = item_data["price"]
    else:
        final_name = item_name
        price = 0

    # Initialize cart if not exists
    if call_id not in cart_store:
        cart_store[call_id] = {"items": [], "customer_name": "", "phone": "", "pickup_time": None}

    # Add item to cart
    cart_store[call_id]["items"].append({
        "name": final_name,
        "qty": qty,
        "price": price,
        "notes": notes
    })

    debug_log(f"🛒 Item added to cart [{call_id}]: {qty}x {final_name}")

    cart_store[call_id]["items"] = normalize_cart_items(cart_store[call_id]["items"])
    cart_items = cart_store[call_id]["items"]
    cart_total = compute_cart_total(cart_items)

    return {
        "status": "ok",
        "message": f"{qty}x {final_name} toegevoegd",
        "item": {
            "name": final_name,
            "qty": qty,
            "price": price,
            "price_formatted": format_price(price) if price else "onbekend",
            "price_spoken": format_price_spoken(price) if price else "prijs onbekend"
        },
        "cart_count": len(cart_items),
        "cart": {
            "items": cart_items,
            "count": len(cart_items),
            "total": cart_total,
            "total_formatted": format_price(cart_total),
            "total_spoken": format_price_spoken(cart_total)
        }
    }

@app.post("/create_web_call")
async def create_web_call(request: Request):
    """Create a Retell web call for testing"""
    from retell import Retell
    import os

    data = await request.json()
    agent_id = data.get("agent_id", "agent_5c757c39c9a255626773ce7ba3")

    api_key = os.getenv("RETELL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="RETELL_API_KEY not set")

    client = Retell(api_key=api_key)
    call = client.call.create_web_call(agent_id=agent_id)

    return {
        "access_token": call.access_token,
        "call_id": call.call_id
    }

@app.get("/tools/get_cart")
async def get_cart(request: Request):
    """Haal huidige cart op"""
    call_id = get_call_id(request)

    if call_id not in cart_store:
        return {"items": [], "total_items": 0}

    cart = cart_store[call_id]

    # Vul ontbrekende prijzen aan voor legacy cart-items + normaliseer qty/price
    normalized_items = []
    for item in cart["items"]:
        price = item.get("price")
        if price is None:
            found = get_item_with_price(item.get("name", ""))
            price = found["price"] if found else 0

        normalized_items.append({
            **item,
            "qty": coerce_quantity(item.get("qty", item.get("quantity", 1))),
            "price": coerce_price(price)
        })

    cart["items"] = normalized_items
    cart_total = compute_cart_total(normalized_items)
    return {
        "items": normalized_items,
        "total_items": len(normalized_items),
        "total": cart_total,
        "formatted_total": format_price(cart_total),
        "total_spoken": format_price_spoken(cart_total)
    }

@app.get("/tools/cart")
async def get_cart_alt(request: Request):
    """Haal huidige cart op (alternatieve endpoint voor tools.py)"""
    call_id = get_call_id(request)

    if call_id not in cart_store:
        cart_store[call_id] = {"items": [], "customer_name": "", "phone": "", "pickup_time": None}
        return {
            "items": [],
            "pickup_time": None,
            "total": 0.0,
            "item_count": 0
        }

    cart = cart_store[call_id]
    
    # Calculate total
    pricing = calculate_order_total(cart["items"])
    
    return {
        "items": cart["items"],
        "pickup_time": cart.get("pickup_time"),
        "total": pricing["total"],
        "item_count": len(cart["items"])
    }

@app.get("/tools/business_info")
async def get_business_info():
    """Retourneer bedrijfsinformatie"""
    return {
        "name": BUSINESS_INFO["name"],
        "address": BUSINESS_INFO["address"],
        "opening_hours": BUSINESS_INFO["opening_hours"]
    }

@app.get("/tools/hours")
async def get_hours():
    """Retourneer openingstijden en check of nu open"""
    status = is_open_now()
    
    return {
        "currently_open": status.get("open", False),
        "status_message": status.get("reason", "Open"),
        "closes_at": status.get("closes_at"),
        "next_open": status.get("next_open"),
        "opens_at": status.get("opens_at")
    }

@app.post("/tools/check_pickup_time")
async def check_pickup_time(request: Request):
    """Check of een afhaaltijd geldig is"""
    call_id = get_call_id(request)

    # Parse body - Retell sends pickup_time in nested "args" object
    data = await request.json()

    if "args" in data and "pickup_time" in data["args"]:
        pickup_time = data["args"]["pickup_time"]
    else:
        pickup_time = data.get("pickup_time", "")

    debug_log(f"📥 check_pickup_time [{call_id}]: {pickup_time}")

    if not pickup_time:
        raise HTTPException(status_code=400, detail="pickup_time parameter required")

    result = is_pickup_time_valid(pickup_time)

    return {
        "valid": result["valid"],
        "message": result["reason"]
    }

@app.get("/tools/menu")
async def get_menu(category: Optional[str] = None):
    """Retourneer menu, optioneel gefilterd op categorie"""
    menu_items = []
    for cat, items in MENU.items():
        for item_name, price in items.items():
            if price is not None:
                if category is None or cat == category:
                    menu_items.append({
                        "id": item_name.lower().replace(" ", "_"),
                        "name": item_name,
                        "price": price,
                        "price_formatted": format_price(price),
                        "price_spoken": format_price_spoken(price),
                        "category": cat
                    })
    
    return {
        "items": menu_items,
        "total": len(menu_items)
    }

@app.get("/tools/calculate_total")
async def calculate_total(request: Request):
    """Bereken totaalprijs van de winkelwagen"""
    call_id = get_call_id(request)
    
    if call_id not in cart_store:
        return {"total": 0.0, "item_count": 0}
    
    cart = cart_store[call_id]
    pricing = calculate_order_total(cart["items"])
    
    return {
        "total": pricing["total"],
        "formatted_total": pricing["formatted_total"],
        "spoken_total": pricing.get("spoken_total", format_price_spoken(pricing["total"])),
        "item_count": len(cart["items"])
    }

@app.post("/tools/update_cart")
async def update_cart(request: Request):
    """Update winkelwagen item"""
    call_id = get_call_id(request)
    data = await request.json()
    
    if call_id not in cart_store:
        raise HTTPException(status_code=404, detail="Geen winkelwagen gevonden")
    
    item_id = data.get("item_id")
    quantity = coerce_quantity(data.get("quantity", 1))
    
    # Find item by name (since we store by name, not id)
    item_name = item_id.replace("_", " ").title() if item_id else None
    
    for item in cart_store[call_id]["items"]:
        if item["name"].lower() == item_name.lower() if item_name else False:
            item["qty"] = max(1, quantity)
            return {
                "status": "ok",
                "message": f"{item['name']} aangepast naar {quantity}",
                "item": item
            }
    
    raise HTTPException(status_code=404, detail="Item niet gevonden in winkelwagen")

@app.post("/tools/remove_from_cart")
async def remove_from_cart(request: Request):
    """Verwijder item uit winkelwagen"""
    call_id = get_call_id(request)
    data = await request.json()
    
    if call_id not in cart_store:
        raise HTTPException(status_code=404, detail="Geen winkelwagen gevonden")
    
    item_id = data.get("item_id")
    item_name = item_id.replace("_", " ").title() if item_id else None
    
    if not item_name:
        raise HTTPException(status_code=400, detail="item_id parameter required")
    
    # Remove item by name
    original_count = len(cart_store[call_id]["items"])
    cart_store[call_id]["items"] = [
        item for item in cart_store[call_id]["items"]
        if item["name"].lower() != item_name.lower()
    ]
    
    removed = original_count - len(cart_store[call_id]["items"])
    
    if removed == 0:
        raise HTTPException(status_code=404, detail="Item niet gevonden in winkelwagen")
    
    return {
        "status": "ok",
        "message": f"{item_name} verwijderd",
        "cart_count": len(cart_store[call_id]["items"])
    }

@app.post("/tools/handoff")
async def handoff(request: Request):
    """Handoff naar medewerker"""
    data = await request.json()
    call_id = get_call_id(request)

    reason = data.get("reason", "Klant vraagt om medewerker")
    summary = data.get("summary", "")

    debug_log(f"🔄 HANDOFF REQUEST [{call_id}]: {reason}")

    return {
        "status": "ok",
        "message": "Doorverbinden naar medewerker...",
        "reason": reason,
        "summary": summary
    }


# ============================================================================
# VAPI ENDPOINTS
# ============================================================================
# VAPI gebruikt een ander payload format dan Retell
# Deze endpoints handelen VAPI-specifieke requests af

def extract_vapi_tool_calls(body: Dict[str, Any]) -> list:
    """
    Extract tool calls uit VAPI payload

    VAPI stuurt toolCallList met 'parameters' (niet 'arguments'):
    {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {"id": "...", "name": "search_menu", "parameters": {"query": "patat"}}
            ]
        },
        "call": {"id": "..."}
    }
    """
    raw_calls = []
    message = body.get("message", {})

    if isinstance(message, dict):
        if isinstance(message.get("toolCallList"), list):
            raw_calls.extend(message.get("toolCallList", []))
        if isinstance(message.get("toolCalls"), list):
            raw_calls.extend(message.get("toolCalls", []))
        if isinstance(message.get("toolCall"), dict):
            raw_calls.append(message.get("toolCall"))

    if isinstance(body.get("toolCallList"), list):
        raw_calls.extend(body.get("toolCallList", []))
    if isinstance(body.get("toolCalls"), list):
        raw_calls.extend(body.get("toolCalls", []))
    if isinstance(body.get("toolCall"), dict):
        raw_calls.append(body.get("toolCall"))

    function_call = body.get("functionCall") or (message.get("functionCall") if isinstance(message, dict) else None)
    if isinstance(function_call, dict):
        raw_calls.append({
            "id": function_call.get("id", "function-call"),
            "name": function_call.get("name"),
            "arguments": function_call.get("arguments", {})
        })

    normalized = []
    for tc in raw_calls:
        if not isinstance(tc, dict):
            continue
        tc_copy = dict(tc)
        if "parameters" in tc_copy and "arguments" not in tc_copy:
            tc_copy["arguments"] = tc_copy["parameters"]
        if "function" in tc_copy and isinstance(tc_copy["function"], dict):
            func = tc_copy["function"]
            if "arguments" in func:
                args = func["arguments"]
                if isinstance(args, str):
                    try:
                        tc_copy["arguments"] = json.loads(args)
                    except Exception:
                        tc_copy["arguments"] = {}
                else:
                    tc_copy["arguments"] = args
            if "name" in func and "name" not in tc_copy:
                tc_copy["name"] = func["name"]
        if isinstance(tc_copy.get("arguments"), str):
            try:
                tc_copy["arguments"] = json.loads(tc_copy["arguments"])
            except Exception:
                tc_copy["arguments"] = {}
        normalized.append(tc_copy)

    return normalized


def format_vapi_response(tool_call_id: str, result: Any) -> Dict:
    """Format response in VAPI format"""
    safe_result = strip_voice_price_fields(result)
    return {
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": safe_result
            }
        ]
    }


@app.post("/vapi/tools/get_menu")
async def vapi_get_menu(request: Request):
    """VAPI endpoint: Haal volledig menu op"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    logger.info(f"[VAPI] get_menu [{call_id}]")

    tool_calls = extract_vapi_tool_calls(body)
    tool_call_id = tool_calls[0].get("id", "unknown") if tool_calls else "unknown"

    # Build menu response
    menu_items = []
    for cat, items in MENU.items():
        for item_name, price in items.items():
            if price is not None:
                menu_items.append({
                    "name": item_name,
                    "price": price,
                    "price_formatted": format_price(price),
                    "price_spoken": format_price_spoken(price),
                    "category": cat
                })

    result = {
        "items": menu_items,
        "total": len(menu_items),
        "categories": list(MENU.keys())
    }

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/search_menu")
async def vapi_search_menu(request: Request):
    """VAPI endpoint: Zoek items in menu - verwerkt ALLE tool calls"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    # Verwerk ALLE tool calls, niet alleen de eerste
    results = []
    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id", "unknown")
        arguments = tool_call.get("arguments", {})
        query = arguments.get("query", "")

        logger.info(f"[VAPI] search_menu [{call_id}]: query='{query}' (id={tool_call_id})")

        if not query:
            result = {"items": [], "total": 0, "query": "", "message": "Geen zoekterm"}
        else:
            search_results = smart_search_item(query.lower())
            formatted = []
            for item in search_results:
                formatted.append({
                    "name": item["name"],
                    "price": item["price"],
                    "price_formatted": format_price(item["price"]),
                    "price_spoken": format_price_spoken(item["price"]),
                    "category": item["category"]
                })
            result = {"items": formatted, "total": len(formatted), "query": query}

        results.append({"toolCallId": tool_call_id, "result": result})

    return {"results": strip_voice_price_fields(results)}


@app.post("/vapi/tools/add_to_cart")
async def vapi_add_to_cart(request: Request):
    """VAPI endpoint: Voeg item toe aan cart - GEOPTIMALISEERD met single lookup"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    # Cleanup oude carts periodiek
    _cleanup_old_carts()

    # Initialize cart if not exists (met timestamp)
    with cart_store_lock:
        if call_id not in cart_store:
            cart_store[call_id] = {
                "items": [],
                "customer_name": "",
                "phone": "",
                "pickup_time": None,
                "created_at": now_nl()
            }

    # Verwerk ALLE tool calls
    results = []
    for tool_call in tool_calls:
        tool_call_id = tool_call.get("id", "unknown")
        arguments = tool_call.get("arguments", {})

        item_name = arguments.get("item", "")
        qty = coerce_quantity(arguments.get("quantity", 1))
        notes = arguments.get("notes", "")

        logger.info(f"[VAPI] add_to_cart [{call_id}]: {qty}x {item_name}")

        # SINGLE LOOKUP
        item_data = get_item_with_price(item_name)

        if not item_data:
            # Item niet gevonden — meld dit expliciet aan de assistent
            result = {
                "status": "not_found",
                "message": f"'{item_name}' staat niet op het menu. Vraag de klant om het anders te omschrijven of gebruik search_menu."
            }
            results.append({"toolCallId": tool_call_id, "result": result})
            continue

        final_name = item_data["name"]
        price = item_data["price"]

        # Add item met prijs (thread-safe) - merge duplicaten
        with cart_store_lock:
            found = False
            for cart_item in cart_store[call_id]["items"]:
                if cart_item["name"].lower() == final_name.lower():
                    cart_item["qty"] = coerce_quantity(cart_item.get("qty", 1)) + qty
                    found = True
                    break

            if not found:
                cart_store[call_id]["items"].append({
                    "name": final_name,
                    "qty": qty,
                    "price": price,
                    "notes": notes if notes else None
                })

            cart_store[call_id]["items"] = normalize_cart_items(cart_store[call_id]["items"])
            cart_items = cart_store[call_id]["items"].copy()
            cart_total = compute_cart_total(cart_items)

        result = {
            "status": "ok",
            "message": f"{qty}x {final_name} toegevoegd",
            "item": final_name,
            "qty": qty,
            "cart_count": len(cart_items)
        }
        results.append({"toolCallId": tool_call_id, "result": result})

    return {"results": results}


@app.post("/vapi/tools/get_cart")
async def vapi_get_cart(request: Request):
    """VAPI endpoint: Haal cart op"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)
    tool_call_id = tool_calls[0].get("id", "unknown") if tool_calls else "unknown"

    if call_id not in cart_store:
        cart_store[call_id] = {"items": [], "customer_name": "", "phone": "", "pickup_time": None}

    cart = cart_store[call_id]

    # Vul ontbrekende prijzen aan uit menu + normaliseer
    enriched_items = []
    for item in cart.get("items", []):
        price = item.get("price")
        if not price:
            found = get_item_with_price(item.get("name", ""))
            price = found["price"] if found else 0
        enriched_items.append({
            **item,
            "qty": coerce_quantity(item.get("qty", item.get("quantity", 1))),
            "price": coerce_price(price)
        })

    cart["items"] = enriched_items

    # Bouw response met alleen item-naam en aantal (geen prijzen voor voice)
    cart_items_summary = [
        {"name": i["name"], "qty": i["qty"]}
        for i in enriched_items
    ]

    result = {
        "items": cart_items_summary,
        "count": len(enriched_items),
        "empty": len(enriched_items) == 0
    }

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/update_cart")
async def vapi_update_cart(request: Request):
    """VAPI endpoint: Update cart item"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "unknown")
    arguments = tool_call.get("arguments", {})

    # Support beide: "item" (nieuw) en "item_name" (legacy)
    item_name = arguments.get("item") or arguments.get("item_name", "")
    quantity = coerce_quantity(arguments.get("quantity", 1))

    if not item_name:
        return format_vapi_response(tool_call_id, {"status": "error", "message": "Geen item opgegeven"})

    if call_id not in cart_store:
        result = {"status": "error", "message": "Geen bestelling gevonden"}
    else:
        found = False
        # Fuzzy match - ook partial matches accepteren
        item_name_lower = item_name.lower()
        for item in cart_store[call_id]["items"]:
            if item["name"].lower() == item_name_lower or item_name_lower in item["name"].lower():
                item["qty"] = max(1, quantity)
                found = True
                break

        if found:
            result = {"status": "ok", "message": f"{item_name} aangepast naar {quantity}"}
        else:
            result = {"status": "error", "message": f"{item_name} niet gevonden in bestelling"}

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/remove_from_cart")
async def vapi_remove_from_cart(request: Request):
    """VAPI endpoint: Verwijder item uit cart"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "unknown")
    arguments = tool_call.get("arguments", {})

    # Support beide: "item" (nieuw) en "item_name" (legacy)
    item_name = arguments.get("item") or arguments.get("item_name", "")

    if not item_name:
        return format_vapi_response(tool_call_id, {"status": "error", "message": "Geen item opgegeven"})

    if call_id not in cart_store:
        result = {"status": "error", "message": "Geen bestelling gevonden"}
    else:
        original = len(cart_store[call_id]["items"])
        # Fuzzy match - ook partial matches accepteren
        item_name_lower = item_name.lower()
        cart_store[call_id]["items"] = [
            i for i in cart_store[call_id]["items"]
            if not (i["name"].lower() == item_name_lower or item_name_lower in i["name"].lower())
        ]
        removed = original - len(cart_store[call_id]["items"])

        if removed > 0:
            result = {"status": "ok", "message": f"{item_name} verwijderd"}
        else:
            result = {"status": "error", "message": f"{item_name} niet gevonden"}

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/check_pickup_time")
async def vapi_check_pickup_time(request: Request):
    """VAPI endpoint: Check afhaaltijd"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "unknown")
    arguments = tool_call.get("arguments", {})

    pickup_time = arguments.get("pickup_time", "")

    logger.info(f"[VAPI] check_pickup_time [{call_id}]: {pickup_time}")

    if not pickup_time:
        result = {"valid": False, "message": "Geen afhaaltijd opgegeven"}
    else:
        check = is_pickup_time_valid(pickup_time)
        result = {"valid": check["valid"], "message": check["reason"]}

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/hours")
async def vapi_get_hours(request: Request):
    """VAPI endpoint: Haal openingstijden op"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    tool_calls = extract_vapi_tool_calls(body)
    tool_call_id = tool_calls[0].get("id", "unknown") if tool_calls else "unknown"

    status = is_open_now()

    result = {
        "currently_open": status.get("open", False),
        "status_message": status.get("reason", "Open"),
        "closes_at": status.get("closes_at"),
        "opens_at": status.get("opens_at"),
        "next_open": status.get("next_open")
    }

    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/tools/handoff")
async def vapi_handoff(request: Request):
    """VAPI endpoint: Doorverbinden naar medewerker"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    if not tool_calls:
        return {"results": []}

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "unknown")
    arguments = tool_call.get("arguments", {})

    reason = sanitize_string(arguments.get("reason", "Klant wil medewerker spreken"), max_length=200)
    logger.info(f"[VAPI] handoff [{call_id}]: {reason}")

    result = {
        "status": "ok",
        "message": "Doorverbinden naar medewerker",
        "reason": reason
    }
    return format_vapi_response(tool_call_id, result)


@app.post("/vapi/order")
async def vapi_receive_order(request: Request):
    """VAPI endpoint: Ontvang en verwerk bestelling"""
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    call_id = get_call_id(request, "vapi", body)
    tool_calls = extract_vapi_tool_calls(body)

    logger.info(f"[VAPI] order [{call_id}]")
    logger.info(f"[VAPI] Raw body: {json.dumps(body, indent=2, ensure_ascii=False)}")

    if not tool_calls:
        return {"results": []}

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "unknown")
    arguments = tool_call.get("arguments", {})

    # Extract order data
    customer_name = sanitize_string(arguments.get("customer_name", ""), 100)
    phone = sanitize_string(arguments.get("phone", ""), 20)
    pickup_time = sanitize_string(arguments.get("pickup_time", ""), 10)
    items = arguments.get("items", [])
    extra_notes = sanitize_string(arguments.get("extra_notes", ""), 500)

    # Fallback: haal items uit cart als niet meegegeven
    if not items and call_id in cart_store:
        items = cart_store[call_id]["items"]
        logger.info(f"[VAPI] Using cart items: {len(items)} items")

    # Validate
    if not items:
        result = {"status": "error", "message": "Geen items in bestelling"}
        return format_vapi_response(tool_call_id, result)

    if not pickup_time:
        result = {"status": "error", "message": "Geen afhaaltijd opgegeven"}
        return format_vapi_response(tool_call_id, result)

    # Normalize items
    normalized_items = []
    for item in items:
        if isinstance(item, dict):
            normalized_items.append({
                "name": sanitize_string(str(item.get("name", "")), 100),
                "qty": coerce_quantity(item.get("qty", item.get("quantity", 1))),
                "notes": sanitize_string(item.get("notes") or "", 200) if item.get("notes") else None
            })

    # Generate order ID
    order_id = f"DRP{now_nl().strftime('%Y%m%d%H%M%S')}"

    # Calculate prices
    pricing = calculate_order_total(normalized_items)

    # Create email
    lines = [
        "Nieuwe BESTELLING (VAPI) - De Dorpspomp & Dieks IJssalon",
        f"Bestelnummer: {order_id}",
        f"Tijd: {now_nl().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Naam: {customer_name or '-'}",
        f"Telefoon: {phone or '-'}",
        f"Afhaaltijd: {pickup_time}",
        "",
        "Items:"
    ]

    for item in pricing["items"]:
        if item["price_per_item"] is not None:
            price_info = f" a {format_price(item['price_per_item'])} = {format_price(item['subtotal'])}"
        else:
            price_info = " (prijs onbekend)"
        lines.append(f"- {item['qty']}x {item['name']}{price_info}")

    lines.append("")
    lines.append(f"TOTAAL: {pricing['formatted_total']}")

    if extra_notes:
        lines.append("")
        lines.append(f"Opmerking: {extra_notes}")

    email_body = "\n".join(lines)

    # 🚀 ASYNC email - blokkeert niet!
    send_email_background("NIEUWE BESTELLING (VAPI) - De Dorpspomp", email_body, order_id)

    result = {
        "status": "ok",
        "message": "Bestelling ontvangen en email verzonden",
        "order_id": order_id,
        "total": pricing["formatted_total"],
        "total_spoken": pricing.get("spoken_total", format_price_spoken(pricing["total"]))
    }

    return format_vapi_response(tool_call_id, result)


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting order webhook server on http://localhost:8000")
    print("POST /order - Receive order and send email")
    print("GET  /health - Health check")
    print("=" * 60)
    print("\nPress CTRL+C to stop the server\n")
    # Use import string for reload to work properly
    uvicorn.run("webhook_order:app", host="0.0.0.0", port=8000, reload=True)
