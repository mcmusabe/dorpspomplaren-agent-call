#!/bin/bash
# Script om webhook server en Cloudflare Tunnel te starten (geen account nodig!)

echo "=========================================="
echo "Starting Webhook Server + Cloudflare Tunnel"
echo "=========================================="
echo ""

# Check of cloudflared geïnstalleerd is
if ! command -v cloudflared &> /dev/null; then
    echo "⚠️  cloudflared niet gevonden"
    echo "   Installeer met: brew install cloudflared"
    exit 1
fi

# Check of webhook server al draait
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Webhook server draait al op poort 8000"
    echo "   Stop deze eerst of gebruik een andere poort"
    exit 1
fi

# Check of cloudflared al draait
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "⚠️  Cloudflare tunnel draait al"
    echo "   Stop deze eerst"
    exit 1
fi

echo "1️⃣  Starting webhook server in background..."
python3 webhook_order.py > webhook.log 2>&1 &
WEBHOOK_PID=$!
echo "   ✓ Webhook server started (PID: $WEBHOOK_PID)"
sleep 2

echo ""
echo "2️⃣  Starting Cloudflare Tunnel..."
echo "   → Public URL wordt hieronder getoond"
echo "   → Kopieer de HTTPS URL (bijv. https://abc123.trycloudflare.com)"
echo ""
echo "=========================================="
echo ""

# Start cloudflared in foreground zodat gebruiker de URL kan zien
cloudflared tunnel --url http://localhost:8000

# Cleanup bij exit
trap "kill $WEBHOOK_PID 2>/dev/null; pkill -f cloudflared" EXIT

