#!/bin/bash
# cat_fetches Environment Setup Script for AWS EC2
# Run this script to set up the production environment on a fresh EC2 instance

set -e

echo "🚀 cat_fetches AWS EC2 Environment Setup"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing required packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    supervisor \
    htop \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    wget \
    unzip

# Verify installations
print_status "Verifying installations..."
python3 --version || { print_error "Python3 installation failed"; exit 1; }
pip3 --version || { print_error "pip3 installation failed"; exit 1; }
git --version || { print_error "git installation failed"; exit 1; }
nginx -version || { print_error "nginx installation failed"; exit 1; }

print_status "Basic system setup completed!"

# Clone repository if not exists
if [ ! -d "/home/ubuntu/cat_fetches" ]; then
    print_status "Cloning cat_fetches repository..."
    cd /home/ubuntu
    # Replace with actual repository URL
    print_warning "Please clone your repository manually:"
    print_warning "git clone https://github.com/your-org/cat_fetches.git"
    print_warning "Then run this script again"
    exit 0
else
    print_status "Repository found, continuing setup..."
fi

cd /home/ubuntu/cat_fetches

# Create virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test imports
print_status "Testing application imports..."
python test_app_imports.py || { print_error "Import test failed"; exit 1; }

# Create systemd directories
print_status "Setting up systemd service..."
sudo mkdir -p /etc/cat-fetches

# Create environment file template if it doesn't exist
if [ ! -f "/etc/cat-fetches/environment" ]; then
    print_status "Creating environment file template..."
    sudo tee /etc/cat-fetches/environment > /dev/null <<EOF
# AI Service Configuration
GEMINI_API_KEY=your_production_gemini_api_key

# News Service Configuration
NEWS_API_KEY=your_production_newsapi_key

# Email Service Configuration (Gmail recommended)
SMTP_EMAIL=your-production-email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Application Environment
APP_ENV=production

# Security settings
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
EOF

    sudo chown root:root /etc/cat-fetches/environment
    sudo chmod 600 /etc/cat-fetches/environment

    print_warning "Environment file created at /etc/cat-fetches/environment"
    print_warning "Please edit this file with your production API keys before starting the service"
fi

# Install systemd service
print_status "Installing systemd service..."
sudo cp deployment/cat-fetches.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cat-fetches.service

# Configure basic Nginx setup
print_status "Setting up Nginx configuration..."
if [ ! -f "/etc/nginx/sites-available/cat-fetches" ]; then
    sudo tee /etc/nginx/sites-available/cat-fetches > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/cat-fetches /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl restart nginx
fi

# Configure UFW firewall
print_status "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8501

# Create update script
print_status "Creating update script..."
tee /home/ubuntu/update-catfetches.sh > /dev/null <<'EOF'
#!/bin/bash
set -e

echo "🔄 Updating cat_fetches application..."

cd /home/ubuntu/cat_fetches

# Stop service
sudo systemctl stop cat-fetches.service

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Test imports
python test_app_imports.py

# Restart service
sudo systemctl start cat-fetches.service

# Verify service is running
sleep 5
sudo systemctl status cat-fetches.service

echo "✅ Update completed successfully!"
EOF

chmod +x /home/ubuntu/update-catfetches.sh

print_status "Environment setup completed!"
echo
echo "Next steps:"
echo "1. Edit /etc/cat-fetches/environment with your production API keys"
echo "2. Start the service: sudo systemctl start cat-fetches.service"
echo "3. Check status: sudo systemctl status cat-fetches.service"
echo "4. View logs: sudo journalctl -u cat-fetches.service -f"
echo "5. Access your app at: http://$(curl -s ifconfig.me):8501"
echo
print_status "Setup completed successfully! 🎉"