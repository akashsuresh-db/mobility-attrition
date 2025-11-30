# OBO Authentication Implementation Guide

**Last Updated:** Nov 30, 2025  
**Status:** ✅ **CRITICAL FIX IMPLEMENTED** - Bypassing GenieAgent Wrapper

---

## 🎯 Executive Summary

**Your 3 findings confirmed the root cause:**

1. ✅ **Genie using SP credentials** → `PERMISSION_DENIED` errors
2. ✅ **Supervisor hallucinating** → Fake Sales/Engineering data
3. ✅ **No authorization prompt** → Normal (consent cached from first deployment)

**Solution:** Bypass the `GenieAgent` wrapper entirely and call Genie API directly with OBO credentials.

---

## 🔴 Root Cause Analysis

### The Problem with GenieAgent

```python
# ❌ GenieAgent from databricks-langchain does NOT support OBO
GenieAgent(genie_space_id=..., ...)
    ↓
    Creates its own internal WorkspaceClient
    ↓
    Uses DEFAULT credentials (Service Principal)
    ↓
    ❌ Ignores OBO credentials we tried to provide
```

### Failed Attempts (All Unsuccessful)

| Attempt | Method | Result |
|---------|--------|--------|
| 1 | Pass `workspace_client` parameter | ❌ TypeError (not accepted) |
| 2 | Set `DATABRICKS_TOKEN` environment variable | ❌ Still used SP credentials |
| 3 | Thread-local `Config` with OBO | ❌ Still used SP credentials |

**Conclusion:** `GenieAgent` wrapper is incompatible with OBO authentication.

---

## ✅ SOLUTION: Direct Genie API Calls

### Architecture

```python
# ✅ NEW APPROACH: Direct API calls with explicit OBO WorkspaceClient

1. Create OBO credentials
   obo_creds = ModelServingUserCredentials()

2. Create OBO WorkspaceClient
   workspace_client = WorkspaceClient(credentials_strategy=obo_creds)

3. Call Genie API directly
   conversation = workspace_client.genie.start_conversation(
       space_id=genie_space_id,
       content=user_question
   )
   
   message = workspace_client.genie.get_message(
       space_id=space_id,
       conversation_id=conversation_id,
       message_id=message_id
   )

4. Parse response
   return message.content or attachments
```

### Key Changes Made

#### 1. **New Function: `query_genie_with_obo()`**

Created in Cell 3:

```python
def query_genie_with_obo(workspace_client: WorkspaceClient, space_id: str, question: str) -> str:
    """
    Query Genie Space using OBO credentials via direct API call.
    
    Bypasses GenieAgent wrapper to ensure user credentials are used.
    """
    # Start conversation
    conversation = workspace_client.genie.start_conversation(
        space_id=space_id,
        content=question
    )
    
    # Poll for results (with 60s timeout)
    # Returns response text or error message
```

#### 2. **Updated `create_langgraph_with_nodes()`**

```python
# OLD (used GenieAgent wrapper)
def create_langgraph_with_nodes(llm, externally_served_agents):
    genie_agent = GenieAgent(...)  # ❌ Uses SP credentials
    
# NEW (accepts OBO workspace client)
def create_langgraph_with_nodes(llm, workspace_client, externally_served_agents):
    genie_space_id = agent.space_id  # ✅ Just store config
```

#### 3. **Simplified `genie_node()`**

```python
# OLD (used GenieAgent wrapper)
def genie_node(state):
    response = genie_agent.invoke({"messages": messages})  # ❌
    
# NEW (direct API call)
def genie_node(state):
    user_question = extract_user_question(messages)
    genie_response = query_genie_with_obo(
        workspace_client=workspace_client,  # ✅ OBO credentials
        space_id=genie_space_id,
        question=user_question
    )
```

#### 4. **Fixed Hallucination in `supervisor_summarizer()`**

```python
# Added error detection BEFORE calling LLM
if any(error_keyword in genie_response for error_keyword in 
       ["Error", "PERMISSION_DENIED", "FAILED", "failed with error"]):
    return {"messages": [AIMessage(
        content="I apologize, but I don't have access to the requested data..."
    )]}

# Removed misleading EXAMPLE from prompt
# OLD: Had Sales/Engineering example → LLM used it when Genie failed ❌
# NEW: No examples, explicit instruction to use only provided data ✅
```

#### 5. **Simplified `_create_graph_with_obo()`**

```python
# OLD (complex thread-local config manipulation)
config = Config(credentials_strategy=obo_creds)
threading.current_thread()._databricks_config = config
try:
    graph = create_langgraph_with_nodes(llm, agents)
finally:
    # Restore config...

# NEW (simple and explicit)
workspace_client = WorkspaceClient(credentials_strategy=obo_creds)
graph = create_langgraph_with_nodes(llm, workspace_client, agents)
```

---

## 📋 What You Need to Do Next

### Step 1: Redeploy the Agent

Run the notebook cells in Databricks:

```python
# Cell 11: Log the model
# Cell 12: Register the model
# Cell 13: Deploy to serving endpoint
```

### Step 2: Verify OBO is Working

**Test Query:**
```
"Show me all the BUs which employees are part of"
```

**Expected Results (with your user who has RLS on HR department):**

✅ **SUCCESS:**
- Response contains ONLY HR department data
- NO `PERMISSION_DENIED` errors
- NO hallucinated Sales/Engineering data

❌ **STILL BROKEN:**
- `PERMISSION_DENIED: Failed to fetch tables`
- Shows all departments instead of just HR
- Returns fake data

### Step 3: Manual Cleanup (Optional but Recommended)

**Remove Service Principal from Genie Space:**

1. Go to Databricks workspace
2. Navigate to your Genie Space
3. Settings → Permissions
4. Remove the service principal that was added
5. Ensure only your user account has access

**Why?** The SP should NOT have Genie Space access. Access should only happen via OBO user credentials.

---

## 🔍 Validation Checklist

After redeployment, verify:

- [ ] Querying returns filtered data (only HR department for your user)
- [ ] No `PERMISSION_DENIED` errors in response
- [ ] No hallucinated data (Sales, Engineering, etc.)
- [ ] Response says "I apologize, but I don't have access..." if user truly has no access
- [ ] Different users get different data based on their RLS permissions

---

## 🏗️ Architecture Diagram

```
User Query
    ↓
Model Serving Endpoint (receives query)
    ↓
predict() method
    ↓
_create_graph_with_obo()
    ↓
ModelServingUserCredentials()  ← Captures USER identity from request
    ↓
WorkspaceClient(credentials_strategy=obo_creds)  ← OBO client
    ↓
genie_node()
    ↓
query_genie_with_obo(workspace_client, space_id, question)
    ↓
workspace_client.genie.start_conversation(...)  ← Uses USER credentials
    ↓
Genie Space queries Unity Catalog tables
    ↓
Unity Catalog applies RLS based on USER identity
    ↓
Returns filtered data to user
```

---

## 📊 Before vs After

| Aspect | BEFORE (GenieAgent) | AFTER (Direct API) |
|--------|---------------------|-------------------|
| **Genie Access** | GenieAgent wrapper | Direct API calls |
| **Credentials** | Service Principal (SP) | User (OBO) |
| **RLS Enforcement** | ❌ No (SP sees all) | ✅ Yes (user filtered) |
| **Permission Errors** | ✅ Got errors | ❌ Should work |
| **Hallucination** | ✅ Returned fake data | ❌ Returns error message |
| **Authorization Prompt** | First time only | Cached (normal) |

---

## 🐛 Troubleshooting

### Issue 1: Still Getting Permission Denied

**Possible Causes:**
1. Old model version still deployed
2. Endpoint didn't pick up new version

**Solution:**
```python
# Check deployed version
deployment_info = agents.get_deployment_info(UC_MODEL_NAME)
print(f"Deployed version: {deployment_info.version}")

# Ensure it matches the latest version you registered
```

### Issue 2: Still Seeing All Data (No RLS)

**Possible Causes:**
1. Service principal still has table access
2. RLS policies not configured correctly

**Solution:**
1. Remove SP from Genie Space permissions (UI)
2. Verify RLS policies on tables:
   ```sql
   SHOW ROW FILTERS ON TABLE akash_s_demo.talent.dim_employees;
   ```

### Issue 3: Still Seeing Fake Sales/Engineering Data

**Possible Causes:**
1. Old cached response
2. LLM still using examples from memory

**Solution:**
1. Clear browser cache
2. Ask a completely different question
3. Check logs to see if Genie actually returned an error

---

## 📝 Code Reference

### Key Files Modified

1. **Cell 3** (`%%writefile agent.py`):
   - Added `query_genie_with_obo()` function
   - Modified `create_langgraph_with_nodes()` to accept `workspace_client`
   - Modified `genie_node()` to use direct API
   - Modified `supervisor_summarizer()` to detect errors and prevent hallucination
   - Modified `_create_graph_with_obo()` to create and pass OBO workspace client

2. **Cell 5** (Visualization):
   - Updated to pass temporary workspace client for graph visualization

3. **Cell 11** (MLflow Logging):
   - Resources: Only infrastructure (endpoint, warehouse)
   - `DatabricksGenieSpace` and `DatabricksTable` removed from `SystemAuthPolicy`
   - UserAuthPolicy includes `dashboards.genie` scope

---

## 🎉 Expected Outcome

After redeployment and testing:

**User Query:** "Show me all the BUs which employees are part of"

**Response (with RLS on HR department):**

```
Based on the available data, employees are currently assigned to the HR department.
This represents the accessible organizational structure for your view.

| Department | Employee Count |
|------------|----------------|
| HR         | 45             |
```

**NOT:**
- ❌ Permission denied errors
- ❌ Sales, Engineering, or other departments
- ❌ Fake hallucinated data

---

## 📞 Next Steps

1. **Redeploy** the agent using the notebook
2. **Test** with your user account (should have HR-only access)
3. **Report back** what you see:
   - If you see only HR data → ✅ **SUCCESS!**
   - If you still see permission errors → Need to debug further
   - If you see all departments → Check RLS policies and SP permissions

---

## 🏆 Why This Will Work

1. **Direct API Control**: We control exactly which credentials are used
2. **Explicit OBO Client**: `WorkspaceClient(credentials_strategy=obo_creds)` is explicit
3. **No Wrapper Interference**: Bypassing GenieAgent removes the black box
4. **Error Handling**: Supervisor detects and reports errors instead of hallucinating
5. **Clean Prompts**: No misleading examples in prompts

**This is the correct architectural pattern for OBO + Genie + RLS.**

---

**Commit:** `e8f1d62` (pushed to `main`)  
**Previous Attempts:** `0f1d338` (thread-local config - didn't work)
