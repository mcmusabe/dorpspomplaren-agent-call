"""
Openingstijden checker voor De Dorpspomp & Dieks IJssalon
"""

from datetime import datetime, time

OPENING_HOURS = {
    "monday": {"open": None, "close": None, "closed": True},
    "tuesday": {"open": None, "close": None, "closed": True},
    "wednesday": {"open": time(11, 30), "close": time(19, 30), "closed": False},
    "thursday": {"open": time(11, 30), "close": time(19, 30), "closed": False},
    "friday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
    "saturday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
    "sunday": {"open": time(11, 30), "close": time(20, 0), "closed": False},
}


def get_day_name(dt: datetime = None) -> str:
    """Haal de dag naam op (in English voor dict lookup)"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%A").lower()


def is_open_now() -> dict:
    """Check of de zaak nu open is"""
    now = datetime.now()
    day = get_day_name(now)
    hours = OPENING_HOURS.get(day)

    if hours["closed"]:
        # Find next open day
        next_open = get_next_opening()
        return {
            "open": False,
            "reason": f"Vandaag ({day}) zijn we gesloten",
            "next_open": next_open
        }

    current_time = now.time()
    if current_time < hours["open"]:
        return {
            "open": False,
            "reason": f"We zijn nog niet open. We openen om {hours['open'].strftime('%H:%M')}",
            "opens_at": hours["open"].strftime("%H:%M")
        }

    if current_time > hours["close"]:
        next_open = get_next_opening()
        return {
            "open": False,
            "reason": f"We zijn al gesloten. We sloten om {hours['close'].strftime('%H:%M')}",
            "next_open": next_open
        }

    return {
        "open": True,
        "closes_at": hours["close"].strftime("%H:%M")
    }


def get_next_opening() -> dict:
    """Vind de volgende keer dat de zaak open gaat"""
    now = datetime.now()
    for i in range(1, 8):  # Check next 7 days
        future_day = (now.day + i) % 7
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
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
        pickup_date: datetime object (default: today)

    Returns:
        dict met 'valid' (bool) en 'reason' (str)
    """
    if pickup_date is None:
        pickup_date = datetime.now()

    day = get_day_name(pickup_date)
    hours = OPENING_HOURS.get(day)

    # Check if closed that day
    if hours["closed"]:
        next_open = get_next_opening()
        return {
            "valid": False,
            "reason": f"We zijn op {translate_day(day)} gesloten. We zijn weer open op {next_open['day_nl']} om {next_open['time']}"
        }

    # Parse pickup time
    try:
        pickup_hour, pickup_min = map(int, pickup_time.split(":"))
        pickup_t = time(pickup_hour, pickup_min)
    except:
        return {
            "valid": False,
            "reason": "Ongeldige tijd format. Gebruik HH:MM (bijv. 18:30)"
        }

    # Check if before opening
    if pickup_t < hours["open"]:
        return {
            "valid": False,
            "reason": f"We openen pas om {hours['open'].strftime('%H:%M')}. Kun je het later ophalen?"
        }

    # Check if after closing (give 15 min buffer before close)
    close_buffer = time(hours["close"].hour, max(0, hours["close"].minute - 15))
    if pickup_t > close_buffer:
        return {
            "valid": False,
            "reason": f"We sluiten om {hours['close'].strftime('%H:%M')}. Kun je het eerder ophalen?"
        }

    # Valid!
    return {
        "valid": True,
        "reason": "Tijd is geldig"
    }
