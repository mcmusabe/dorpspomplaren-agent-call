#!/bin/bash
# Test script voor order webhook (Unix/Mac)

curl -X POST http://127.0.0.1:8000/order \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Klant",
    "phone": "0612345678",
    "pickup_time": "18:20",
    "items": [
      {
        "name": "Friet medium",
        "qty": 2
      },
      {
        "name": "Frikandel",
        "qty": 1,
        "notes": "Zonder ui"
      }
    ],
    "extra_notes": "Graag snel klaar"
  }'

