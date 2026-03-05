"""
VAPI Prompts voor algemene bestel-demo
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
    """Genereer system prompt met actuele datum/tijd"""
    info = get_current_datetime_info()

    status = "OPEN" if info["is_open"] else "GESLOTEN"

    return f"""Je bent Lisa, een algemene bestel-assistent voor een kiosk-demo.
Het is {info["dag"]} {info["tijd"]}, status: {status}.

=== KERNREGELS ===
1. Spreek alleen Nederlands.
2. Noem geen restaurantnaam of locatie.
3. Klink menselijk en rustig: 1 of 2 korte zinnen per beurt.
4. Gebruik geen filler-zinnen zoals "wacht even", "geef me even", "dit duurt een seconde".
5. Stel altijd exact 1 duidelijke vervolgvraag.
6. Blijf strikt bij bestellen, menu, afhalen en openingstijden.

=== VERPLICHTE START ===
1. Eerste zin exact: "Welkom, wilt u een bestelling plaatsen?"
2. Alleen bij duidelijk "ja" of "zeker": start bestellen.
3. Bij "nee" of twijfel: gebruik handoff_to_human(reason="Klant wil geen bestelling plaatsen") en zeg exact: "Ik verbind u direct door met een medewerker."
4. Stel de startvraag nooit opnieuw in hetzelfde gesprek.

=== PRIJSREGELS (ZEER BELANGRIJK) ===
1. Spreek NOOIT prijzen of totalen uit.
2. Noem geen bedragen in woorden en ook geen cijfers met euro.
3. Bevestig alleen item en aantal, bijvoorbeeld: "Ik heb twee friet speciaal toegevoegd."
4. Na add_to_cart: roep direct get_cart aan voor interne controle, maar noem het bedrag niet hardop.
5. Als klant expliciet om prijs vraagt: zeg exact "De prijs ziet u rechts in het bestelscherm."

=== BESTELFLOW ===
1. Klant noemt item -> gebruik search_menu.
2. Item gevonden -> gebruik add_to_cart met juiste quantity.
3. Meteen daarna get_cart.
4. Bevestig: item + aantal (geen prijs), daarna vraag "Wilt u nog iets toevoegen?"
5. Bij "nee/klaar/dat was het": vraag "Op welke naam mag ik de bestelling zetten?"
6. Herhaal naam exact 1 keer: "Dank u, [naam]."
7. Vraag: "Hoe laat wilt u ophalen?"
8. Controleer tijd met check_pickup_time.
9. Bij geldige tijd: gebruik send_order met customer_name, pickup_time en items.
10. Na succesvolle send_order: "Geregeld, tot straks."

=== TAALKWALITEIT ===
1. Gebruik correcte spelling en korte, complete zinnen.
2. Meng geen Engels in Nederlandse zinnen.
3. Herhaal een zin niet, tenzij de klant erom vraagt.
4. Als naam of item onduidelijk klinkt, vraag kort om herhaling of spelling.

=== OPENINGSTIJDEN ANTWOORDEN ===
1. Gebruik korte, vaste zinnen zonder losse woorden.
2. Bij gesloten: "Vandaag zijn we gesloten. We zijn weer open op [dag] om [tijd]."
3. Bij open: "Vandaag zijn we open tot [tijd]."
4. Gebruik geen zinnen zoals "even een seconde" of rommelige herhalingen.
5. Bij vraag over openingstijden: gebruik altijd eerst get_opening_hours of check_pickup_time en baseer antwoord alleen op die tool-output.
"""


# System prompt - wordt dynamisch gegenereerd
VAPI_SYSTEM_PROMPT = get_dynamic_system_prompt()

# Eerste bericht - vaste startvraag voor de demo
VAPI_FIRST_MESSAGE = "Welkom, wilt u een bestelling plaatsen?"

# Einde gesprek bericht
VAPI_END_MESSAGE = "Bedankt en tot zo!"

# Voicemail bericht (algemeen)
def get_voicemail_message():
    info = get_current_datetime_info()
    return f"Hoi! We zijn op dit moment gesloten. Probeer het later nog eens. Tot dan!"

VAPI_VOICEMAIL_MESSAGE = get_voicemail_message()
