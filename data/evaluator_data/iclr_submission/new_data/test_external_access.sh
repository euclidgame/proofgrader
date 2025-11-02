#!/bin/bash

echo "🧪 Testing External Access to Math Viewer"
echo "=========================================="
echo ""

# Get external IP
EXTERNAL_IP=$(curl -s ifconfig.me)
echo "📍 Your external IP: $EXTERNAL_IP"
echo ""

# Test local connection
echo "1️⃣  Testing LOCAL connection (should work)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:7860 | grep -q "200"; then
    echo "   ✅ Local connection: OK"
else
    echo "   ❌ Local connection: FAILED (app not running?)"
    exit 1
fi

# Check if app is running
echo ""
echo "2️⃣  Checking if app is listening on all interfaces..."
LISTEN_CHECK=$(sudo netstat -tlnp | grep :7860 | grep "0.0.0.0")
if [ -n "$LISTEN_CHECK" ]; then
    echo "   ✅ App listening on 0.0.0.0:7860 (correct)"
else
    echo "   ❌ App not listening on 0.0.0.0 (may be localhost only)"
    sudo netstat -tlnp | grep :7860
fi

# Check firewall
echo ""
echo "3️⃣  Checking local firewall..."
IPTABLES_CHECK=$(sudo iptables -L INPUT -n | grep 7860)
if [ -n "$IPTABLES_CHECK" ]; then
    echo "   ✅ iptables allows port 7860"
else
    echo "   ⚠️  No iptables rule found (may be OK if firewall disabled)"
fi

# Instructions for external test
echo ""
echo "4️⃣  Testing EXTERNAL connection..."
echo "   ⚠️  Cannot test external connection from the server itself"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 MANUAL TEST REQUIRED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "From your LOCAL computer (laptop/phone), try:"
echo ""
echo "   http://$EXTERNAL_IP:7860"
echo ""
echo "If it DOESN'T work, the issue is:"
echo "   🔴 AWS Security Group not configured"
echo ""
echo "If it DOES work:"
echo "   🟢 Everything is working!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 How to Configure AWS Security Group:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Go to: https://console.aws.amazon.com/ec2/"
echo "2. Instances → Select your instance"
echo "3. Security tab → Click Security Group link"
echo "4. Edit inbound rules → Add rule:"
echo "   • Type: Custom TCP"
echo "   • Port: 7860"
echo "   • Source: 0.0.0.0/0"
echo "5. Save rules"
echo ""
echo "Then try accessing the URL again!"
echo ""

