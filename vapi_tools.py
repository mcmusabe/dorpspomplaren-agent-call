"""
VAPI Tool definities voor De Dorpspomp & Dieks IJssalon
Tools in VAPI format (verschilt van Retell format)
"""


def get_vapi_tools(webhook_url: str) -> list:
    """
    Retourneert tools in VAPI format.

    VAPI gebruikt:
    - type: "function" met nested "function" object
    - server.url voor HTTP endpoints
    - async: true voor server-side tools
    """

    if not webhook_url:
        return []

    tools = [
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "get_menu",
                "description": "Haal het volledige menu op met alle categorieen (friet, snacks, ijs, dranken). Gebruik als klant vraagt wat er op het menu staat.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/get_menu"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "search_menu",
                "description": "Zoek items in het menu op naam. GEBRUIK DEZE TOOL wanneer klant iets wil bestellen zoals friet, snack, ijs of drinken.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Wat de klant wil bestellen (bijv. 'friet', 'frikandel', 'cola', 'ijsje')"
                        }
                    },
                    "required": ["query"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/search_menu",
                "timeoutSeconds": 5
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "add_to_cart",
                "description": "Voeg item toe aan bestelling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "Item naam"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Aantal",
                            "default": 1
                        }
                    },
                    "required": ["item"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/add_to_cart",
                "timeoutSeconds": 5
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "get_cart",
                "description": "Haal de huidige bestelling op om te controleren wat er in zit.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/get_cart"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "update_cart",
                "description": "Wijzig het aantal van een item in de bestelling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "Naam van het item om te wijzigen (bijv. 'friet speciaal', 'frikandel')"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Nieuw aantal",
                            "minimum": 1
                        }
                    },
                    "required": ["item", "quantity"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/update_cart"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "remove_from_cart",
                "description": "Verwijder een item uit de bestelling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "Naam van het item om te verwijderen (bijv. 'friet speciaal', 'frikandel')"
                        }
                    },
                    "required": ["item"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/remove_from_cart"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "check_pickup_time",
                "description": "Controleer of een afhaaltijd geldig is (binnen openingstijden).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pickup_time": {
                            "type": "string",
                            "description": "Afhaaltijd in HH:MM format (bijv. '18:30')"
                        }
                    },
                    "required": ["pickup_time"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/check_pickup_time"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "send_order",
                "description": "Verstuur de bestelling. Gebruik ALLEEN nadat klant heeft bevestigd.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "Naam van de klant"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Telefoonnummer (optioneel)"
                        },
                        "pickup_time": {
                            "type": "string",
                            "description": "Afhaaltijd in HH:MM format"
                        },
                        "items": {
                            "type": "array",
                            "description": "Bestelde items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "qty": {"type": "integer", "minimum": 1},
                                    "notes": {"type": "string"}
                                },
                                "required": ["name", "qty"]
                            }
                        },
                        "extra_notes": {
                            "type": "string",
                            "description": "Extra opmerkingen voor de hele bestelling"
                        }
                    },
                    "required": ["pickup_time", "items"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/order"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "get_opening_hours",
                "description": "Haal de openingstijden op en check of we nu open zijn.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/hours"
            }
        }
    ]

    return tools


def get_vapi_end_call_tool() -> dict:
    """
    VAPI end call tool (built-in, geen server nodig)
    """
    return {
        "type": "endCall",
        "function": {
            "name": "end_call",
            "description": "Beeindig het gesprek nadat de bestelling is verzonden of klant klaar is."
        }
    }
