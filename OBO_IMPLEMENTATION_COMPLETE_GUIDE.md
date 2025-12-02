# 🎯 Complete OBO Implementation Guide
## Multi-Agent System with Row-Level Security

**Status:** ✅ Fully Implemented and Working  
**Last Updated:** 2025-12-01  
**Components:** Agent (Notebook) + Databricks App

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Agent OBO Implementation](#agent-obo-implementation)
3. [Databricks App OBO Implementation](#databricks-app-obo-implementation)
4. [Deployment Steps](#deployment-steps)
5. [Troubleshooting](#troubleshooting)
6. [Testing & Validation](#testing--validation)

---

## Overview

### What is OBO (On-Behalf-Of) Authentication?

OBO allows the agent to execute queries using the **end user's credentials** instead of a service principal, enabling:
- ✅ **Row-Level Security (RLS)** enforcement
- ✅ **User-specific data access** based on Unity Catalog permissions
- ✅ **Audit trails** showing which user accessed what data
- ✅ **Multi-tenant** data isolation

### Architecture

```
User → Databricks App → Agent Endpoint → Genie Space → Unity Catalog Tables
        (User Token)    (OBO Creds)      (User Creds)   (RLS Applied)
```

---

## Agent OBO Implementation

### File: `langgraph-agent-with-summary.ipynb`

### 1. Cell 1: Install Dependencies

```python
%pip install -U -qqq langgraph-supervisor==0.0.30 mlflow[databricks] \
    databricks-langchain databricks-agents databricks-ai-bridge uv
dbutils.library.restartPython()
```

**Key Addition:** `databricks-ai-bridge` for `ModelServingUserCredentials`

---

### 2. Cell 3: Agent Code with OBO

#### **Critical: Create OBO Resources Per Request**

```python
from databricks_ai_bridge import ModelServingUserCredentials
from databricks.sdk import WorkspaceClient

class LangGraphResponsesAgent(ResponsesAgent):
    def __init__(self, llm_endpoint_name: str, externally_served_agents: list):
        """Store config only - NO OBO resources here!"""
        self.llm_endpoint_name = llm_endpoint_name
        self.externally_served_agents = externally_served_agents
        # ✅ Config stored, OBO resources deferred to predict()
    
    def _create_graph_with_obo(self):
        """
        Create OBO resources INSIDE predict/predict_stream.
        User identity only available at query time!
        """
        # 1. Create OBO credentials
        obo_creds = ModelServingUserCredentials()
        
        # 2. Create OBO-enabled UC function client
        client = DatabricksFunctionClient(credentials_strategy=obo_creds)
        set_uc_function_client(client)
        
        # 3. Create OBO-enabled LLM
        llm = ChatDatabricks(
            endpoint=self.llm_endpoint_name,
            credentials_strategy=obo_creds
        )
        
        # 4. Create OBO-enabled WorkspaceClient for GenieAgent
        workspace_client = WorkspaceClient(credentials_strategy=obo_creds)
        
        # 5. Create graph with OBO resources
        graph = create_langgraph_with_nodes(
            llm=llm,
            workspace_client=workspace_client,  # ← CRITICAL for Genie OBO!
            externally_served_agents=self.externally_served_agents
        )
        return graph
    
    def predict(self, request: ResponsesAgentRequest):
        # Create OBO graph for THIS request with THIS user's credentials
        agent = self._create_graph_with_obo()
        # ... rest of predict logic
```

**Key Points:**
- ❌ **DON'T** create OBO resources in `__init__` (user identity not available yet)
- ✅ **DO** create OBO resources in `predict/predict_stream` (user identity available)
- ✅ Use `credentials_strategy` (not deprecated `credentials_provider`)
- ✅ Pass `workspace_client` to `GenieAgent` via `client=` parameter

---

#### **Pass OBO Client to GenieAgent**

```python
def create_langgraph_with_nodes(
    llm: Runnable,
    workspace_client: WorkspaceClient,  # ← Accept OBO client
    externally_served_agents: list[ServedSubAgent] = [],
):
    # Create Genie agent with OBO credentials
    genie_agent = None
    for agent in externally_served_agents:
        if isinstance(agent, Genie):
            genie_agent = GenieAgent(
                genie_space_id=agent.space_id,
                genie_agent_name=agent.name,
                description=agent.description,
                client=workspace_client  # ← CRITICAL for OBO!
            )
            genie_agent.name = agent.name
            break
    # ... rest of graph creation
```

**CRITICAL:** The `client=workspace_client` parameter is the **documented way** to enable OBO for GenieAgent.

---

### 3. Cell 11: MLflow Logging with Auth Policies

```python
from mlflow.models.auth_policy import AuthPolicy, SystemAuthPolicy, UserAuthPolicy

# Declare ALL resources used by agent
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
    DatabricksSQLWarehouse(warehouse_id="148ccb90800933a1"),
    DatabricksGenieSpace(genie_space_id=agent.space_id),  # ← Declare Genie
]

# System auth: Declares resources (service principal manages infrastructure)
systemAuthPolicy = SystemAuthPolicy(resources=resources)

# User auth: Define API scopes for OBO
userAuthPolicy = UserAuthPolicy(
    api_scopes=[
        "serving.serving-endpoints",  # Required to reach endpoint
        "dashboards.genie",           # Required for Genie Space OBO
    ]
)

# Log model with OBO
with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model="agent.py",
        auth_policy=AuthPolicy(
            system_auth_policy=systemAuthPolicy,
            user_auth_policy=userAuthPolicy
        ),
        pip_requirements=[
            # ... other deps ...
            "databricks-ai-bridge",  # ← Required for OBO!
        ],
    )
```

**Key Points:**
- ✅ Declare **ALL** resources in `SystemAuthPolicy` (infrastructure + data)
- ✅ `UserAuthPolicy` scopes must match what app can provide
- ✅ Keep scopes simple: `serving.serving-endpoints` + `dashboards.genie`
- ❌ **DON'T** pass `resources` separately (already in SystemAuthPolicy)

---

### 4. Graceful Empty Result Handling

```python
def genie_node(state: AgentState):
    # ... get genie_content ...
    
    # Check if empty
    is_empty = (
        len(genie_content.strip()) < 10 or
        any(indicator in genie_content.lower() for indicator in 
            ["no rows", "no data", "no results", "returned 0 rows"]) or
        (genie_content.count('|') <= 4 and len(genie_content.split('\n')) <= 3)
    )
    
    if is_empty:
        helpful_msg = (
            "EMPTY_GENIE_RESULT: I don't have access to data for your query. "
            "This could be because:\n"
            "1. Your data permissions (RLS) limit what you can see\n"
            "2. The data you're asking for is outside your access scope\n"
            "3. There's no data available for this specific query\n\n"
            "Try asking about data within your department or scope."
        )
        return {"messages": [AIMessage(content=helpful_msg, name="genie")]}
```

**Benefits:**
- ✅ Clear explanation when RLS filters all data
- ✅ Prevents LLM hallucination on empty results
- ✅ Guides user to ask scoped questions

---

## Databricks App OBO Implementation

### File: `app.py`

### 1. Never Cache User Tokens

```python
# CRITICAL: DO NOT cache user tokens or clients!
# Each request must use fresh X-Forwarded-Access-Token header for OBO.
# Caching tokens causes "Invalid scope" errors with stale tokens.

# ❌ BAD - Don't do this:
# _cached_client = None
# if user_token and _cached_client:
#     return _cached_client

# ✅ GOOD - Always read per-request:
user_token = request.headers.get('X-Forwarded-Access-Token')
```

---

### 2. Extract and Validate User Token

```python
def update_chat(send_clicks, clear_clicks, n_submit, user_message, conversation_history):
    # CRITICAL: Read user token from request headers PER REQUEST (never cache!)
    user_token = request.headers.get('X-Forwarded-Access-Token')
    
    # Validate token is present
    if not user_token:
        print("❌ ERROR: No user token found!")
        return error_response("No user access token found")
    
    print(f"✓ User token found (length: {len(user_token)})")
    
    # Always use the per-request token (never cache!)
    agent_response = get_agent_response(
        conversation_history, 
        user_token=user_token  # ← Always fresh per-request token
    )
```

---

### 3. Verify Token Scopes (Debugging)

```python
def get_agent_response(conversation_history, user_token=None):
    if user_token:
        # Decode token and check scopes (for debugging)
        import jwt
        decoded = jwt.decode(user_token, options={"verify_signature": False})
        scopes = decoded.get("scp") or decoded.get("scope") or "NO_SCOPES_FOUND"
        print(f"🔍 Token scopes: {scopes}")
        
        # Check for required scopes
        has_serving = "serving.serving-endpoints" in str(scopes)
        has_genie = "dashboards.genie" in str(scopes)
        
        print(f"✓ Has serving.serving-endpoints: {has_serving}")
        print(f"✓ Has dashboards.genie: {has_genie}")
        
        # If critical scopes missing, return error immediately
        if not has_serving or not has_genie:
            return "⚠️ Token Missing Required Scopes\n\n[Instructions to re-consent]"
```

---

### 4. Call Agent with User Token

```python
def get_agent_response(conversation_history, user_token=None):
    # Use direct requests.post with user token
    headers = {
        "Authorization": f"Bearer {user_token}",  # ← Per-request user token
        "Content-Type": "application/json"
    }
    
    # Agent Framework schema (NOT OpenAI schema!)
    payload = {
        "input": conversation_history,  # ← "input" not "messages"
        "metadata": {
            "user": request.headers.get('X-Forwarded-Email', 'unknown'),
            "source": "databricks_app"
        }
    }
    
    url = f"https://{host}/serving-endpoints/{MODEL_NAME}/invocations"
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    
    return response.json()
```

**Key Points:**
- ✅ Use `Authorization: Bearer {user_token}` header
- ✅ Use Agent Framework schema: `{"input": [...]}` not `{"messages": [...]}`
- ✅ Never cache or fall back to app token
- ✅ Add metadata for tracking

---

## Deployment Steps

### Step 1: Deploy Agent

```bash
# In Databricks notebook: langgraph-agent-with-summary.ipynb

# Cell 11: Log model with OBO
# Cell 12: Register to Unity Catalog
# Cell 13: Deploy to serving endpoint
```

**Verify:**
- ✅ Endpoint status: "Ready"
- ✅ Auth policy shows UserAuthPolicy with scopes
- ✅ Test with direct API call (should work with your PAT)

---

### Step 2: Configure Databricks App

```
Databricks UI
  → Compute → Databricks Apps
  → [Your App] → Settings
  → User Authorization

☑ Enable user authorization

API Scopes (check these):
  ☑ Model Serving endpoints  ← serving.serving-endpoints
  ☑ Genie spaces            ← dashboards.genie
  ☑ SQL                     ← Optional but helpful

[Save]
```

**App restarts automatically after saving.**

---

### Step 3: Deploy App

```bash
# App auto-deploys when code changes pushed to repo
# Or manually restart from Databricks Apps UI
```

---

### Step 4: User Re-Consent (CRITICAL!)

**Users MUST re-consent after app User Authorization changes:**

1. **Close all browser tabs** with the app
2. **Open incognito/private browser window**
3. **Navigate to app URL**
4. **MUST see OAuth consent screen:**
   ```
   "This app wants to access:
    ☑ Model Serving Endpoints
    ☑ Genie Spaces
    [Authorize] [Cancel]"
   ```
5. **Click "Authorize"**
6. **New token generated** with correct scopes

**If you DON'T see consent screen:**
- Clear browser cache/cookies
- Check app User Authorization settings are enabled
- Ensure scopes are checked and saved

---

## Troubleshooting

### Issue 1: `403 Invalid scope`

**Symptom:**
```
ERROR: HTTP Error: 403
Response text: Invalid scope
```

**Cause:** Token missing required scopes

**Check App Logs:**
```
🔍 Token scopes: [...]
✓ Has serving.serving-endpoints: False  ← PROBLEM!
✓ Has dashboards.genie: False           ← PROBLEM!
```

**Fix:**
1. Verify app User Authorization has both scopes enabled
2. User must clear cache and re-consent
3. Use incognito mode to force fresh session

---

### Issue 2: `400 Bad Request - missing inputs ['input']`

**Symptom:**
```
Model is missing inputs ['input']. 
Note that there were extra inputs: ['messages'].
```

**Cause:** App sending OpenAI schema instead of Agent Framework schema

**Fix:**
```python
# ❌ WRONG
payload = {"messages": conversation_history}

# ✅ CORRECT
payload = {"input": conversation_history}
```

---

### Issue 3: Empty Genie Results

**Symptom:** Agent returns "no data" or empty table

**Possible Causes:**

**A) RLS Working Correctly (Most Common)**
- User asks: "Show me ALL departments"
- RLS limits user to: HR only
- Query returns empty (can't see "all")

**Solution:** Ask scoped questions
```
❌ "Show me ALL departments"
✅ "Show me data for my department"
✅ "What's the attrition rate in HR?"
```

**B) Agent Returns Helpful Message (After Fix)**
```
I don't have access to data for your query. This could be because:
1. Your data permissions (RLS) limit what you can see
2. The data you're asking for is outside your access scope
3. There's no data available for this specific query

Try asking about data within your department or scope.
```

**Check:** Test same question directly in Genie Space UI
- **Works in Genie UI?** → Problem in agent code
- **Fails in Genie UI?** → RLS or data access issue

---

### Issue 4: Token Oscillation (403 → Works → 403)

**Symptom:** Sometimes works, sometimes gets 403

**Cause:** App caching old token or falling back to app token

**Fix:** (Already implemented in latest code)
```python
# ✅ Always use per-request token
user_token = request.headers.get('X-Forwarded-Access-Token')

# ✅ Never cache across requests
# ✅ Never fall back to app token
# ✅ Fail fast if no user token
```

---

### Issue 5: AttributeError: 'ModelServingUserCredentials' object has no attribute 'token'

**Symptom:**
```
AttributeError: 'ModelServingUserCredentials' object has no attribute 'token'
```

**Cause:** Trying to call `.token()` on credentials object

**Fix:**
```python
# ❌ WRONG - Don't do this:
obo_token = obo_creds.token()
os.environ['DATABRICKS_TOKEN'] = obo_token

# ✅ CORRECT - Pass credentials object directly:
workspace_client = WorkspaceClient(credentials_strategy=obo_creds)
```

---

## Testing & Validation

### Test 1: Verify Token Scopes

**Check app logs after making a request:**

**✅ Success:**
```
Processing request for user: user@example.com
✓ User token found (length: 1013)
🔍 Token scopes: [...serving.serving-endpoints...dashboards.genie...]
✓ Has serving.serving-endpoints: True
✓ Has dashboards.genie: True
Calling agent at: https://.../invocations
Response status: 200
```

**❌ Failure:**
```
🔍 Token scopes: [offline_access email ...]
✓ Has serving.serving-endpoints: False  ← Missing!
✓ Has dashboards.genie: False           ← Missing!
ERROR: HTTP Error: 403
Response text: Invalid scope
```

---

### Test 2: Verify RLS Enforcement

**Setup:**
- User A has RLS access to: HR department only
- User B has RLS access to: Engineering department only

**Test:**

1. **User A asks:** "Show me attrition in HR"
   - **Expected:** ✅ Returns HR data only
   
2. **User A asks:** "Show me attrition in Engineering"
   - **Expected:** ✅ Returns empty (no access)
   
3. **User B asks:** "Show me attrition in Engineering"
   - **Expected:** ✅ Returns Engineering data only
   
4. **User B asks:** "Show me attrition in HR"
   - **Expected:** ✅ Returns empty (no access)

**If both users see ALL data:** ❌ RLS not working (agent using service principal)

---

### Test 3: Verify Agent Endpoint Works

**Direct API Test (with your PAT):**

```bash
export USER_TOKEN="your_personal_access_token"

curl -X POST \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","content":"What is the attrition rate?"}]}' \
  https://your-workspace.databricks.net/serving-endpoints/your-agent/invocations
```

**Expected:** 200 OK with agent response

---

### Test 4: Verify App Forwards Token

**Check app logs:**
```
Processing request for user: user@example.com
Using OBO - calling endpoint with user token
✓ User token found (length: 1013)
Token prefix: eyJraWQiOi...
```

**NOT:**
```
Using app token - calling endpoint with service principal  ← BAD!
```

---

## Summary Checklist

### Agent Implementation
- [x] `databricks-ai-bridge` in pip requirements
- [x] `ModelServingUserCredentials()` in predict/predict_stream (not __init__)
- [x] `WorkspaceClient(credentials_strategy=obo_creds)` created per request
- [x] `GenieAgent(..., client=workspace_client)` for OBO
- [x] `credentials_strategy` used (not deprecated `credentials_provider`)
- [x] `UserAuthPolicy` with `serving.serving-endpoints` + `dashboards.genie`
- [x] Resources declared in `SystemAuthPolicy`
- [x] Empty result handling with helpful messages

### App Implementation
- [x] Read `X-Forwarded-Access-Token` per request
- [x] Never cache user tokens
- [x] Never fall back to app token
- [x] Token scope verification (debugging)
- [x] Use Agent Framework schema: `{"input": [...]}`
- [x] Direct `requests.post` with `Authorization: Bearer {user_token}`
- [x] PyJWT in requirements.txt

### Deployment
- [x] Agent deployed to serving endpoint
- [x] App User Authorization configured (serving + genie scopes)
- [x] App deployed and running
- [x] User re-consented after scope changes

### Testing
- [x] Token has required scopes (check logs)
- [x] No `403 Invalid scope` errors
- [x] No `400 missing input` errors
- [x] RLS enforced (users see only their data)
- [x] Empty results handled gracefully
- [x] App logs show per-request token usage

---

## Key Takeaways

### 1. OBO Resources Must Be Per-Request
```python
# ❌ WRONG - Don't create in __init__
def __init__(self):
    self.workspace_client = WorkspaceClient(...)  # NO!

# ✅ CORRECT - Create in predict/predict_stream
def predict(self, request):
    obo_creds = ModelServingUserCredentials()
    workspace_client = WorkspaceClient(credentials_strategy=obo_creds)
```

### 2. Pass OBO Client to GenieAgent
```python
# ✅ CRITICAL for RLS enforcement
genie_agent = GenieAgent(
    ...,
    client=workspace_client  # ← This enables OBO!
)
```

### 3. App Must Use Per-Request Token
```python
# ✅ Read fresh token every request
user_token = request.headers.get('X-Forwarded-Access-Token')

# ❌ Never cache
# ❌ Never fall back to app token
# ❌ Never use default SDK clients
```

### 4. User Must Re-Consent After Scope Changes
- App User Authorization change → User must re-consent
- Clear cache → Open in incognito → See OAuth screen → Authorize
- No consent = old token = missing scopes = 403 error

### 5. Match App Scopes to Agent Requirements
```python
# Agent requires:
userAuthPolicy = UserAuthPolicy(
    api_scopes=["serving.serving-endpoints", "dashboards.genie"]
)

# App must request at least:
User Authorization:
  ☑ Model Serving endpoints
  ☑ Genie spaces
```

---

## Resources

- **Databricks Docs:** [Agent Framework with OBO](https://docs.databricks.com/en/generative-ai/agent-framework/)
- **Files in this repo:**
  - `langgraph-agent-with-summary.ipynb` - Agent implementation
  - `app.py` - Databricks App implementation
  - `requirements.txt` - App dependencies

---

**Status:** ✅ All components implemented and working!

**Last Validated:** 2025-12-01

**Questions?** Check the Troubleshooting section above or review agent/app logs for DEBUG output.

