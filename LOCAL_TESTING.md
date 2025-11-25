# Local Testing Guide

Test your multi-agent system locally before deploying to Databricks.

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
./setup_local_test.sh
```

This will:
1. Install required dependencies
2. Prompt for your Databricks credentials
3. Set up environment variables

Then test:
```bash
python test_agent_local.py
```

### Option 2: Manual Setup

1. **Install dependencies:**
   ```bash
   pip install langgraph-supervisor==0.0.30 mlflow[databricks] databricks-langchain databricks-agents
   ```

2. **Set environment variables:**
   ```bash
   export DATABRICKS_HOST='https://adb-984752964297111.11.azuredatabricks.net'
   export DATABRICKS_TOKEN='dapi...'  # Your personal access token
   ```

3. **Run the test:**
   ```bash
   python test_agent_local.py
   ```

## What Gets Tested

The local test will:
- ✅ Verify Databricks authentication
- ✅ Initialize LLM endpoint (Llama 3.1-8B)
- ✅ Connect to Genie Space
- ✅ Create supervisor with enhanced summarization prompt
- ✅ Run test queries
- ✅ Display both summary and table output

## Expected Output

```
🧪 TESTING MULTI-AGENT SYSTEM LOCALLY
================================================================================

✓ Databricks Host: https://adb-...
✓ Token: ******************** (hidden)

📦 Importing required libraries...
✓ All libraries imported successfully

⚙️  Configuration:
   • LLM Endpoint: databricks-meta-llama-3-1-8b-instruct
   • Genie Space: 01f0c9f705201d14b364f5daf28bb639

🔧 Initializing clients...
✓ Databricks clients initialized

🧠 Creating Genie agent...
✓ Genie agent created

📝 Creating supervisor with enhanced summarization prompt...
✓ Supervisor created with enhanced prompt

================================================================================
🚀 TESTING AGENT
================================================================================

📊 Test 1: What is the total attrition count?
--------------------------------------------------------------------------------

🔄 Agent response:

============================================================
➜ Agent: talent_genie
============================================================

[Table with data from Genie]

============================================================
➜ Agent: supervisor
============================================================

[Natural language summary from Llama 3.1]

✅ Test completed successfully
```

## Troubleshooting

### "Missing required library" error
```bash
pip install -r requirements.txt
pip install langgraph-supervisor==0.0.30 databricks-langchain
```

### "Failed to initialize clients" error
- Check your DATABRICKS_HOST URL is correct
- Verify your DATABRICKS_TOKEN is valid and not expired
- Ensure you have network connectivity

### "Failed to create Genie agent" error
- Verify the Genie Space ID is correct
- Check your token has access to the Genie Space
- Ensure the space is in a "Ready" state

### Permission errors
- Your token needs "Can Query" permission on:
  - The LLM serving endpoint
  - The Genie Space
  - The SQL Warehouse used by Genie

## What's Next?

After successful local testing:

1. **Open the notebook:** `langgraph-agent-with-summary.ipynb`
2. **Run all cells** to:
   - Log to MLflow
   - Register in Unity Catalog
   - Deploy to serving endpoint
3. **Update your Dash app** to use the new endpoint

## Tips

- Test with multiple questions to verify different response types
- Check that both summary and table are returned
- Verify the summary is insightful and uses specific numbers
- Ensure tables are properly formatted

