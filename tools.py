"""
Tool definities voor De Dorpspomp & Dieks IJssalon Retell AI Agent
SIMPELE 3-STATE MACHINE voor wijzigingen zonder reset
"""

def get_tools_config(webhook_url=None):
    """
    Retourneert basis tools + update/remove tools
    """

    tools = [
        {
            "type": "end_call",
            "name": "end_call",
            "description": "Beëindig het gesprek"
        }
    ]

    # Als er een webhook URL is, voeg custom tools toe
    if webhook_url:
        custom_tools = [
            {
                "type": "custom",
                "name": "get_menu",
                "description": "Haal VOLLEDIG menu op met ALLE categorieën (friet, snacks, dranken, ijs, etc.). Gebruik ALLEEN als klant expliciet vraagt: 'wat heb je allemaal', 'wat staat er op menu', 'wat kan ik bestellen'. NIET gebruiken voor specifieke items - gebruik dan search_menu.",
                "url": f"{webhook_url}/tools/menu",
                "method": "GET",
                "parameters": {
                    "type": "object",
                    "properties": {}
                },
                "speak_after_execution": True
            },
            {
                "type": "custom",
                "name": "search_menu",
                "description": "Zoek SPECIFIEKE menu items op naam. Begrijpt synoniemen: patat=friet, frikadel=frikandel, cola=coca-cola. Gebruik dit ALTIJD als klant een specifiek item noemt (bijv. 'patat', 'frikandel', 'cola'). Retourneert lijst met matches inclusief varianten.",
                "url": f"{webhook_url}/tools/search_menu",
                "method": "POST",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Zoekterm: exact wat klant zegt (bijv. 'patat', 'frikadel', 'cola', 'kroketje')"
                        }
                    },
                    "required": ["query"]
                },
                "speak_after_execution": True
            },
            {
                "type": "custom",
                "name": "add_to_cart",
                "description": "Voeg item toe aan winkelwagen. Gebruik EXACTE naam uit search_menu resultaat. Bijvoorbeeld: als search_menu 'friet met mayonaise' retourneert, gebruik exact die naam.",
                "url": f"{webhook_url}/tools/add_to_cart",
                "method": "POST",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "EXACTE itemnaam uit search_menu (bijv. 'friet met mayonaise', 'frikandel speciaal')"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Aantal (minimaal 1, default 1)",
                            "minimum": 1
                        }
                    },
                    "required": ["item", "quantity"]
                },
                "speak_after_execution": False
            },
            {
                "type": "custom",
                "name": "update_cart",
                "description": "Wijzig aantal van een item in de bestelling",
                "url": f"{webhook_url}/tools/update_cart",
                "method": "POST",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "Item naam om te wijzigen"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Nieuw aantal",
                            "minimum": 1
                        }
                    },
                    "required": ["item_id", "quantity"]
                },
                "speak_after_execution": False
            },
            {
                "type": "custom",
                "name": "remove_from_cart",
                "description": "Verwijder item uit bestelling",
                "url": f"{webhook_url}/tools/remove_from_cart",
                "method": "POST",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "Item naam om te verwijderen"
                        }
                    },
                    "required": ["item_id"]
                },
                "speak_after_execution": False
            },
            {
                "type": "custom",
                "name": "get_cart",
                "description": "Haal huidige bestelling op",
                "url": f"{webhook_url}/tools/cart",
                "method": "GET",
                "parameters": {
                    "type": "object",
                    "properties": {}
                },
                "speak_after_execution": False
            },
            {
                "type": "custom",
                "name": "send_order",
                "description": "Verstuur bestelling",
                "url": f"{webhook_url}/order",
                "method": "POST",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "Naam klant"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Telefoonnummer"
                        },
                        "pickup_time": {
                            "type": "string",
                            "description": "Afhaaltijd HH:MM (bijv. 18:30)"
                        },
                        "items": {
                            "type": "array",
                            "description": "Bestelde items",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "qty": {"type": "integer", "minimum": 1}
                                },
                                "required": ["name", "qty"]
                            }
                        }
                    },
                    "required": ["items", "pickup_time"]
                },
                "speak_after_execution": True
            }
        ]
        tools.extend(custom_tools)

    return tools


def get_states_with_tools(webhook_url=None):
    """
    VEREENVOUDIGDE 3-STATE MACHINE
    Kortere prompts, duidelijke transities
    """
    tools = get_tools_config(webhook_url)

    # Helper om tools te filteren op naam
    tools_by_name = {t["name"]: t for t in tools}

    def get_tools_by_names(names):
        return [tools_by_name[name] for name in names if name in tools_by_name]

    states = [
        {
            "name": "greeting",
            "state_prompt": """Begroet de klant kort en vriendelijk.

Begin met: "Hoi, je spreekt met de Dorpspomp. Wat kan ik voor je doen?"

Luister naar de klant. Als ze willen bestellen of eten noemen, ga naar ordering.""",
            "edges": [
                {
                    "destination_state_name": "ordering",
                    "description": "Klant noemt eten, drinken, of wil bestellen"
                }
            ],
            "tools": []
        },
        {
            "name": "ordering",
            "state_prompt": """Neem de bestelling op:

1. Vraag naam (als nog niet bekend)
2. Vraag wat ze willen bestellen
3. Gebruik search_menu om items te zoeken
4. Gebruik add_to_cart om toe te voegen
5. Vraag "Verder nog iets?"
6. Vraag afhaaltijd (openingstijden: wo-do 11:30-19:30, vr-zo 11:30-20:00)
7. Herhaal bestelling en vraag bevestiging

BELANGRIJK:
- search_menu begrijpt synoniemen (patat=friet, cola=coca cola)
- Als resultaten gevonden: item bestaat!
- Noem NOOIT prijzen""",
            "edges": [
                {
                    "destination_state_name": "confirm",
                    "description": "Klant bevestigt (ja, klopt, prima, goed, oke, dat is goed, correct)"
                }
            ],
            "tools": get_tools_by_names(["get_menu", "search_menu", "add_to_cart", "update_cart", "remove_from_cart", "get_cart"])
        },
        {
            "name": "confirm",
            "state_prompt": """Rond de bestelling af:

1. Gebruik send_order om de bestelling te versturen
2. Zeg: "Top! Je bestelling staat klaar om [tijd]. Tot zo!"
3. Beeindig het gesprek met end_call

Als klant wil wijzigen, ga terug naar ordering.""",
            "edges": [
                {
                    "destination_state_name": "ordering",
                    "description": "Klant wil wijzigen, aanpassen, of toch iets anders"
                }
            ],
            "tools": get_tools_by_names(["get_cart", "send_order"])
        }
    ]

    return states
