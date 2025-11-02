#!/bin/bash

# Script to enable external access to the Math Viewer

echo "🌐 Enabling External Access to Math Viewer"
echo "=========================================="
echo ""

# Get external IP
echo "📍 Detecting your external IP..."
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s https://api.ipify.org 2>/dev/null || echo "Unable to detect")

if [ "$EXTERNAL_IP" != "Unable to detect" ]; then
    echo "✅ Your external IP: $EXTERNAL_IP"
else
    echo "⚠️  Could not auto-detect external IP"
    echo "   You can find it manually at: https://ifconfig.me"
fi
echo ""

# Check if running on cloud provider
echo "🔍 Checking environment..."
if curl -s -m 2 http://169.254.169.254/latest/meta-data/ &>/dev/null; then
    echo "☁️  AWS EC2 detected"
    echo "⚠️  IMPORTANT: You must also configure Security Group:"
    echo "   1. Go to EC2 Console → Security Groups"
    echo "   2. Add inbound rule: TCP port 7860"
    echo ""
elif curl -s -m 2 -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/ &>/dev/null; then
    echo "☁️  Google Cloud detected"
    echo "⚠️  IMPORTANT: You must also configure firewall:"
    echo "   gcloud compute firewall-rules create allow-gradio --allow tcp:7860"
    echo ""
elif curl -s -m 2 -H Metadata:true "http://169.254.169.254/metadata/instance?api-version=2021-02-01" &>/dev/null; then
    echo "☁️  Azure detected"
    echo "⚠️  IMPORTANT: You must also configure Network Security Group"
    echo ""
else
    echo "💻 Local/on-premise server detected"
fi

# Open firewall
echo "🔓 Configuring firewall to allow port 7860..."
echo ""

if command -v ufw &> /dev/null && sudo ufw status | grep -q "Status: active"; then
    echo "Using UFW..."
    sudo ufw allow 7860/tcp
    if [ $? -eq 0 ]; then
        echo "✅ UFW rule added successfully"
    else
        echo "❌ Failed to add UFW rule (may need sudo)"
    fi
elif command -v firewall-cmd &> /dev/null; then
    echo "Using firewalld..."
    sudo firewall-cmd --permanent --add-port=7860/tcp
    sudo firewall-cmd --reload
    if [ $? -eq 0 ]; then
        echo "✅ Firewalld rule added successfully"
    else
        echo "❌ Failed to add firewalld rule (may need sudo)"
    fi
elif command -v iptables &> /dev/null; then
    echo "Using iptables..."
    sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT
    if [ $? -eq 0 ]; then
        echo "✅ iptables rule added successfully"
        echo "⚠️  Note: iptables rules may not persist after reboot"
    else
        echo "❌ Failed to add iptables rule (may need sudo)"
    fi
else
    echo "⚠️  No firewall detected (or already configured)"
fi

echo ""
echo "🎯 Testing port availability..."
if command -v ss &> /dev/null; then
    PORT_CHECK=$(sudo ss -tlnp | grep :7860)
    if [ -n "$PORT_CHECK" ]; then
        echo "✅ Port 7860 is already in use (app may be running)"
    else
        echo "ℹ️  Port 7860 is available (app not yet started)"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$EXTERNAL_IP" != "Unable to detect" ]; then
    echo "🚀 Access your app from other machines at:"
    echo ""
    echo "   http://$EXTERNAL_IP:7860"
    echo ""
else
    echo "🚀 Access your app from other machines at:"
    echo ""
    echo "   http://<YOUR_EXTERNAL_IP>:7860"
    echo ""
    echo "   Find your external IP at: https://ifconfig.me"
    echo ""
fi

echo "📝 Next steps:"
echo "   1. Launch the app: ./launch.sh (or python app.py)"
echo "   2. Visit the URL above from any device"
echo "   3. If connection fails, check cloud security groups"
echo ""
echo "🔒 Security tips:"
echo "   - Add password: Edit app.py, set auth=(\"user\", \"pass\")"
echo "   - Restrict IPs: sudo ufw allow from <IP> to any port 7860"
echo "   - Use SSH tunnel: ssh -L 7860:localhost:7860 user@server"
echo ""
echo "📚 For more details, see: EXTERNAL_ACCESS.md"
echo ""

