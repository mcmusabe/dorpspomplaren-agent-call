"""
Openingstijden checker voor De Dorpspomp & Dieks IJssalon

Gebruikt Europe/Amsterdam timezone zodat openingstijden correct zijn,
ook als de server in UTC draait (bijv. Railway).
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

# Nederlandse tijdzone - ALTIJD gebruiken ipv datetime.now()
NL_TZ = ZoneInfo("Europe/Amsterdam")

OPENING_HOURS = {
    "monday": {"open": None, "close": None, "closed": True},
    "tuesday": {"open": None, "close": None, "closed": True},
    "wednesday": {"open": time(11, 30), "close": time(19, 30), "closed": False},
    "thursday": {"open": time(11, 30), "close": time(19, 30), "closed": False},
    "friday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
    "saturday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
    "sunday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
}


def now_nl() -> datetime:
    """Huidige tijd in Nederlandse tijdzone"""
    return datetime.now(NL_TZ)


def get_day_name(dt: datetime = None) -> str:
    """Haal de dag naam op (in English voor dict lookup)"""
    if dt is None:
        dt = now_nl()
    return dt.strftime("%A").lower()


def is_open_now() -> dict:
    """Check of de zaak nu open is"""
    now = now_nl()
    day = get_day_name(now)
    hours = OPENING_HOURS.get(day)

    if hours["closed"]:
        next_open = get_next_opening()
        return {
            "open": False,
            "reason": f"Vandaag zijn we gesloten. We zijn weer open op {next_open['day_nl']} om {next_open['time']}",
            "next_open": next_open
        }

    current_time = now.time()
    if current_time < hours["open"]:
        return {
            "open": False,
            "reason": f"Vandaag zijn we open vanaf {hours['open'].strftime('%H:%M')}",
            "opens_at": hours["open"].strftime("%H:%M")
        }

    if current_time > hours["close"]:
        next_open = get_next_opening()
        return {
            "open": False,
            "reason": f"Vandaag zijn we gesloten. We zijn weer open op {next_open['day_nl']} om {next_open['time']}",
            "next_open": next_open
        }

    return {
        "open": True,
        "reason": f"Vandaag zijn we open tot {hours['close'].strftime('%H:%M')}",
        "closes_at": hours["close"].strftime("%H:%M")
    }


def get_next_opening() -> dict:
    """Vind de volgende keer dat de zaak open gaat"""
    now = now_nl()
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i in range(1, 8):
        future_day_idx = (now.weekday() + i) % 7
        day_name = day_names[future_day_idx]

        hours = OPENING_HOURS.get(day_name)
        if not hours["closed"]:
            return {
                "day": day_name,
                "day_nl": translate_day(day_name),
                "time": hours["open"].strftime("%H:%M")
            }

    return {"day": "unknown", "day_nl": "onbekend", "time": "onbekend"}


def translate_day(day: str) -> str:
    """Vertaal Engelse dag naar Nederlands"""
    translations = {
        "monday": "maandag",
        "tuesday": "dinsdag",
        "wednesday": "woensdag",
        "thursday": "donderdag",
        "friday": "vrijdag",
        "saturday": "zaterdag",
        "sunday": "zondag"
    }
    return translations.get(day, day)


def is_pickup_time_valid(pickup_time: str, pickup_date: datetime = None) -> dict:
    """
    Check of een afhaaltijd geldig is

    Args:
        pickup_time: string in format "HH:MM" (e.g., "18:30")
        pickup_date: datetime object (default: vandaag NL tijd)

    Returns:
        dict met 'valid' (bool) en 'reason' (str)
    """
    if pickup_date is None:
        pickup_date = now_nl()

    day = get_day_name(pickup_date)
    hours = OPENING_HOURS.get(day)

    if hours["closed"]:
        next_open = get_next_opening()
        return {
            "valid": False,
            "reason": f"Vandaag zijn we gesloten. We zijn weer open op {next_open['day_nl']} om {next_open['time']}"
        }

    # Parse pickup time
    try:
        pickup_hour, pickup_min = map(int, pickup_time.split(":"))
        pickup_t = time(pickup_hour, pickup_min)
    except (ValueError, AttributeError):
        return {
            "valid": False,
            "reason": "Ongeldige tijd. Gebruik HH:MM, bijvoorbeeld 18:30"
        }

    # Check te vroeg
    if pickup_t < hours["open"]:
        return {
            "valid": False,
            "reason": f"We openen pas om {hours['open'].strftime('%H:%M')}. Kunt u het later ophalen?"
        }

    # Check te laat (15 min buffer voor sluiting)
    close_buffer = time(hours["close"].hour, max(0, hours["close"].minute - 15))
    if pickup_t > close_buffer:
        return {
            "valid": False,
            "reason": f"We sluiten om {hours['close'].strftime('%H:%M')}. Kunt u het eerder ophalen?"
        }

    # Check of tijd niet in het verleden ligt
    now = now_nl()
    current_time = now.time()
    if pickup_t < current_time:
        return {
            "valid": False,
            "reason": f"Het is al {current_time.strftime('%H:%M')}. Kunt u een later tijdstip kiezen?"
        }

    return {
        "valid": True,
        "reason": "Tijd is geldig"
    }
