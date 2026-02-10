#!/bin/bash
# Script om webhook server en ngrok te starten

echo "=========================================="
echo "Starting Webhook Server + ngrok"
echo "=========================================="
echo ""

# Check of webhook server al draait
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Webhook server draait al op poort 8000"
    echo "   Stop deze eerst of gebruik een andere poort"
    exit 1
fi

# Check of ngrok al draait
if pgrep -f "ngrok http" > /dev/null; then
    echo "⚠️  ngrok draait al"
    echo "   Stop deze eerst"
    exit 1
fi

echo "1️⃣  Starting webhook server in background..."
python3 webhook_order.py > webhook.log 2>&1 &
WEBHOOK_PID=$!
echo "   ✓ Webhook server started (PID: $WEBHOOK_PID)"
sleep 2

echo ""
echo "2️⃣  Starting ngrok..."
echo "   → Public URL wordt hieronder getoond"
echo "   → Kopieer de HTTPS URL (bijv. https://abc123.ngrok.io)"
echo ""
echo "=========================================="
echo ""

# Start ngrok in foreground zodat gebruiker de URL kan zien
ngrok http 8000

# Cleanup bij exit
trap "kill $WEBHOOK_PID 2>/dev/null; pkill -f ngrok" EXIT

