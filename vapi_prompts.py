"""
VAPI Prompts voor De Dorpspomp & Dieks IJssalon
Aangepast voor VAPI (geen state machine zoals Retell)
"""

from datetime import datetime
import locale

# Probeer Nederlandse locale te zetten voor datum formatting
try:
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'nl_NL')
    except:
        pass  # Gebruik default als Nederlands niet beschikbaar is


def get_current_datetime_info():
    """Haal huidige datum, tijd en dag informatie op"""
    now = datetime.now()

    # Nederlandse dagnamen
    dagen_nl = {
        0: "maandag", 1: "dinsdag", 2: "woensdag",
        3: "donderdag", 4: "vrijdag", 5: "zaterdag", 6: "zondag"
    }

    # Nederlandse maandnamen
    maanden_nl = {
        1: "januari", 2: "februari", 3: "maart", 4: "april",
        5: "mei", 6: "juni", 7: "juli", 8: "augustus",
        9: "september", 10: "oktober", 11: "november", 12: "december"
    }

    dag_naam = dagen_nl[now.weekday()]
    maand_naam = maanden_nl[now.month]

    return {
        "dag": dag_naam,
        "datum": now.day,
        "maand": maand_naam,
        "jaar": now.year,
        "tijd": now.strftime("%H:%M"),
        "uur": now.hour,
        "minuut": now.minute,
        "is_open": is_zaak_open(now)
    }


def is_zaak_open(now=None):
    """Check of de zaak nu open is"""
    if now is None:
        now = datetime.now()

    dag = now.weekday()  # 0=maandag, 6=zondag
    uur = now.hour
    minuut = now.minute
    tijd_decimaal = uur + minuut / 60

    # Maandag en dinsdag gesloten
    if dag in [0, 1]:
        return False

    # Woensdag en donderdag: 11:30 - 19:30
    if dag in [2, 3]:
        return 11.5 <= tijd_decimaal < 19.5

    # Vrijdag, zaterdag, zondag: 11:30 - 20:00
    if dag in [4, 5, 6]:
        return 11.5 <= tijd_decimaal < 20.0

    return False


def get_dynamic_system_prompt():
    """Genereer system prompt met actuele datum/tijd - VERBETERD"""
    info = get_current_datetime_info()

    status = "OPEN" if info["is_open"] else "GESLOTEN"

    return f"""Je bent Lisa, medewerker van snackbar De Dorpspomp in Laren.
Het is {info["dag"]} {info["tijd"]}, we zijn {status}.

=== BELANGRIJKE REGELS ===
1. Spreek ALLEEN Nederlands
2. Antwoord KORT (max 15 woorden)
3. Wees vriendelijk en informeel

=== BESTELLING FLOW ===
1. Klant noemt item → gebruik search_menu tool
2. Item gevonden → gebruik add_to_cart tool → zeg "Top! Nog iets?"
3. Klant zegt "nee/klaar/dat was het" → vraag "Op welke naam?"
4. Na naam → vraag "Hoe laat wil je ophalen?"
5. Na tijd → gebruik send_order tool → zeg "Geregeld! Tot straks!"

=== TOOLS ===
- search_menu: zoek in menu (bijv. "friet", "cola", "kroket")
- add_to_cart: voeg item toe met aantal
- get_cart: bekijk bestelling
- send_order: verstuur bestelling (ALLEEN na naam + tijd!)
- check_pickup_time: check of afhaaltijd geldig is

=== VOORBEELDEN ===
Klant: "Twee friet speciaal"
→ search_menu("friet speciaal") → add_to_cart("friet speciaal", 2)
→ Zeg: "Twee friet speciaal! Nog iets anders?"

Klant: "Nee dat was het"
→ Zeg: "Prima! Op welke naam mag ik het zetten?"

Klant: "Jan"
→ Zeg: "Top Jan! Hoe laat kom je het ophalen?"

Klant: "Half zes"
→ send_order(naam="Jan", tijd="17:30", items=[...])
→ Zeg: "Helemaal goed! Tot half zes, Jan!"

=== NIET DOEN ===
- Geen Engels spreken
- Geen lange zinnen
- Niet "bedankt" of "tot zo" zeggen voordat bestelling verstuurd is"""


# System prompt - wordt dynamisch gegenereerd
VAPI_SYSTEM_PROMPT = get_dynamic_system_prompt()

# Eerste bericht - Direct en vriendelijk
VAPI_FIRST_MESSAGE = "Hoi! Welkom bij De Dorpspomp. Wat mag het zijn?"

# Einde gesprek bericht
VAPI_END_MESSAGE = "Bedankt en tot zo!"

# Voicemail bericht (algemeen)
def get_voicemail_message():
    info = get_current_datetime_info()
    return f"Hoi! We zijn op dit moment gesloten. Probeer het later nog eens. Tot dan!"

VAPI_VOICEMAIL_MESSAGE = get_voicemail_message()
