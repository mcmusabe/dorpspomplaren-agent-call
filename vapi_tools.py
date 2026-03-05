"""
VAPI Tool definities voor De Dorpspomp & Dieks IJssalon
"""


def get_vapi_tools(webhook_url: str) -> list:
    """Retourneert tools in VAPI format."""

    if not webhook_url:
        return []

    tools = [
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "get_menu",
                "description": "Haal het volledige menu op met alle categorieën en items. Gebruik wanneer de klant vraagt wat er te bestellen is of het menu wil zien.",
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
                "description": "Zoek een specifiek item in het menu op naam. GEBRUIK DEZE TOOL ALTIJD voordat je add_to_cart aanroept, om de exacte itemnaam te vinden. Voorbeelden: 'friet speciaal', 'kroket', 'cola', 'softijs'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Wat de klant wil bestellen, zo letterlijk mogelijk (bijv. 'friet speciaal groot', 'frikandel', 'blikje cola', 'ijs 2 bollen')"
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
                "description": "Voeg een item toe aan de bestelling. Gebruik ALTIJD eerst search_menu om de exacte itemnaam te vinden. Als het item niet gevonden wordt, krijg je status 'not_found' terug.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "Exacte itemnaam zoals gevonden via search_menu (bijv. 'friet speciaal', 'kroket rundvlees', 'blikje coca cola')"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Aantal stuks (standaard 1)",
                            "default": 1
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optionele opmerking bij dit item (bijv. 'extra krokant', 'zonder ui')"
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
                "description": "Bekijk wat er in de huidige bestelling zit. Geeft een lijst van items met naam en aantal.",
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
                "description": "Wijzig het aantal van een item dat al in de bestelling zit.",
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
                "description": "Verwijder een item volledig uit de bestelling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item": {
                            "type": "string",
                            "description": "Naam van het item om te verwijderen"
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
                "description": "Controleer of een afhaaltijd geldig is (binnen openingstijden en niet in het verleden). Geeft een melding als de tijd ongeldig is.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pickup_time": {
                            "type": "string",
                            "description": "Afhaaltijd in HH:MM format (bijv. '14:30', '18:00')"
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
                "description": "Verstuur de definitieve bestelling. Gebruik ALLEEN nadat de klant naam, afhaaltijd en items heeft bevestigd. Haalt items automatisch uit de cart.",
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
                            "description": "Bevestigde afhaaltijd in HH:MM format"
                        },
                        "items": {
                            "type": "array",
                            "description": "Bestelde items (wordt automatisch uit cart gehaald als leeg)",
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
                    "required": ["customer_name", "pickup_time"]
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
                "description": "Haal de openingstijden op en check of we nu open of gesloten zijn. Gebruik bij elke vraag over openingstijden.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/hours"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "get_suggestions",
                "description": "Haal slimme suggesties op gebaseerd op wat er in de bestelling zit. Gebruik na elke toevoeging aan de cart. Geeft suggesties voor ontbrekende categorieën zoals drankje of toetje, en populaire items.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/get_suggestions"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "confirm_order",
                "description": "Maak een besteloverzicht aan om voor te lezen aan de klant ter bevestiging. Gebruik ALTIJD voordat je send_order aanroept. Lees het overzicht voor en vraag of het klopt.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "Naam van de klant"
                        },
                        "pickup_time": {
                            "type": "string",
                            "description": "Afhaaltijd in HH:MM format"
                        }
                    },
                    "required": ["customer_name", "pickup_time"]
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/confirm_order"
            }
        },
        {
            "type": "function",
            "async": False,
            "function": {
                "name": "handoff_to_human",
                "description": "Verbind door naar een medewerker. Gebruik wanneer de klant geen bestelling wil plaatsen, om een medewerker vraagt, of een vraag heeft die je niet kunt beantwoorden.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Korte reden voor het doorverbinden"
                        }
                    },
                    "required": []
                }
            },
            "server": {
                "url": f"{webhook_url}/vapi/tools/handoff"
            }
        }
    ]

    return tools


def get_vapi_end_call_tool() -> dict:
    """VAPI end call tool (built-in)"""
    return {
        "type": "endCall",
        "function": {
            "name": "end_call",
            "description": "Beëindig het gesprek nadat de bestelling succesvol is verzonden of de klant het gesprek wil beëindigen."
        }
    }
