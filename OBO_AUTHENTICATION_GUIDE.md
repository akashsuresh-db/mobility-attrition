# OBO Authentication Implementation Guide

**Last Updated:** Nov 30, 2025  
**Status:** ✅ **USING DOCUMENTED APPROACH** - GenieAgent with `client=` Parameter

---

## 🎯 Executive Summary

**The documentation you shared revealed the KEY parameter we missed:**

```python
genie_agent = GenieAgent(
    genie_space_id="<space_id>",
    genie_agent_name="Genie",
    client=user_client  # ← THIS is the parameter we never tried!
)
```

**Solution:** Use the official `GenieAgent` wrapper with the documented `client=` parameter instead of direct API calls.

---

## 🔍 Root Cause: We Tried the Wrong Parameter Names

### What We Tried (All Wrong):

| Attempt | Parameter Name | Result |
|---------|---------------|--------|
| 1 | `workspace_client=user_client` | ❌ TypeError (not accepted) |
| 2 | Environment variable `DATABRICKS_TOKEN` | ❌ Still used SP credentials |
| 3 | Thread-local `Config` | ❌ Still used SP credentials |
| 4 | Direct API calls (bypassing GenieAgent) | ⚠️ Works but against LangGraph pattern |

### What the Documentation Says:

```python
# ✅ CORRECT (from official docs)
client=user_client
```

**We never tried `client=` !** We tried `workspace_client=`, which doesn't exist!

---

## ✅ CORRECT IMPLEMENTATION

### Architecture (Per Documentation)

```python
# 1. Create OBO credentials (inside predict, not __init__)
obo_creds = ModelServingUserCredentials()

# 2. Create OBO WorkspaceClient
user_client = WorkspaceClient(credentials_strategy=obo_creds)

# 3. Pass to GenieAgent via client= parameter
genie_agent = GenieAgent(
    genie_space_id="<space_id>",
    genie_agent_name="Genie",
    client=user_client  # ← CRITICAL!
)

# 4. Use genie_agent in LangGraph normally
response = genie_agent.invoke({"messages": messages})
```

### Key Requirements Checklist

| Requirement | Our Implementation | Status |
|-------------|-------------------|---------|
| ✅ Instantiate in `predict()` | Yes, in `_create_graph_with_obo()` | ✅ PASS |
| ✅ Use `client=` parameter | Yes, `client=workspace_client` | ✅ PASS |
| ✅ Declare `dashboards.genie` scope | Yes, in `UserAuthPolicy` | ✅ PASS |
| ✅ Declare Genie Space resource | Yes, added to `resources` list | ✅ PASS |
| ⚠️ Workspace OBO enabled | Unknown (check with admin) | ⚠️ CHECK |
| ⚠️ Genie credential mode | Unknown (check in UI) | ⚠️ **CHECK THIS** |

---

## 📋 Implementation Details

### Cell 3: Agent Definition

**Key Changes:**

1. **Import GenieAgent:**
```python
from databricks_langchain.genie import GenieAgent
```

2. **Create OBO WorkspaceClient in `_create_graph_with_obo()`:**
```python
def _create_graph_with_obo(self):
    obo_creds = ModelServingUserCredentials()
    
    # Create OBO-enabled WorkspaceClient
    workspace_client = WorkspaceClient(credentials_strategy=obo_creds)
    
    # Pass to graph creation
    graph = create_langgraph_with_nodes(
        llm=llm,
        workspace_client=workspace_client,  # ← For Genie
        externally_served_agents=self.externally_served_agents
    )
```

3. **Pass `client=` to GenieAgent in `create_langgraph_with_nodes()`:**
```python
def create_langgraph_with_nodes(llm, workspace_client, externally_served_agents):
    for agent in externally_served_agents:
        if isinstance(agent, Genie):
            genie_agent = GenieAgent(
                genie_space_id=agent.space_id,
                genie_agent_name=agent.name,
                description=agent.description,
                client=workspace_client  # ← CRITICAL for OBO!
            )
```

4. **Use GenieAgent normally in `genie_node()`:**
```python
def genie_node(state):
    response = genie_agent.invoke({"messages": messages})
    # Parse response...
```

### Cell 11: MLflow Logging

**Key Changes:**

1. **Declare ALL Resources (per documentation):**
```python
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
    DatabricksSQLWarehouse(warehouse_id="..."),
]

# Add Genie Space to resources
for agent in EXTERNALLY_SERVED_AGENTS:
    if isinstance(agent, Genie):
        resources.append(DatabricksGenieSpace(genie_space_id=agent.space_id))
```

**Understanding:**
- Resources list declares **WHAT** the agent needs
- Auth policy determines **WHO** accesses them
- Genie Space in resources + UserAuthPolicy = OBO access with RLS

2. **UserAuthPolicy with correct scopes:**
```python
userAuthPolicy = UserAuthPolicy(
    api_scopes=[
        "serving.serving-endpoints",
        "sql.warehouses",
        "sql.statement-execution",
        "dashboards.genie",  # ← CRITICAL for Genie OBO
    ]
)
```

---

## 🚨 CRITICAL: Genie Space Credential Mode

**Per the documentation you shared:**

> "If set to 'run as embedded credentials,' queries may always run as the service principal or a generic agent account."

### ⚠️ ACTION REQUIRED: Check Genie Space Settings

**Before redeploying, please check:**

1. Go to Databricks workspace
2. Navigate to your Genie Space
3. Open Settings
4. Look for "Credential Mode" or "Authentication Mode"
5. Check the setting:

| Setting | Impact | Action |
|---------|--------|--------|
| "Run as viewer" / "OBO mode" | ✅ OBO will work | Proceed with deployment |
| "Embedded credentials" / "Run as SP" | ❌ OBO CANNOT work | Change to "run as viewer" |

**If it's set to "embedded credentials," our code changes won't help!** The Genie Space itself must be configured to support OBO.

---

## 🔄 What Changed from Previous Approach

### Before (Direct API):
```python
# Custom function to call Genie API directly
def query_genie_with_obo(workspace_client, space_id, question):
    conversation = workspace_client.genie.start_conversation(...)
    message = workspace_client.genie.get_message(...)
    # Parse response...
    return response

# Use in genie_node
def genie_node(state):
    response = query_genie_with_obo(...)
```

**Issues:**
- ❌ Against LangGraph routing pattern
- ❌ Custom implementation (more code to maintain)
- ❌ Loses GenieAgent features

### After (Official Wrapper):
```python
# Use GenieAgent with client= parameter
genie_agent = GenieAgent(
    genie_space_id=agent.space_id,
    genie_agent_name=agent.name,
    client=workspace_client  # ← Simple!
)

# Use in genie_node
def genie_node(state):
    response = genie_agent.invoke({"messages": messages})
```

**Benefits:**
- ✅ Follows official documentation
- ✅ Aligns with LangGraph pattern
- ✅ Simpler and more maintainable
- ✅ Better error handling

---

## 🧪 Testing Checklist

### Before Deployment:

- [ ] **Check Genie Space credential mode** (CRITICAL!)
  - Setting should be "run as viewer" or "OBO mode"
  - NOT "embedded credentials"

- [ ] **Verify workspace OBO is enabled**
  - Ask workspace admin
  - Requires MLflow 2.22.1+

### After Deployment:

- [ ] **Test with RLS-restricted user**
  - Query: "Show me all the BUs which employees are part of"
  - Expected: Only departments user has access to (e.g., HR only)
  - NOT expected: All departments or permission errors

- [ ] **Check for errors**
  - No `PERMISSION_DENIED` errors
  - No hallucinated data (Sales/Engineering from examples)

- [ ] **Verify OBO is actually being used**
  - Different users should see different data
  - Data should match their RLS permissions

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
GenieAgent(client=workspace_client)  ← Pass OBO client via client=
    ↓
genie_agent.invoke({"messages": ...})
    ↓
GenieAgent uses USER credentials internally
    ↓
Genie Space queries Unity Catalog tables
    ↓
Unity Catalog applies RLS based on USER identity
    ↓
Returns filtered data to user
```

---

## 📊 Implementation Validation

### Code Review:

**✅ Cell 3 (agent.py):**
- [x] Imports `GenieAgent`
- [x] Creates `WorkspaceClient(credentials_strategy=obo_creds)` in `_create_graph_with_obo()`
- [x] Passes `workspace_client` to `create_langgraph_with_nodes()`
- [x] Uses `client=workspace_client` when creating `GenieAgent`
- [x] `genie_node()` calls `genie_agent.invoke()`

**✅ Cell 11 (MLflow Logging):**
- [x] Declares `DatabricksGenieSpace` in `resources` list
- [x] `UserAuthPolicy` includes `dashboards.genie` scope
- [x] `SystemAuthPolicy(resources=resources)` declares all resources
- [x] Both policies combined in `AuthPolicy`

**✅ Cell 5 (Visualization):**
- [x] Passes temporary `WorkspaceClient()` for visualization

---

## 🐛 Troubleshooting

### Issue 1: Still Getting Permission Denied

**Possible Causes:**
1. **Genie Space credential mode is "embedded credentials"**
   - **FIX:** Change to "run as viewer" in Genie Space settings

2. Old model version still deployed
   - **FIX:** Check deployed version matches latest

3. Workspace OBO not enabled
   - **FIX:** Ask admin to enable, ensure MLflow 2.22.1+

### Issue 2: Still Seeing All Data (No RLS)

**Possible Causes:**
1. **Genie Space credential mode is "embedded credentials"**
   - **FIX:** Change to "run as viewer"

2. RLS policies not configured on tables
   - **FIX:** Verify RLS policies exist:
     ```sql
     SHOW ROW FILTERS ON TABLE akash_s_demo.talent.dim_employees;
     ```

3. User actually has access to all data
   - **FIX:** Test with different user who should have restricted access

### Issue 3: TypeError on GenieAgent

**Error:**
```
TypeError: GenieAgent() got an unexpected keyword argument 'client'
```

**Possible Causes:**
1. Old version of `databricks-langchain`
   - **FIX:** Update to latest version

2. Wrong parameter name
   - **FIX:** Verify using `client=`, not `workspace_client=`

---

## 📝 Next Steps

### 1. **CRITICAL: Check Genie Space Credential Mode**

Before redeploying, please verify:
```
Genie Space → Settings → Credential Mode = "Run as viewer" (or similar)
NOT "Embedded credentials"
```

**If this is set to "embedded credentials," stop here and change it first!**

### 2. Redeploy the Agent

Run notebook cells in Databricks:
```
Cell 11: Log model
Cell 12: Register model
Cell 13: Deploy to endpoint
```

### 3. Test with RLS User

Query: "Show me all the BUs which employees are part of"

**Expected (for user with HR-only access):**
```
Based on the available data, employees are part of the HR department.

| Department | Count |
|------------|-------|
| HR         | 45    |
```

**NOT expected:**
- ❌ Permission denied errors
- ❌ All departments (Sales, Engineering, etc.)
- ❌ Hallucinated data

### 4. Report Results

**Tell me:**
- [ ] What is the Genie Space credential mode?
- [ ] Did deployment succeed?
- [ ] What data do you see when querying?
- [ ] Any errors?

---

## 🎓 Key Learnings

1. **Read the documentation carefully** - the `client=` parameter was documented all along!

2. **Resource declaration ≠ Access control**
   - Declaring a resource in the list tells Databricks WHAT is needed
   - Auth policy determines WHO can access it
   - You CAN declare Genie Space in resources AND use OBO

3. **Genie Space settings matter**
   - Credential mode must support OBO ("run as viewer")
   - "Embedded credentials" mode prevents OBO entirely

4. **Use official wrappers when available**
   - GenieAgent handles complexity internally
   - Direct API calls should be last resort
   - Follow documented patterns

---

## 🏆 Why This Approach is Correct

1. **✅ Follows official documentation** - Uses `client=` parameter as documented
2. **✅ Aligns with LangGraph** - Uses official GenieAgent wrapper
3. **✅ Simpler implementation** - Less custom code to maintain
4. **✅ Better error handling** - GenieAgent handles edge cases
5. **✅ Properly declares resources** - Per Databricks requirements

---

**Commit:** `6ec9a98` (pushed to `main`)  
**Previous commits:**
- `e8f1d62` - Direct API approach (reverted)
- `0f1d338` - Thread-local config (didn't work)

---

## ⚠️ BEFORE YOU REDEPLOY

**Check Genie Space credential mode!** This is the most common reason OBO doesn't work with Genie.

If it's set to "embedded credentials," changing the code won't help. The Genie Space itself must be configured to support OBO.

Let me know what the credential mode is set to! 🔍
