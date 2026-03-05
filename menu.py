"""
Menu database voor De Dorpspomp & Dieks IJssalon
Prijzen in euro's

GEOPTIMALISEERD:
- Pre-built index voor O(1) lookups
- Cached search results
- Single lookup functie voor prijs + match
"""

from functools import lru_cache
from typing import Optional, Dict, List, Tuple
import time
import re

MENU = {
    "friet": {
        "kinder frites": 2.30,
        "friet zonder": 2.80,
        "friet met mayonaise": 3.55,
        "friet groot": 3.75,
        "friet groot mayonaise": 4.50,
        "friet speciaal": 3.75,
        "friet speciaal groot": 4.70,
        "friet sate": 3.75,
        "friet sate groot": 4.70,
        "friet oorlog": 3.75,
        "friet oorlog groot": 4.70,
        "friet stoofvlees": 7.50,
        "friet stoofvlees groot": 9.00,
        "boerenfriet": 7.50,
        "friet piri piri": 8.50
    },
    "snack": {
        "kroket rundvlees": 2.85,
        "kroket kalfsvlees": 2.85,
        "kroket loarnse": 2.85,
        "kroket groente": 2.85,
        "kroket vegan": 2.85,
        "kroket glutenvrij": 2.85,
        "frikandel": 2.30,
        "frikandel speciaal": 3.00,
        "frikandel glutenvrij": 2.30,
        "kaassoufle": 2.70,
        "kaassoufle glutenvrij": 2.70,
        "bamischijf": 2.75,
        "vega bamischijf": 2.75
    },
    "ijs": {
        "ijs 1 bol": 2.50,
        "ijs 2 bollen": 4.00,
        "ijs 3 bollen": 5.50,
        "softijs klein": 2.50,
        "softijs groot": 4.00,
        "ijscoupe": 6.50
    },
    "gehaktbal": {
        "gehaktbal": 4.30,
        "nasischijf": 2.75,
        "kipcorn": 2.75,
        "picanto": 2.75,
        "mexicano": 3.50,
        "shoarmarol": 4.30,
        "berehap": 4.00,
        "spek berehap": 4.50,
        "superberehap": 5.00,
        "loarnse spies": 5.00,
        "loempia kip": 4.75,
        "vietnamese 3 stuks": 5.00,
        "kipsatestokjes": 8.50,
        "kipnuggets 5 stuks": 3.50,
        "schnitzel": 7.75,
        "boeren": 8.50,
        "zigeuner": 8.50
    },
    "broodjes": {
        "kroket": 3.50,
        "kalfskroket": 3.50,
        "goulash kroket": 3.50,
        "groente kroket": 3.50,
        "frikandel": 3.15,
        "bal": 5.00
    },
    "hamburgers": {
        "de dorpspomp": 4.95,
        "de dorpspomp kaas": 5.50,
        "de dorpspomp hawaii": 5.75,
        "achterhoek": 9.50,
        "kip": 9.50
    },
    "broodje": {
        "carpaccio": 7.95,
        "gezond": 7.95,
        "warme kip": 7.95
    },
    "menu": {
        "boerenschnitzel": 17.25,
        "zigeunerschnitzel": 17.25,
        "sate": 18.75,
        "gehaktbal": 15.95,
        "stoofpotje": 16.95,
        "achterhoekburger": 19.75
    },
    "frisdranken": {
        "capri sun": 1.75,
        "blikje coca cola": 3.00,
        "blikje coca cola zero": 3.00,
        "blikje fanta": 3.00,
        "blikje cassis": 3.00,
        "blikje sprite": 3.00,
        "blikje fuze tea": 3.00,
        "blikje rivella": 3.00,
        "blikje tonic": 3.00,
        "blikje bitter lemon": 3.00,
        "jus d'orange": 3.30,
        "appelsap": 3.30,
        "chocomel": 3.30,
        "fristi": 3.30,
        "red bull": 3.50,
        "aa drink": 3.50
    },
    "warme dranken": {
        "koffie": 3.00,
        "cappuccino": 3.25,
        "latte macchiato": 3.75,
        "koffie verkeerd": 3.25,
        "thee": 3.00
    },
    "milkshakes": {
        "klein": 3.25,
        "medium": 3.75,
        "groot": 4.25
    }
}

# Synoniemen voor menu items (klanten zeggen vaak andere woorden)
# Uitgebreide lijst met veelvoorkomende variaties en typfouten
SYNONYMS = {
    # Friet variaties
    "patat": "friet",
    "patatje": "friet",
    "pata": "friet",  # typo
    "pataat": "friet",  # typo
    "frietje": "friet",
    "frites": "friet",
    "frieten": "friet",
    "fritten": "friet",  # typo
    "french fries": "friet",
    "frie": "friet",  # afgekapt

    # Saus variaties
    "mayo": "mayonaise",
    "mayonais": "mayonaise",  # zonder e
    "majonaise": "mayonaise",  # andere spelling

    # Snacks
    "frikadel": "frikandel",
    "frikandellen": "frikandel",
    "frika": "frikandel",  # afkorting
    "kroketje": "kroket",
    "kroketten": "kroket",
    "croquette": "kroket",
    "bitterbal": "gehaktbal",

    # Dranken
    "cola": "coca cola",
    "coke": "coca cola",
    "cocacola": "coca cola",
    "pepsi": "coca cola",
    "fanta": "blikje fanta",
    "sprite": "blikje sprite",
    "rivella": "blikje rivella",
    "tonic": "blikje tonic",
    "bitter lemon": "blikje bitter lemon",
    "fuze tea": "blikje fuze tea",
    "fuzetea": "blikje fuze tea",
    "ice tea": "blikje fuze tea",
    "icetea": "blikje fuze tea",
    "cassis": "blikje cassis",
    "sinas": "blikje fanta",
    "sinaasappel": "jus d'orange",
    "jus": "jus d'orange",
    "appel": "appelsap",

    # IJs
    "icecream": "ijs",
    "ijsje": "ijs",
    "bolletje": "bol",
    "bolletjes": "bollen",
    "ijsbolletje": "ijs",
    "softice": "softijs",
    "soft ijs": "softijs",
    "slagroom": "softijs",

    # Hamburgers
    "cheeseburger": "dorpspomp kaas",
    "cheese burger": "dorpspomp kaas",
    "kaashamburger": "dorpspomp kaas",
    "burger": "dorpspomp",
    "hamburger": "dorpspomp",
    "hamburgertje": "dorpspomp",

    # Broodjes
    "broodje kroket": "kroket",
    "broodje frikandel": "frikandel",
    "broodje bal": "bal",
    "broodje carpaccio": "carpaccio",
    "broodje gezond": "gezond",
    "broodje warme kip": "warme kip",
    "broodje kip": "warme kip",

    # Milkshakes
    "shake": "milkshake",
    "milkshakes": "milkshake",

    # Kaassoufle variaties
    "souffle": "soufle",
    "soufflé": "soufle",
    "kaassouffle": "kaassoufle",
    "kaassoufflé": "kaassoufle",
    "soefle": "soufle",
    "kaas souffle": "kaassoufle",

    # Koffie variaties
    "cappucino": "cappuccino",  # typo
    "capuccino": "cappuccino",  # typo
    "latte": "latte macchiato",

    # Grootte variaties
    "grote": "groot",
    "kleine": "klein",
    "middelgroot": "medium",
    "middel": "medium",

    # Overige
    "nugget": "kipnuggets",
    "nuggets": "kipnuggets",
    "kipnugget": "kipnuggets",
    "satestokjes": "kipsatestokjes",
    "sate stokjes": "kipsatestokjes",
}

# =============================================================================
# PRE-BUILT INDEX voor snelle lookups (gebouwd bij import)
# =============================================================================
_MENU_INDEX: Dict[str, Dict] = {}  # lowercase name -> {name, price, category}
_MENU_WORDS_INDEX: Dict[str, List[Dict]] = {}  # word -> list of items containing that word
_INDEX_BUILT = False


def _build_menu_index():
    """Bouw menu index bij eerste gebruik (lazy loading)"""
    global _MENU_INDEX, _MENU_WORDS_INDEX, _INDEX_BUILT

    if _INDEX_BUILT:
        return

    for category, items in MENU.items():
        for item_name, price in items.items():
            item_data = {
                "name": item_name,
                "price": price,
                "category": category
            }

            # Exacte naam index (lowercase)
            name_lower = item_name.lower()
            _MENU_INDEX[name_lower] = item_data

            # Ook zonder accenten
            name_normalized = _remove_accents_fast(name_lower)
            if name_normalized != name_lower:
                _MENU_INDEX[name_normalized] = item_data

            # Woorden index voor partial matching
            words = name_lower.split()
            for word in words:
                if word not in _MENU_WORDS_INDEX:
                    _MENU_WORDS_INDEX[word] = []
                _MENU_WORDS_INDEX[word].append(item_data)

                # Ook genormaliseerde versie
                word_norm = _remove_accents_fast(word)
                if word_norm != word:
                    if word_norm not in _MENU_WORDS_INDEX:
                        _MENU_WORDS_INDEX[word_norm] = []
                    _MENU_WORDS_INDEX[word_norm].append(item_data)

    _INDEX_BUILT = True


def _remove_accents_fast(text: str) -> str:
    """Snelle accent removal zonder unicodedata import elke keer"""
    replacements = {
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u',
        'ñ': 'n', 'ç': 'c'
    }
    for acc, repl in replacements.items():
        text = text.replace(acc, repl)
    return text


def remove_accents(text: str) -> str:
    """Verwijder accenten van letters (é → e, ë → e, etc.)"""
    import unicodedata
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


def normalize_query(query: str) -> str:
    """
    Normaliseer een zoekterm met synoniemen

    Voorbeelden:
    - "patat" → "friet"
    - "patatje zonder" → "friet zonder"
    - "kroketje" → "kroket"
    - "kaassoufflé" → "kaassoufle"
    """
    query = query.lower().strip()

    # Verwijder accenten (é → e, etc.)
    query = remove_accents(query)

    # 1) Vervang eerst multi-word synoniemen (bijv. "french fries")
    phrase_synonyms = [
        (synonym, replacement)
        for synonym, replacement in SYNONYMS.items()
        if " " in synonym
    ]
    for synonym, replacement in sorted(phrase_synonyms, key=lambda x: len(x[0]), reverse=True):
        pattern = r"(?<!\w)" + re.escape(synonym) + r"(?!\w)"
        query = re.sub(pattern, replacement, query)

    # 2) Vervang losse woorden exact 1x per token (geen cascades zoals cola -> coca cola -> coca coca cola)
    word_synonyms = {
        synonym: replacement
        for synonym, replacement in SYNONYMS.items()
        if " " not in synonym
    }
    tokens = query.split()
    normalized_tokens = [word_synonyms.get(token, token) for token in tokens]

    return " ".join(normalized_tokens).strip()


def search_item(query: str):
    """
    Zoek een item in het menu op basis van een query string
    Ondersteunt synoniemen (bijv. "patat" → "friet")
    """
    query = query.lower().strip()

    # Normaliseer query met synoniemen en verwijder accenten
    normalized = normalize_query(query)

    results = []

    for category, items in MENU.items():
        for item_name, price in items.items():
            # Verwijder ook accenten uit item naam voor vergelijking
            item_name_normalized = remove_accents(item_name.lower())

            # Zoek met zowel originele als genormaliseerde query
            if normalized in item_name_normalized or query in item_name.lower():
                results.append({
                    "name": item_name,
                    "price": price,
                    "category": category
                })

    return results


def fuzzy_match(s1: str, s2: str) -> float:
    """
    Bereken similarity ratio tussen twee strings (0.0 - 1.0)
    Simpele implementatie zonder externe dependencies
    """
    s1 = s1.lower()
    s2 = s2.lower()

    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    # Longest Common Subsequence ratio
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs_length = dp[m][n]
    return (2.0 * lcs_length) / (m + n)


def fuzzy_search_item(query: str, threshold: float = 0.6):
    """
    Zoek items met fuzzy matching voor typfouten

    Args:
        query: Zoekterm
        threshold: Minimum similarity score (0.0 - 1.0)

    Returns:
        Lijst van items met score, gesorteerd op relevantie
    """
    query = query.lower().strip()
    normalized = normalize_query(query)

    results = []

    for category, items in MENU.items():
        for item_name, price in items.items():
            item_name_lower = item_name.lower()
            item_name_normalized = remove_accents(item_name_lower)

            # Exacte match heeft hoogste score
            if normalized in item_name_normalized or query in item_name_lower:
                results.append({
                    "name": item_name,
                    "price": price,
                    "category": category,
                    "score": 1.0,
                    "match_type": "exact"
                })
            else:
                # Fuzzy match
                # Check elk woord in de item naam
                item_words = item_name_normalized.split()
                best_score = 0.0

                for word in item_words:
                    score = fuzzy_match(normalized, word)
                    if score > best_score:
                        best_score = score

                # Check ook hele naam
                full_score = fuzzy_match(normalized, item_name_normalized)
                if full_score > best_score:
                    best_score = full_score

                if best_score >= threshold:
                    results.append({
                        "name": item_name,
                        "price": price,
                        "category": category,
                        "score": best_score,
                        "match_type": "fuzzy"
                    })

    # Sorteer op score (hoogste eerst)
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


@lru_cache(maxsize=256)
def _cached_smart_search(query: str) -> tuple:
    """Cached versie van smart search - returns tuple voor hashability"""
    # Probeer eerst exacte match
    results = search_item(query)

    if results:
        return tuple((r["name"], r["price"], r["category"]) for r in results)

    # Geen exacte match, probeer fuzzy
    fuzzy_results = fuzzy_search_item(query, threshold=0.6)

    # Filter alleen hoge scores voor fuzzy
    good_fuzzy = [r for r in fuzzy_results if r["score"] >= 0.7]

    if good_fuzzy:
        return tuple((r["name"], r["price"], r["category"]) for r in good_fuzzy)

    # Return fuzzy results met lagere threshold als backup
    if fuzzy_results:
        return tuple((r["name"], r["price"], r["category"]) for r in fuzzy_results[:5])

    return tuple()


def smart_search_item(query: str) -> List[Dict]:
    """
    Slimme zoekfunctie die eerst exacte match probeert,
    dan fuzzy match als er geen resultaten zijn.

    GEOPTIMALISEERD: Cached results voor herhaalde queries.
    """
    _build_menu_index()  # Ensure index exists

    # Normaliseer query
    query = query.lower().strip()
    if not query:
        return []

    # Gebruik cached versie
    cached = _cached_smart_search(query)

    # Convert tuple terug naar list of dicts
    return [{"name": r[0], "price": r[1], "category": r[2]} for r in cached]


def clear_search_cache():
    """Clear de search cache (bijv. na menu update)"""
    _cached_smart_search.cache_clear()


def get_item_price(item_name: str) -> Optional[float]:
    """Haal de prijs op van een specifiek item - GEOPTIMALISEERD met index"""
    _build_menu_index()  # Ensure index is built

    item_name = normalize_query(item_name).lower()

    # O(1) lookup in index
    if item_name in _MENU_INDEX:
        return _MENU_INDEX[item_name]["price"]

    # Partial match via words index
    for word in item_name.split():
        if word in _MENU_WORDS_INDEX:
            # Return eerste match
            return _MENU_WORDS_INDEX[word][0]["price"]

    # Fallback: check of item_name IN een menu item zit
    for key, data in _MENU_INDEX.items():
        if item_name in key or key in item_name:
            return data["price"]

    return None


def get_item_with_price(item_name: str) -> Optional[Dict]:
    """
    NIEUWE FUNCTIE: Haal item + prijs in één lookup
    Voorkomt dubbel zoeken in add_to_cart

    Returns: {"name": str, "price": float, "category": str} of None
    """
    _build_menu_index()

    original_name = item_name
    item_name = normalize_query(item_name).lower()

    # O(1) exacte lookup
    if item_name in _MENU_INDEX:
        return _MENU_INDEX[item_name].copy()

    # Partial match via words index
    for word in item_name.split():
        if len(word) >= 3 and word in _MENU_WORDS_INDEX:
            return _MENU_WORDS_INDEX[word][0].copy()

    # Fallback: substring match
    for key, data in _MENU_INDEX.items():
        if item_name in key or key in item_name:
            return data.copy()

    # Laatste poging: smart search (met fuzzy)
    results = smart_search_item(original_name)
    if results:
        return {
            "name": results[0]["name"],
            "price": results[0]["price"],
            "category": results[0]["category"]
        }

    return None


def format_price(price: float) -> str:
    """Format prijs naar euro string"""
    if price is None:
        return "Prijs onbekend"
    return f"EUR {price:.2f}".replace(".", ",")


def format_price_spoken(price: float) -> str:
    """Format prijs voor natuurlijke Nederlandse uitspraak."""
    if price is None:
        return "prijs onbekend"

    value = float(price)
    euros = int(value)
    cents = int(round((value - euros) * 100))
    if cents == 100:
        euros += 1
        cents = 0

    if cents == 0:
        return f"{euros} euro"
    return f"{euros} euro en {cents:02d} cent"


def calculate_order_total(items: list) -> dict:
    """
    Bereken totaalprijs van een bestelling

    Args:
        items: list van dicts met keys: name, qty

    Returns:
        dict met totaal en per-item prijzen
    """
    total = 0.0
    items_with_prices = []

    for item in items:
        item_name = item.get("name", "").lower()
        raw_qty = item.get("qty", item.get("quantity", 1))
        if isinstance(raw_qty, int):
            qty = raw_qty
        elif isinstance(raw_qty, float):
            qty = int(raw_qty)
        elif isinstance(raw_qty, str):
            text = raw_qty.strip().lower()
            qty_words = {
                "een": 1, "eentje": 1,
                "twee": 2, "drie": 3, "vier": 4, "vijf": 5,
                "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10
            }
            if text in qty_words:
                qty = qty_words[text]
            else:
                match = re.search(r"\d+", text)
                qty = int(match.group(0)) if match else 1
        else:
            qty = 1
        qty = max(1, qty)

        price = get_item_price(item_name)

        if price is not None:
            subtotal = price * qty
            total += subtotal

            items_with_prices.append({
                "name": item.get("name"),
                "qty": qty,
                "price_per_item": price,
                "subtotal": subtotal
            })
        else:
            # Item niet gevonden in menu
            items_with_prices.append({
                "name": item.get("name"),
                "qty": qty,
                "price_per_item": None,
                "subtotal": None
            })

    return {
        "items": items_with_prices,
        "total": total,
        "formatted_total": format_price(total),
        "spoken_total": format_price_spoken(total)
    }
