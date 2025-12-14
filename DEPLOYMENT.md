# VPS Deployment Guide

Deploy the Voice CRM application to a VPS.

## Prerequisites

- Ubuntu 20.04+ or Debian 11+ VPS
- Root or sudo access
- Domain name (optional but recommended for SSL)

## Architecture

- **Backend**: Django + Channels (ASGI) running on uvicorn
- **Frontend**: React + Vite (static files served by Nginx)
- **WebSocket**: Real-time voice agent communication

## Deployment Steps

### 1. Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.10 python3.10-venv python3-pip nginx git

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. Clone Repository

```bash
git clone <your-repo-url> /opt/voice_crm
cd /opt/voice_crm
```

### 3. Setup Backend

```bash
cd /opt/voice_crm/backend

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp env.example .env
nano .env  # Edit with your values
```

Set these in `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
CLOSE_API_KEY=your_close_api_key_here
DEBUG=False
SECRET_KEY=generate_a_secure_random_key_here
ALLOWED_HOSTS=your-domain.com,your-server-ip
```

Generate a secure SECRET_KEY:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Run Migrations

```bash
cd /opt/voice_crm/backend
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Setup Frontend

```bash
cd /opt/voice_crm/frontend
npm install
npm run build
```

### 6. Setup Systemd Service

```bash
sudo cp /opt/voice_crm/deployment/voice_crm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable voice_crm
sudo systemctl start voice_crm
```

### 7. Configure Nginx

```bash
sudo cp /opt/voice_crm/deployment/nginx-site.conf /etc/nginx/sites-available/voice_crm
sudo nano /etc/nginx/sites-available/voice_crm  # Update domain name
sudo ln -s /etc/nginx/sites-available/voice_crm /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Setup Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 9. Setup SSL (Optional, requires domain)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Updating the Application

```bash
cd /opt/voice_crm
./deployment/deploy.sh
```

Or manually:
```bash
cd /opt/voice_crm
git pull
cd backend && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
cd ../frontend && npm install && npm run build
sudo systemctl restart voice_crm
```

## Checking Status

```bash
# Service status
sudo systemctl status voice_crm

# Logs
sudo journalctl -u voice_crm -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

### WebSocket Connection Issues
- Check nginx config has WebSocket proxy settings
- Verify firewall allows ports 80/443
- Check `ALLOWED_HOSTS` in `.env`

### Static Files Not Loading
```bash
cd /opt/voice_crm/backend
source venv/bin/activate
python manage.py collectstatic --noinput
```

### 502 Bad Gateway
- Check if backend is running: `sudo systemctl status voice_crm`
- Check backend logs: `sudo journalctl -u voice_crm -f`

## Security Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Setup SSL/HTTPS
- [ ] Configure firewall
- [ ] Keep system updated
