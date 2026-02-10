#!/usr/bin/env python3
"""
Test script voor menu search - test alle veelvoorkomende synoniemen
"""

from menu import search_item

# Test cases: (user input, verwacht aantal resultaten > 0)
test_cases = [
    # Friet synoniemen
    ("patat", True, "friet items"),
    ("patatje", True, "friet items"),
    ("frites", True, "friet items"),
    ("friet", True, "friet items"),
    ("patat met mayo", True, "friet met mayonaise"),

    # Snacks
    ("frikadel", True, "frikandel"),
    ("kroketje", True, "kroket items"),
    ("kroket", True, "kroket items"),
    ("kaassoufflé", True, "kaassoufle"),
    ("souffle", True, "soufle items"),

    # Dranken
    ("cola", True, "coca cola items"),
    ("coke", True, "coca cola items"),
    ("pepsi", True, "coca cola items (fallback)"),
    ("sprite", True, "sprite"),
    ("fanta", True, "fanta"),

    # IJs
    ("ijsje", True, "ijs items"),
    ("ijs", True, "ijs items"),

    # Items die niet bestaan
    ("pizza", False, "niet in menu"),
    ("sushi", False, "niet in menu"),
]

print("=" * 60)
print("MENU SEARCH TEST - Synoniemen & Common Queries")
print("=" * 60)
print()

passed = 0
failed = 0

for query, should_find, description in test_cases:
    results = search_item(query)
    found = len(results) > 0

    status = "✅ PASS" if found == should_find else "❌ FAIL"

    if found == should_find:
        passed += 1
    else:
        failed += 1

    print(f"{status} | '{query}' → {len(results)} items | {description}")

    # Print eerste 2 resultaten als gevonden
    if found and len(results) > 0:
        for item in results[:2]:
            print(f"         - {item['name']} (€{item['price']})")

print()
print("=" * 60)
print(f"RESULTAAT: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("✅ Alle tests geslaagd! Menu search werkt correct.")
else:
    print(f"⚠️  {failed} test(s) gefaald. Check menu.py synoniemen.")
