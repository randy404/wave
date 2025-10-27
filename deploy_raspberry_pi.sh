#!/bin/bash
# 🚀 Script Deployment Otomatis Dashboard Ombak untuk Raspberry Pi 5
# Domain: https://wave-monitoring.lppm-upiyptk.site/

set -e  # Exit on any error

echo "🚀 Starting Wave Monitoring Dashboard Deployment..."
echo "📋 Target Domain: https://wave-monitoring.lppm-upiyptk.site/"
echo "🖥️  Target Host: Raspberry Pi 5"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as regular user with sudo privileges."
   exit 1
fi

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is designed for Raspberry Pi. Continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_status "Step 2: Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git ufw fail2ban

print_status "Step 3: Installing Python packages..."
pip3 install streamlit opencv-python numpy pandas plotly reportlab requests python-dotenv

print_status "Step 4: Creating project directory..."
sudo mkdir -p /opt/wave-monitoring
sudo chown $USER:$USER /opt/wave-monitoring
cd /opt/wave-monitoring

print_status "Step 5: Setting up Nginx configuration..."
sudo tee /etc/nginx/sites-available/wave-monitoring > /dev/null <<EOF
server {
    listen 80;
    server_name wave-monitoring.lppm-upiyptk.site;

    # Redirect HTTP ke HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name wave-monitoring.lppm-upiyptk.site;

    # SSL Configuration (akan diisi oleh Certbot)
    ssl_certificate /etc/letsencrypt/live/wave-monitoring.lppm-upiyptk.site/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wave-monitoring.lppm-upiyptk.site/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy ke Streamlit
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)\$ {
        proxy_pass http://127.0.0.1:8501;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

print_status "Step 6: Enabling Nginx site..."
sudo ln -sf /etc/nginx/sites-available/wave-monitoring /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

print_status "Step 7: Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

print_status "Step 8: Setting up SSL certificate..."
print_warning "Make sure DNS record 'wave-monitoring.lppm-upiyptk.site' points to this server's IP address!"
print_warning "Press Enter when DNS is configured, or Ctrl+C to exit..."
read -r

sudo certbot --nginx -d wave-monitoring.lppm-upiyptk.site --non-interactive --agree-tos --email admin@lppm-upiyptk.site

print_status "Step 9: Setting up auto-renewal..."
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

print_status "Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/wave-monitoring.service > /dev/null <<EOF
[Unit]
Description=Wave Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/wave-monitoring
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/bin/python3 -m streamlit run ombak_dashboard_streamlit.py --server.headless true --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Step 11: Creating environment template..."
tee .env.template > /dev/null <<EOF
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
WHATSAPP_TO=whatsapp:+6281234567890

# SMS Configuration
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid_here
TWILIO_SMS_FROM=+12025550123
SMS_TO=+6281234567890

# RTSP Configuration
RTSP_URL=rtsp://user:pass@192.168.1.100:8554/Streaming/Channels/101

# Camera Location
CAMERA_LOCATION=Pantai Kuta, Bali

# CSV Path
OMBAK_CSV_PATH=/opt/wave-monitoring/deteksi_ombak.csv
EOF

print_status "Step 12: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable wave-monitoring.service

print_status "Step 13: Setting up fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

print_success "🎉 Deployment completed successfully!"
echo ""
print_status "📋 Next steps:"
echo "1. Copy your project files to /opt/wave-monitoring/"
echo "2. Copy .env.template to .env and configure your settings"
echo "3. Start the service: sudo systemctl start wave-monitoring.service"
echo "4. Check status: sudo systemctl status wave-monitoring.service"
echo "5. Access dashboard: https://wave-monitoring.lppm-upiyptk.site/"
echo ""
print_status "🔧 Useful commands:"
echo "- Check service logs: sudo journalctl -u wave-monitoring.service -f"
echo "- Restart service: sudo systemctl restart wave-monitoring.service"
echo "- Check Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "- Check SSL status: sudo certbot certificates"
echo ""
print_success "🚀 Your Wave Monitoring Dashboard is ready for deployment!"
