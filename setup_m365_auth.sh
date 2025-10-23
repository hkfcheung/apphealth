#!/bin/bash
# Setup script for Microsoft 365 authentication

echo "=================================================="
echo "Microsoft 365 Status Monitoring - Setup"
echo "=================================================="
echo ""

# Step 1: Install Playwright
echo "Step 1: Installing Playwright..."
echo "Running: pip install playwright"
pip install playwright

if [ $? -ne 0 ]; then
    echo "❌ Failed to install playwright"
    exit 1
fi

echo ""
echo "✓ Playwright Python package installed"
echo ""

# Step 2: Install Chromium browser
echo "Step 2: Installing Chromium browser for Playwright..."
echo "Running: playwright install chromium"
playwright install chromium

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Chromium"
    exit 1
fi

echo ""
echo "✓ Chromium browser installed"
echo ""

# Step 3: Run authentication
echo "=================================================="
echo "Step 3: Running authentication script..."
echo "=================================================="
echo ""
echo "A browser window will open shortly."
echo "Please sign in with your Microsoft 365 admin account."
echo ""
read -p "Press Enter when ready to continue..."

python3 authenticate_microsoft.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ Authentication complete!"
    echo "=================================================="
    echo ""
    echo "Next step: Copy the session file to Docker"
    echo "Run this command:"
    echo ""
    echo "  docker cp microsoft_auth_state.json status-dashboard-backend:/app/"
    echo ""
else
    echo ""
    echo "❌ Authentication failed. Please try running again:"
    echo "  python3 authenticate_microsoft.py"
fi
