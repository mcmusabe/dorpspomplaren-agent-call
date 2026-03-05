import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import webhook_order
from opening_hours import is_pickup_time_valid, is_open_now, now_nl, NL_TZ
from menu import (
    normalize_query, search_item, smart_search_item, get_item_with_price,
    get_item_price, format_price, format_price_spoken, calculate_order_total
)


class BackendGuardrailsTests(unittest.TestCase):
    def setUp(self):
        webhook_order.cart_store.clear()
        self.client = TestClient(webhook_order.app)

    def _vapi_payload(self, tool_name, parameters=None, call_id="test-call-1", tool_id="tc-1"):
        return {
            "message": {
                "type": "tool-calls",
                "toolCallList": [
                    {
                        "id": tool_id,
                        "name": tool_name,
                        "parameters": parameters or {},
                    }
                ],
            },
            "call": {"id": call_id},
        }

    # =========================================================================
    # COERCE QUANTITY
    # =========================================================================
    def test_coerce_quantity_variants(self):
        cq = webhook_order.coerce_quantity
        self.assertEqual(cq("3"), 3)
        self.assertEqual(cq("3x"), 3)
        self.assertEqual(cq("drie"), 3)
        self.assertEqual(cq("twee"), 2)
        self.assertEqual(cq("tien"), 10)
        self.assertEqual(cq(2.8), 2)
        self.assertEqual(cq(None), 1)
        self.assertEqual(cq(True), 1)  # bool edge case
        self.assertEqual(cq(""), 1)
        self.assertEqual(cq(0), 1)  # min 1

    # =========================================================================
    # PRICE FORMATTING
    # =========================================================================
    def test_format_price(self):
        self.assertEqual(format_price(3.75), "EUR 3,75")
        self.assertEqual(format_price(0), "EUR 0,00")
        self.assertEqual(format_price(10.0), "EUR 10,00")
        self.assertEqual(format_price(None), "Prijs onbekend")

    def test_format_price_spoken(self):
        self.assertEqual(format_price_spoken(3.75), "3 euro en 75 cent")
        self.assertEqual(format_price_spoken(5.0), "5 euro")
        self.assertEqual(format_price_spoken(0), "0 euro")
        self.assertEqual(format_price_spoken(12.50), "12 euro en 50 cent")

    # =========================================================================
    # STRIP VOICE PRICE FIELDS
    # =========================================================================
    def test_strip_voice_price_fields_recursive(self):
        payload = {
            "price": 3.75,
            "cart": {
                "total": 12.5,
                "items": [{"name": "friet", "qty": 2, "price_formatted": "EUR 3,75"}],
            },
            "message": "ok",
        }
        clean = webhook_order.strip_voice_price_fields(payload)
        self.assertNotIn("price", clean)
        self.assertNotIn("total", clean["cart"])
        self.assertNotIn("price_formatted", clean["cart"]["items"][0])
        self.assertEqual(clean["message"], "ok")

    # =========================================================================
    # MENU SYNONYMS
    # =========================================================================
    def test_normalize_query_friet(self):
        self.assertEqual(normalize_query("patat"), "friet")
        self.assertEqual(normalize_query("patatje"), "friet")
        self.assertEqual(normalize_query("frietje"), "friet")
        self.assertEqual(normalize_query("frites"), "friet")

    def test_normalize_query_phrase_synonyms(self):
        self.assertEqual(normalize_query("patatje oorlog"), "friet oorlog")
        self.assertEqual(normalize_query("patat speciaal"), "friet speciaal")
        self.assertEqual(normalize_query("patatje sate"), "friet sate")
        self.assertEqual(normalize_query("patatje met"), "friet met mayonaise")

    def test_normalize_query_dranken(self):
        self.assertEqual(normalize_query("cola"), "coca cola")
        self.assertIn("coca cola", normalize_query("colaatje"))
        # "cola zero" is a phrase synonym → "coca cola zero"
        # "cola" inside result should NOT cascade to "coca coca cola zero"
        result = normalize_query("cola zero")
        self.assertEqual(result, "coca cola zero")

    def test_normalize_query_snacks(self):
        self.assertEqual(normalize_query("frikadel"), "frikandel")
        self.assertEqual(normalize_query("kipkorn"), "kipcorn")
        self.assertEqual(normalize_query("berenhap"), "berehap")

    def test_normalize_query_no_cascade(self):
        """cola -> coca cola should NOT become coca coca cola"""
        result = normalize_query("cola")
        self.assertEqual(result, "coca cola")
        self.assertNotIn("coca coca", result)

    # =========================================================================
    # MENU SEARCH
    # =========================================================================
    def test_search_item_exact(self):
        results = search_item("friet speciaal")
        names = [r["name"] for r in results]
        self.assertIn("friet speciaal", names)

    def test_search_item_synonym(self):
        results = search_item("patatje oorlog")
        names = [r["name"] for r in results]
        self.assertIn("friet oorlog", names)

    def test_search_item_cola(self):
        results = search_item("cola")
        names = [r["name"] for r in results]
        self.assertTrue(any("coca cola" in n for n in names))

    def test_get_item_with_price_returns_correct(self):
        item = get_item_with_price("friet speciaal")
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "friet speciaal")
        self.assertEqual(item["price"], 3.75)

    def test_get_item_with_price_synonym(self):
        item = get_item_with_price("patatje oorlog")
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "friet oorlog")

    def test_get_item_with_price_not_found(self):
        item = get_item_with_price("xylofoon taart")
        self.assertIsNone(item)

    # =========================================================================
    # CALCULATE ORDER TOTAL
    # =========================================================================
    def test_calculate_order_total_basic(self):
        items = [
            {"name": "friet speciaal", "qty": 2},
            {"name": "kroket rundvlees", "qty": 1},
        ]
        result = calculate_order_total(items)
        # friet speciaal = 3.75 * 2 = 7.50, kroket rundvlees = 2.85
        expected = 7.50 + 2.85
        self.assertAlmostEqual(result["total"], expected, places=2)

    def test_calculate_order_total_string_qty(self):
        items = [{"name": "kroket rundvlees", "qty": "drie"}]
        result = calculate_order_total(items)
        self.assertAlmostEqual(result["total"], 2.85 * 3, places=2)

    def test_calculate_order_total_unknown_item(self):
        items = [{"name": "sushi deluxe platter", "qty": 1}]
        result = calculate_order_total(items)
        self.assertEqual(result["total"], 0.0)
        self.assertIsNone(result["items"][0]["price_per_item"])

    # =========================================================================
    # OPENING HOURS
    # =========================================================================
    def test_timezone_is_amsterdam(self):
        now = now_nl()
        self.assertEqual(str(now.tzinfo), "Europe/Amsterdam")

    def test_pickup_time_closed_day(self):
        # Dinsdag = gesloten
        check = is_pickup_time_valid("12:00", pickup_date=datetime(2026, 2, 17, 10, 0, tzinfo=NL_TZ))
        self.assertFalse(check["valid"])
        self.assertIn("gesloten", check["reason"])
        self.assertIn("open op", check["reason"])

    def test_pickup_time_too_early(self):
        # Woensdag 10:00, open om 11:30
        check = is_pickup_time_valid("10:00", pickup_date=datetime(2026, 3, 4, 10, 0, tzinfo=NL_TZ))
        self.assertFalse(check["valid"])
        self.assertIn("11:30", check["reason"])

    def test_pickup_time_valid(self):
        # Woensdag 15:00
        check = is_pickup_time_valid("15:00", pickup_date=datetime(2026, 3, 4, 14, 0, tzinfo=NL_TZ))
        self.assertTrue(check["valid"])

    def test_pickup_time_too_late(self):
        # Woensdag 19:20 (sluit 19:30, buffer 15 min)
        check = is_pickup_time_valid("19:20", pickup_date=datetime(2026, 3, 4, 14, 0, tzinfo=NL_TZ))
        self.assertFalse(check["valid"])
        self.assertIn("sluiten", check["reason"])

    def test_pickup_time_invalid_format(self):
        check = is_pickup_time_valid("half zes", pickup_date=datetime(2026, 3, 4, 14, 0, tzinfo=NL_TZ))
        self.assertFalse(check["valid"])
        self.assertIn("Ongeldige", check["reason"])

    # =========================================================================
    # VAPI ENDPOINTS
    # =========================================================================
    def test_vapi_search_menu_hides_price_fields(self):
        response = self.client.post(
            "/vapi/tools/search_menu",
            json=self._vapi_payload("search_menu", {"query": "friet speciaal"}),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data["results"][0]["result"]["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertIn("name", items[0])
        self.assertNotIn("price", items[0])
        self.assertNotIn("price_formatted", items[0])
        self.assertNotIn("price_spoken", items[0])

    def test_vapi_add_to_cart_success(self):
        response = self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "blikje coca cola", "quantity": 3}),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]["result"]

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["qty"], 3)
        self.assertEqual(result["item"], "blikje coca cola")
        self.assertEqual(result["cart_count"], 1)
        # No price fields in response
        self.assertNotIn("price", result)
        self.assertNotIn("total", result)

    def test_vapi_add_to_cart_not_found(self):
        response = self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "xylofoon taart"}),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["status"], "not_found")
        self.assertIn("niet op het menu", result["message"])

    def test_vapi_add_to_cart_merges_duplicates(self):
        # Add friet speciaal twice
        self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "friet speciaal", "quantity": 1}),
        )
        self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "friet speciaal", "quantity": 2}),
        )
        # Check cart has 1 item with qty 3
        response = self.client.post(
            "/vapi/tools/get_cart",
            json=self._vapi_payload("get_cart"),
        )
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["qty"], 3)

    def test_vapi_get_cart_empty(self):
        response = self.client.post(
            "/vapi/tools/get_cart",
            json=self._vapi_payload("get_cart"),
        )
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["count"], 0)
        self.assertTrue(result["empty"])
        self.assertEqual(result["items"], [])
        # No price fields
        self.assertNotIn("total", result)
        self.assertNotIn("total_formatted", result)

    def test_vapi_get_cart_no_price_fields(self):
        """Cart response should only contain name and qty, no prices"""
        self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "frikandel", "quantity": 2}),
        )
        response = self.client.post(
            "/vapi/tools/get_cart",
            json=self._vapi_payload("get_cart"),
        )
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["count"], 1)
        item = result["items"][0]
        self.assertIn("name", item)
        self.assertIn("qty", item)
        self.assertNotIn("price", item)

    def test_vapi_remove_from_cart(self):
        self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "frikandel"}),
        )
        response = self.client.post(
            "/vapi/tools/remove_from_cart",
            json=self._vapi_payload("remove_from_cart", {"item": "frikandel"}),
        )
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["status"], "ok")

    def test_vapi_update_cart(self):
        self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "frikandel", "quantity": 1}),
        )
        response = self.client.post(
            "/vapi/tools/update_cart",
            json=self._vapi_payload("update_cart", {"item": "frikandel", "quantity": 5}),
        )
        result = response.json()["results"][0]["result"]
        self.assertEqual(result["status"], "ok")

    def test_vapi_hours_returns_status(self):
        response = self.client.post(
            "/vapi/tools/hours",
            json=self._vapi_payload("get_opening_hours"),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]["result"]
        self.assertIn("currently_open", result)
        self.assertIn("status_message", result)

    def test_vapi_check_pickup_time(self):
        response = self.client.post(
            "/vapi/tools/check_pickup_time",
            json=self._vapi_payload("check_pickup_time", {"pickup_time": "15:00"}),
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]["result"]
        self.assertIn("valid", result)
        self.assertIn("message", result)

    def test_vapi_endpoint_without_tool_calls_is_safe(self):
        response = self.client.post(
            "/vapi/tools/search_menu",
            json={"message": {"type": "tool-calls", "toolCallList": []}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})

    # =========================================================================
    # NON-VAPI ENDPOINTS (UI/Retell)
    # =========================================================================
    def test_tools_search_menu_keeps_price_for_ui(self):
        response = self.client.post("/tools/search_menu", json={"query": "friet speciaal"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertIn("price", data["items"][0])
        self.assertIn("price_formatted", data["items"][0])

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    # =========================================================================
    # FULL ORDER FLOW
    # =========================================================================
    def test_full_order_flow(self):
        """Test complete bestelflow: search -> add -> get_cart -> order"""
        call_id = "flow-test-1"

        # 1. Zoek friet speciaal
        resp = self.client.post(
            "/vapi/tools/search_menu",
            json=self._vapi_payload("search_menu", {"query": "friet speciaal"}, call_id=call_id),
        )
        items = resp.json()["results"][0]["result"]["items"]
        self.assertTrue(len(items) >= 1)

        # 2. Voeg toe aan cart
        resp = self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "friet speciaal", "quantity": 2}, call_id=call_id),
        )
        result = resp.json()["results"][0]["result"]
        self.assertEqual(result["status"], "ok")

        # 3. Voeg frikandel toe
        resp = self.client.post(
            "/vapi/tools/add_to_cart",
            json=self._vapi_payload("add_to_cart", {"item": "frikandel", "quantity": 1}, call_id=call_id),
        )
        result = resp.json()["results"][0]["result"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cart_count"], 2)

        # 4. Check cart
        resp = self.client.post(
            "/vapi/tools/get_cart",
            json=self._vapi_payload("get_cart", call_id=call_id),
        )
        cart = resp.json()["results"][0]["result"]
        self.assertEqual(cart["count"], 2)
        self.assertFalse(cart["empty"])

        # 5. Verzend bestelling
        resp = self.client.post(
            "/vapi/order",
            json=self._vapi_payload("send_order", {
                "customer_name": "Jan",
                "pickup_time": "15:00",
                "items": [
                    {"name": "friet speciaal", "qty": 2},
                    {"name": "frikandel", "qty": 1},
                ],
            }, call_id=call_id),
        )
        result = resp.json()["results"][0]["result"]
        self.assertEqual(result["status"], "ok")
        self.assertIn("order_id", result)


if __name__ == "__main__":
    unittest.main()
