#!/bin/bash
# Deployment script for Voice CRM
# Usage: ./deploy.sh

set -e

PROJECT_DIR="/opt/voice_crm"

echo "Starting deployment..."
    cd $PROJECT_DIR
    
    # Pull latest code
    git pull origin main || git pull origin master
    
    # Backend
echo "Updating backend..."
    cd backend
    source venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py collectstatic --noinput
    deactivate
    
    # Frontend
echo "Building frontend..."
    cd ../frontend
    npm install
    npm run build
    
    # Restart service
echo "Restarting service..."
    sudo systemctl restart voice_crm
    
    echo "Deployment complete!"
    sudo systemctl status voice_crm
