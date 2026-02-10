# Test script voor order webhook (Windows PowerShell)

$body = @{
    customer_name = "Test Klant"
    phone = "0612345678"
    pickup_time = "18:20"
    items = @(
        @{
            name = "Friet medium"
            qty = 2
        },
        @{
            name = "Frikandel"
            qty = 1
            notes = "Zonder ui"
        }
    )
    extra_notes = "Graag snel klaar"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://127.0.0.1:8000/order" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

