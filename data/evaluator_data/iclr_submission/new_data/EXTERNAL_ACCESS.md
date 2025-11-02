# 🌐 External Access Guide - Access from Other Machines

## Quick Steps to Enable External Access

### 1. Find Your External IP

```bash
# Get your machine's external IP
curl ifconfig.me

# Or
curl https://api.ipify.org
```

### 2. Open Firewall Port 7860

#### On Ubuntu/Debian (using UFW):
```bash
# Check if UFW is active
sudo ufw status

# Allow port 7860
sudo ufw allow 7860/tcp

# Verify the rule was added
sudo ufw status
```

#### On RHEL/CentOS/Fedora (using firewalld):
```bash
# Allow port 7860
sudo firewall-cmd --permanent --add-port=7860/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

#### On systems with iptables:
```bash
sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT
sudo iptables-save
```

### 3. Configure Cloud Provider Security (if applicable)

#### AWS EC2:
1. Go to EC2 Console → Security Groups
2. Select your instance's security group
3. Click "Edit inbound rules"
4. Add rule:
   - Type: Custom TCP
   - Port: 7860
   - Source: 0.0.0.0/0 (or specific IPs for security)
   - Description: Gradio Math Viewer

#### Google Cloud Platform:
```bash
# Create firewall rule
gcloud compute firewall-rules create allow-gradio \
    --allow tcp:7860 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow Gradio app access"
```

Or via Console:
1. VPC Network → Firewall
2. Create Firewall Rule
3. Target: All instances
4. Source IP ranges: 0.0.0.0/0
5. Protocols and ports: tcp:7860

#### Azure:
1. Virtual Machines → Networking
2. Add inbound port rule
3. Destination port ranges: 7860
4. Protocol: TCP
5. Action: Allow

### 4. Launch the App

```bash
cd /home/ubuntu/wenjie-cal/ProofGym/evaluator_design/data/iclr_submission/new_data
python app.py
```

### 5. Access from Another Machine

From any other computer on the network:
```
http://<YOUR_EXTERNAL_IP>:7860
```

Example:
```
http://34.123.45.67:7860
```

---

## 🔒 Security Considerations

### Option A: Restrict to Specific IPs (Recommended)

Instead of allowing `0.0.0.0/0`, allow only specific IPs:

```bash
# UFW example - allow only from specific IP
sudo ufw allow from 192.168.1.100 to any port 7860
```

### Option B: Add Password Protection

Edit `app.py` and add authentication:

```python
app.launch(
    server_name="0.0.0.0",
    server_port=7860,
    share=False,
    show_error=True,
    auth=("admin", "your_secure_password_here")  # Add this line
)
```

### Option C: Use SSH Tunnel (Most Secure)

No firewall changes needed! From the remote machine:

```bash
# Create SSH tunnel
ssh -L 7860:localhost:7860 ubuntu@<YOUR_EXTERNAL_IP>

# Then access on remote machine at:
# http://localhost:7860
```

---

## 🛠️ Troubleshooting

### Test if port is accessible

From another machine:
```bash
# Test if port 7860 is open
nc -zv <YOUR_EXTERNAL_IP> 7860

# Or use telnet
telnet <YOUR_EXTERNAL_IP> 7860
```

### Check what's listening on port 7860

On the server:
```bash
# See what's using port 7860
sudo netstat -tlnp | grep 7860

# Or with ss
sudo ss -tlnp | grep 7860

# Or with lsof
sudo lsof -i :7860
```

### Verify firewall rules

```bash
# UFW
sudo ufw status numbered

# iptables
sudo iptables -L -n -v | grep 7860

# firewalld
sudo firewall-cmd --list-all
```

### Common Issues

**Issue: Connection refused**
- App not running: Check with `ps aux | grep python`
- Wrong IP: Verify with `curl ifconfig.me`
- Firewall blocking: Check firewall rules

**Issue: Connection timeout**
- Cloud security group not configured
- ISP blocking the port
- Server firewall blocking

**Issue: Can't access from work/school**
- Corporate firewall may block non-standard ports
- Solution: Use SSH tunnel or deploy on standard ports (80/443)

---

## 🚀 Production Deployment Tips

### Use a Reverse Proxy (Recommended)

Install nginx:
```bash
sudo apt install nginx -y
```

Configure nginx (`/etc/nginx/sites-available/math-viewer`):
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your IP

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and start:
```bash
sudo ln -s /etc/nginx/sites-available/math-viewer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

Now access via: `http://<YOUR_IP>` (port 80, no need to specify)

### Add SSL/HTTPS (Free with Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

Access via: `https://your-domain.com`

### Run as a System Service

Create `/etc/systemd/system/math-viewer.service`:
```ini
[Unit]
Description=Mathematical Olympiad Solution Viewer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/wenjie-cal/ProofGym/evaluator_design/data/iclr_submission/new_data
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable math-viewer
sudo systemctl start math-viewer
sudo systemctl status math-viewer
```

---

## 📊 Quick Reference

| Access Method | Security | Ease | Best For |
|--------------|----------|------|----------|
| **Direct IP:7860** | Low | Easy | Testing |
| **IP:7860 + Auth** | Medium | Easy | Small teams |
| **SSH Tunnel** | High | Medium | Individual use |
| **Nginx + SSL** | High | Medium | Production |
| **Hugging Face** | High | Very Easy | Public sharing |

---

## 🎯 Quick Setup Script

Save as `enable_external_access.sh`:

```bash
#!/bin/bash

echo "🌐 Enabling External Access to Math Viewer"
echo "=========================================="

# Get external IP
EXTERNAL_IP=$(curl -s ifconfig.me)
echo "📍 Your external IP: $EXTERNAL_IP"

# Open firewall
echo "🔓 Opening port 7860..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 7860/tcp
    echo "✅ UFW rule added"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=7860/tcp
    sudo firewall-cmd --reload
    echo "✅ Firewalld rule added"
else
    sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT
    echo "✅ iptables rule added"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Access your app from other machines at:"
echo "   http://$EXTERNAL_IP:7860"
echo ""
echo "⚠️  Note: If on AWS/GCP/Azure, you also need to configure"
echo "   security groups/firewall rules in your cloud console."
```

Run it:
```bash
chmod +x enable_external_access.sh
./enable_external_access.sh
```

---

**Need help?** Check the troubleshooting section or see README_DEPLOYMENT.md for more options.

