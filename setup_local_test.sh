#!/bin/bash

echo "============================================================================"
echo "🔧 SETUP FOR LOCAL AGENT TESTING"
echo "============================================================================"

# Check if running on macOS/Linux
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "✓ Platform: $OSTYPE"
else
    echo "⚠️  Warning: This script is designed for macOS/Linux"
fi

echo ""
echo "📦 Step 1: Installing Python dependencies..."
echo "--------------------------------------------"

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "❌ pip not found. Please install Python and pip first."
    exit 1
fi

# Install dependencies
pip install -q langgraph-supervisor==0.0.30 mlflow[databricks] databricks-langchain databricks-agents

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🔑 Step 2: Configure Databricks Authentication"
echo "--------------------------------------------"
echo ""
echo "You need to set the following environment variables:"
echo ""
echo "1. DATABRICKS_HOST - Your Databricks workspace URL"
echo "   Example: https://adb-984752964297111.11.azuredatabricks.net"
echo ""
echo "2. DATABRICKS_TOKEN - Your Databricks personal access token"
echo "   Get it from: Databricks → Settings → Developer → Access Tokens"
echo ""
echo "Enter your Databricks workspace URL:"
read -p "DATABRICKS_HOST: " DB_HOST

echo ""
echo "Enter your Databricks token:"
read -sp "DATABRICKS_TOKEN: " DB_TOKEN
echo ""

# Validate inputs
if [ -z "$DB_HOST" ] || [ -z "$DB_TOKEN" ]; then
    echo ""
    echo "❌ Both DATABRICKS_HOST and DATABRICKS_TOKEN are required!"
    exit 1
fi

# Export for current session
export DATABRICKS_HOST="$DB_HOST"
export DATABRICKS_TOKEN="$DB_TOKEN"

echo ""
echo "✓ Environment variables set for current session"
echo ""
echo "To make these permanent, add to your ~/.zshrc or ~/.bashrc:"
echo ""
echo "export DATABRICKS_HOST='$DB_HOST'"
echo "export DATABRICKS_TOKEN='$DB_TOKEN'"
echo ""

echo "============================================================================"
echo "✅ SETUP COMPLETE"
echo "============================================================================"
echo ""
echo "Now run the test script:"
echo "   python test_agent_local.py"
echo ""

