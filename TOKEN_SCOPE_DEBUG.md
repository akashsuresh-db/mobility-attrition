# 🔍 Token Scope Debugging Guide

## Problem: "Invalid scope" 403 Error

The agent endpoint rejects the request with `403 Invalid scope` before the agent even runs.

---

## Root Cause

The bearer token sent to `/serving-endpoints/.../invocations` **does not include the `serving.serving-endpoints` scope**.

This is separate from endpoint ACLs—having "Can Query" permission won't help if the token lacks the required API scope.

---

## Most Likely Causes

### 1. **Stale Token** ❌
User token was minted **before** you added `serving.serving-endpoints` scope to app User Authorization.

**Fix:** User must **re-consent** to the app with new scopes.

### 2. **App Using Service Principal** ❌
The call is being made with the **app's service principal** (via default SDK client or cached session), which doesn't carry user OBO scopes.

**Fix:** Explicitly use the user token from `X-Forwarded-Access-Token`.

### 3. **Token Not Forwarded** ❌
Multi-tier apps sometimes drop headers, so the downstream call falls back to system auth.

**Fix:** Ensure `X-Forwarded-Access-Token` is passed end-to-end.

---

## Diagnostics (Now in App Code)

The app now **automatically logs token scopes** when using OBO:

```python
# In app.py get_agent_response()
import jwt
decoded = jwt.decode(user_token, options={"verify_signature": False})
scopes = decoded.get("scp") or decoded.get("scope")
print("🔍 Token scopes:", scopes)
print("✓ Has serving.serving-endpoints:", "serving.serving-endpoints" in scopes)
print("✓ Has dashboards.genie:", "dashboards.genie" in scopes)
```

### What You Should See in App Logs:

#### ✅ **Working (Correct Scopes):**
```
Processing request for user: akash.s@databricks.com
Using OBO REDACTED_SECRET
🔍 Token scopes: ['serving.serving-endpoints', 'dashboards.genie', 'sql', ...]
✓ Has serving.serving-endpoints: True
✓ Has dashboards.genie: True
Calling agent at: https://.../invocations
✅ Response received
```

#### ❌ **Broken (Missing Scopes):**
```
Processing request for user: akash.s@databricks.com
Using OBO REDACTED_SECRET
🔍 Token scopes: ['sql', 'catalog.tables', ...]
✓ Has serving.serving-endpoints: False  ← PROBLEM!
✓ Has dashboards.genie: False           ← PROBLEM!
⚠️ WARNING: Token missing 'serving.serving-endpoints' scope!
   This will cause 403 Invalid scope error.
ERROR: HTTP Error: 403
Response text: Invalid scope
```

---

## Fixes to Apply

### Fix 1: Ensure Fresh Token with Correct Scopes ✅

1. **In Databricks UI:**
   ```
   Compute → Databricks Apps → [Your App] → Settings
   → User Authorization
   ☑ Enable user authorization
   
   API Scopes:
   • Model Serving endpoints  [ENABLE]
   • Genie spaces            [ENABLE]
   • SQL                     [ENABLE if agent uses SQL]
   
   [Save]
   ```

2. **Restart the app** (happens automatically after save)

3. **User must re-consent:**
   - Open app in browser
   - You'll see OAuth prompt:
     ```
     "This app wants to access:
      - Model Serving Endpoints
      - Genie Spaces
      - SQL
     
     [Authorize] [Cancel]"
     ```
   - Click **Authorize**
   - This generates a NEW token with the correct scopes

### Fix 2: Verify App Uses User Token (Already Done) ✅

The app correctly:
```python
# In update_chat callback
user_token = flask.request.headers.get('X-Forwarded-Access-Token')

if user_token:
    response = get_agent_response(conversation_history, user_token=user_token)
else:
    # Fallback to system auth
    response = get_agent_response(conversation_history)
```

And forwards it properly:
```python
# In get_agent_response
headers = {
    "Authorization": f"Bearer {auth_token}",  # ← user_token passed here
    "Content-Type": "application/json"
}
response = requests.post(url, headers=headers, json=payload)
```

### Fix 3: Required Scopes Must Match Agent's UserAuthPolicy ✅

Your agent requires:
```python
userAuthPolicy = UserAuthPolicy(
    api_scopes=[
        "serving.serving-endpoints",  # ← MUST be in app token
        "dashboards.genie",           # ← MUST be in app token
    ]
)
```

The app's User Authorization must request **at least these scopes**.

---

## Testing After Fix

### Step 1: Clear Browser Session
```bash
# Clear browser cache/cookies or use incognito mode
# This ensures no stale tokens are cached
```

### Step 2: Open App
```
1. Navigate to app URL
2. You SHOULD see OAuth consent screen (first time after scope change)
3. Click "Authorize"
```

### Step 3: Check App Logs
```
Look for:
🔍 Token scopes: ['serving.serving-endpoints', 'dashboards.genie', ...]
✓ Has serving.serving-endpoints: True
✓ Has dashboards.genie: True
```

### Step 4: Test Query
```
Ask: "Which department has the highest attrition rate?"

Expected:
- No 403 error
- Agent responds
- Only see YOUR data (HR for you, due to RLS)
```

---

## Manual cURL Test (Sanity Check)

If app still fails, test the endpoint directly with your token:

```bash
# 1. Get your user token from app logs (look for REDACTED_SECRET line)
export USER_TOKEN="eyJraWQiOi..."

# 2. Test GET (check if token has serving scope)
curl -sS -H "Authorization: Bearer $USER_TOKEN" \
  https://adb-984752964297111.11.azuredatabricks.net/api/2.0/serving-endpoints/agents_akash_s_demo-talent-talent_agent_v1

# 3. Test POST (actual invocation)
curl -sS -X POST \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}' \
  https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints/agents_akash_s_demo-talent-talent_agent_v1/invocations
```

**Expected:**
- GET returns endpoint details (200 OK)
- POST returns agent response (200 OK)

**If you get 403:**
- Token still doesn't have `serving.serving-endpoints` scope
- User needs to re-consent in the app

---

## Pre-empting Next Error: SQL Scopes

Your agent's `UserAuthPolicy` currently has:
```python
api_scopes=[
    "serving.serving-endpoints",
    "dashboards.genie",
]
```

**If your agent performs SQL queries** during `predict()` (e.g., Genie queries Unity Catalog tables), you'll need:
```python
api_scopes=[
    "serving.serving-endpoints",
    "dashboards.genie",
    "sql.warehouses",           # ← Add if agent uses SQL
    "sql.statement-execution",  # ← Add if agent uses SQL
]
```

And the app's User Authorization must also include:
- ✅ SQL

Otherwise you'll get a different 403 during agent execution (not during invocation).

---

## Summary Checklist

- [ ] App User Authorization has `serving.serving-endpoints` scope enabled
- [ ] App User Authorization has `dashboards.genie` scope enabled
- [ ] App restarted after scope change
- [ ] User re-consented to app (saw OAuth prompt)
- [ ] App logs show: `✓ Has serving.serving-endpoints: True`
- [ ] App logs show: `✓ Has dashboards.genie: True`
- [ ] No more `403 Invalid scope` errors
- [ ] Agent responds successfully
- [ ] RLS enforced (user sees only their data)

---

## Key Insight from Internal Doc

> "Once your app forwards a fresh user token that includes `serving.serving-endpoints`, the invocation should succeed and the agent will downscope that token to the scopes declared in your **UserAuthPolicy** during `predict()`."

**Translation:**
1. App token must have `serving.serving-endpoints` to **reach** the agent endpoint
2. Once inside, agent uses `UserAuthPolicy` to determine which resources the token can access
3. Both must align for OBO to work end-to-end

**App token scopes ⊇ Agent required scopes** (superset or equal)

---

**Next Step:** Redeploy app, clear browser cache, re-consent, and check logs for scope presence! 🚀

