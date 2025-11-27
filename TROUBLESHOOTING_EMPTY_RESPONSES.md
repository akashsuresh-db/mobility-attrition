# Troubleshooting Empty Agent Responses

## Issue Description
The app shows only "**Talent Genie**" header but no actual data when asking questions like "Number of employees in each BU".

## Root Cause Analysis

Based on the agent architecture, the flow should be:
```
User Question → Router → Genie → Summarizer → Final Response
```

The fact that you're seeing "**Talent Genie**" suggests:
1. ✅ The router correctly identified your question as talent-related
2. ✅ The Genie agent is being invoked
3. ❌ **The Genie is not returning data OR the data is being lost in processing**

## Possible Causes

### 1. **Genie Space Permissions** (Most Likely)
The agent endpoint's service principal may not have access to query the Genie Space.

**How to Check:**
1. Go to your Databricks workspace
2. Navigate to **Genie Spaces**
3. Find space ID: `01f0c9f705201d14b364f5daf28bb639`
4. Check the **Permissions** tab
5. Ensure the agent's service principal has **"Can Query"** permission

**How to Fix:**
```bash
# Option 1: Grant via UI
1. Open Genie Space settings
2. Go to Permissions
3. Add the service principal with "Can Query" role

# Option 2: Grant via CLI (if you have Databricks CLI)
databricks permissions set genie-space 01f0c9f705201d14b364f5daf28bb639 \
  --principal <SERVICE_PRINCIPAL_ID> \
  --permission CAN_QUERY
```

### 2. **Genie Space Has No Data**
The Genie Space might not be properly configured with data sources.

**How to Check:**
1. Go to the Genie Space in Databricks UI
2. Test the same question directly in the Genie UI: "Number of employees in each BU"
3. If Genie returns empty results there, the issue is with Genie configuration, not the app

**How to Fix:**
- Ensure the Genie Space has access to the required tables
- Check that the data sources are properly indexed
- Verify SQL queries work in the Genie Space

### 3. **Agent Endpoint Not Rebuilt**
After making changes to the agent configuration, the endpoint needs to be rebuilt.

**How to Check:**
- Look at the deployment timestamp of the agent endpoint
- Compare with when you last updated the agent code

**How to Fix:**
1. Open the notebook: `langgraph-agent-with-summary.ipynb`
2. Re-run the deployment cells (starting from "Register and Deploy")
3. Wait for the endpoint to redeploy

### 4. **LLM Endpoint Issues**
The supervisor uses `databricks-meta-llama-3-1-8b-instruct` endpoint for summarization.

**How to Check:**
1. Go to **Serving Endpoints** in Databricks
2. Find endpoint: `databricks-meta-llama-3-1-8b-instruct`
3. Check if it's running and healthy

**How to Fix:**
- If endpoint is down, restart it
- If it doesn't exist, update the `LLM_ENDPOINT_NAME` in the notebook

## Debugging Steps with New Logging

I've added extensive debugging to `app.py`. After redeploying, check the app logs:

### Where to Find Logs:
1. Go to your Databricks workspace
2. Navigate to **Apps**
3. Find your app: `mobility-attrition`
4. Click on **Logs** tab

### What to Look For:

```python
# Expected log output for a successful query:
Calling agent with history: 1 messages
Response object type: <class 'ResponsesAgentResponse'>
Response output: [...]
Output type: <type>, Output: {...}
Content type: <type>, Content: {...}
Extracted text: '<full response text>'
Final response text length: 450
Final response text: '...'
```

### Interpreting the Logs:

| Log Message | Meaning |
|------------|---------|
| `Extracted text: ''` | Genie returned empty response |
| `Final response text length: 0` | No data was extracted |
| `Response output: []` | Agent didn't produce any output |
| `Extracted text: '**Talent Genie**'` | Only header, no content |

## Quick Fix Test

### Test Locally First:
```bash
# Set your token
export DATABRICKS_TOKEN='dapi...'
export DATABRICKS_HOST='https://adb-984752964297111.11.azuredatabricks.net'

# Run test script
python test_agent_local.py
```

This will show you exactly what the agent is returning without the app layer.

## Expected Behavior

When working correctly, you should see:

**User:** "Number of employees in each BU"

**Assistant:**
```
**Talent Genie**

Based on the employee data, we have 5 business units with varying headcounts. 
The largest is Corporate (500 employees) while the smallest is Research (50 employees).

| Business Unit | Employee Count |
|--------------|---------------|
| Corporate    | 500           |
| Sales        | 350           |
| Engineering  | 250           |
| Marketing    | 150           |
| Research     | 50            |
```

## Next Steps

1. **Check Genie Space Permissions** (Most Critical)
   - Service principal needs "Can Query" access

2. **Test Genie Space Directly**
   - Verify it returns data in the Genie UI

3. **Review App Logs**
   - Look for the debug messages I added
   - Share the logs if you need more help

4. **Rebuild Agent Endpoint**
   - If permissions were changed, rebuild the endpoint

5. **Test Locally**
   - Run `test_agent_local.py` to isolate the issue

## Still Having Issues?

If none of the above helps, please provide:
1. Screenshot of the app logs (with debug output)
2. Screenshot of Genie Space permissions
3. Result of testing the same question directly in Genie UI
4. Output from `test_agent_local.py`

---

**Updated:** 2025-11-27  
**Agent Model:** `agents_akash_s_demo-talent-mobility_attrition`  
**Genie Space:** `01f0c9f705201d14b364f5daf28bb639`

