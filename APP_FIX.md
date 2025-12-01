# 🔧 Fix "Invalid scope" Error in Databricks App

## Problem
The app is correctly sending the user's OBO token, but getting `403 Invalid scope` error.

## Root Cause
The Databricks App's **User Authorization** scopes don't match what the agent requires.

---

## ✅ SOLUTION: Update App User Authorization

### Step 1: Open App Settings in Databricks UI
1. Go to **Databricks Workspace**
2. Navigate to **Compute** → **Databricks Apps**
3. Find your app and click **Settings**

### Step 2: Configure User Authorization
1. Scroll to **User Authorization** section
2. **Enable** "Request user authorization"
3. Add these **API Scopes**:
   - ✅ `serving.serving-endpoints`
   - ✅ `dashboards.genie`

### Step 3: Save and Redeploy
1. Click **Save**
2. App will restart automatically

---

## Why These Scopes?

Your agent's `UserAuthPolicy` requires exactly these scopes:

```python
userAuthPolicy = UserAuthPolicy(
    api_scopes=[
        "serving.serving-endpoints",     # For calling the agent endpoint
        "dashboards.genie",              # For Genie Space access with RLS
    ]
)
```

The app's user authorization token must contain **at least** these scopes for the agent to accept it.

---

## Current Status

### ✅ What's Working:
- Agent deployed with OBO
- Agent works via endpoint (when you test directly)
- App correctly extracts user token from `X-Forwarded-Access-Token`
- App correctly sends `Authorization: Bearer {user_token}` to agent

### ❌ What's Broken:
- App's user authorization token doesn't have the scopes the agent requires
- Agent rejects the token with `403 Invalid scope`

---

## After Fix, You Should See:

### App Logs (Success):
```
Processing request for user: akash.s@databricks.com
Using OBO REDACTED_SECRET
Calling agent at: https://.../invocations
✅ Response received from agent
```

### No More Errors:
- ❌ `403 Invalid scope` → ✅ Gone
- ❌ `Permission Error` → ✅ Gone

### User Experience:
1. User opens app → Prompted to authorize scopes (first time only)
2. User authorizes → App can call agent on their behalf
3. User asks question → Agent responds with RLS-filtered data (only HR for you!)

---

## Verification Checklist

After updating app settings:

- [ ] App Settings → User Authorization → Enabled
- [ ] API Scopes include: `serving.serving-endpoints`
- [ ] API Scopes include: `dashboards.genie`
- [ ] App redeployed/restarted
- [ ] Test query in app
- [ ] No "Invalid scope" error in logs
- [ ] Agent responds successfully
- [ ] Only see YOUR data (HR department)

---

## If Still Not Working

1. **Check agent deployment status:**
   ```
   Is the agent you deployed (with simplified UserAuthPolicy) actually serving?
   Check endpoint version in Databricks UI.
   ```

2. **Verify app is using latest code:**
   ```
   App logs should show: "Using OBO REDACTED_SECRET"
   If not, redeploy the app.
   ```

3. **Test agent directly with your PAT:**
   ```python
   # In notebook
   import requests
   response = requests.post(
       "https://.../invocations",
       headers={"Authorization": f"Bearer {YOUR_PAT}"},
       json={"input": [{"role": "user", "content": "test"}]}
   )
   print(response.status_code)  # Should be 200
   ```

4. **Check which scopes your user token actually has:**
   The Databricks Apps framework should automatically include the scopes you configure.
   If you're still getting "Invalid scope", the app may need to be fully recreated.

---

## Quick Reference: Where to Configure

```
Databricks Workspace UI
  ↓
Compute → Databricks Apps
  ↓
[Your App] → Settings (gear icon)
  ↓
User Authorization
  ↓
☑ Enable user authorization
  ↓
API Scopes:
  • serving.serving-endpoints  [Add]
  • dashboards.genie          [Add]
  ↓
[Save]
```

---

**CRITICAL:** The scopes in the app MUST EXACTLY MATCH the scopes in the agent's `UserAuthPolicy`.

Agent requires: `serving.serving-endpoints`, `dashboards.genie`
App must request: `serving.serving-endpoints`, `dashboards.genie`

**No more, no less!** ✅

