#!/bin/bash
# Setup Fly.io secrets from .env file
# This script reads .env and sets secrets in Fly.io

set -e

echo "=========================================="
echo "Fly.io Secrets Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "Error: Fly CLI is not installed"
    echo "Install it with: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo "Not logged in to Fly.io. Please login:"
    fly auth login
fi

# Read .env and set secrets
echo "Reading .env file and setting secrets..."
echo ""

while IFS='=' read -r key value || [ -n "$key" ]; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^#.*$ ]] && continue
    
    # Remove quotes from value if present
    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Skip if value is empty
    [[ -z "$value" ]] && continue
    
    echo "Setting $key..."
    fly secrets set "$key=$value" --app tradenova
    
done < .env

echo ""
echo "=========================================="
echo "✓ Secrets configured"
echo "=========================================="
echo ""
echo "Verify with: fly secrets list --app tradenova"

