#!/bin/bash
# Deploy TradeNova to Fly.io
# This script automates the deployment process

set -e

echo "=========================================="
echo "TradeNova Fly.io Deployment Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}Error: Fly CLI is not installed${NC}"
    echo "Install it with: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓ Fly CLI found${NC}"

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Fly.io. Please login:${NC}"
    fly auth login
fi

echo -e "${GREEN}✓ Logged in to Fly.io${NC}"

# Check if app exists
APP_NAME="tradenova"
if ! fly apps list | grep -q "$APP_NAME"; then
    echo -e "${YELLOW}App '$APP_NAME' not found. Creating...${NC}"
    fly apps create "$APP_NAME"
    echo -e "${GREEN}✓ App created${NC}"
else
    echo -e "${GREEN}✓ App '$APP_NAME' exists${NC}"
fi

# Check if secrets are set
echo ""
echo "Checking environment variables..."
echo ""

REQUIRED_SECRETS=(
    "ALPACA_API_KEY"
    "ALPACA_SECRET_KEY"
    "ALPACA_BASE_URL"
)

MISSING_SECRETS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! fly secrets list | grep -q "$secret"; then
        MISSING_SECRETS+=("$secret")
    fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing required secrets:${NC}"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - $secret"
    done
    echo ""
    echo "Please set them with:"
    echo "  fly secrets set ALPACA_API_KEY=your_key"
    echo "  fly secrets set ALPACA_SECRET_KEY=your_secret"
    echo "  fly secrets set ALPACA_BASE_URL=https://paper-api.alpaca.markets"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ All required secrets are set${NC}"
fi

# Deploy
echo ""
echo "Deploying to Fly.io..."
echo ""

fly deploy

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ Deployment Successful!"
    echo "==========================================${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Check status: fly status"
    echo "2. View logs: fly logs --app $APP_NAME"
    echo "3. Access dashboard: https://$APP_NAME.fly.dev"
    echo ""
    echo "Trading system will automatically start at market open (9:30 AM ET)"
    echo ""
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ Deployment Failed"
    echo "==========================================${NC}"
    echo ""
    echo "Check the error messages above and try again."
    exit 1
fi

