# 🔍 How to Check Current App Scopes

## Option 1: Via Databricks UI (Easiest)

1. Go to **Workspace** → **Compute** → **Databricks Apps**
2. Find your app
3. Click **Settings** (gear icon)
4. Scroll to **User Authorization** section
5. Check the **API Scopes** list

**Required scopes:**
- ✅ `serving.serving-endpoints`
- ✅ `dashboards.genie`

**NOT needed (remove if present):**
- ❌ `sql.warehouses`
- ❌ `sql.statement-execution`
- ❌ `catalog.*`

---

## Option 2: Via App Logs (Debug)

Your app logs show:
```
Using OBO REDACTED_SECRET
Token prefix: eyJraWQiOi... (length: 956)
```

This confirms the app IS getting a user token. The problem is the token's scopes don't match the agent's requirements.

---

## The Issue

### What's Happening:
```
App User Token Scopes    ≠    Agent Required Scopes
      (unknown)                serving.serving-endpoints
                               dashboards.genie
```

### Result:
```
Agent rejects token → 403 Invalid scope
```

---

## The Fix

**In Databricks Apps UI Settings:**

1. User Authorization → **Enable**
2. API Scopes → **Add these exactly:**
   - `serving.serving-endpoints`
   - `dashboards.genie`
3. **Remove any other scopes** (sql.*, catalog.*, etc.)
4. **Save** → App restarts
5. **Test** → First time will ask user to authorize

---

## Why This Happens

Databricks Apps injects the user's token into `X-Forwarded-Access-Token`, but the token only contains the scopes that are:
1. Configured in the app's User Authorization settings
2. Available to the user (based on their workspace permissions)

If the app requests scopes the agent doesn't need (like `sql.warehouses`), or doesn't request scopes the agent DOES need (like `dashboards.genie`), the agent will reject the token.

---

## After Fixing

### Expected Flow:
1. User opens app
2. **First time:** User sees OAuth authorization prompt
   ```
   "This app wants to access:
   - Model Serving Endpoints
   - Genie Spaces"
   
   [Authorize] [Cancel]
   ```
3. User clicks **Authorize**
4. App receives token with correct scopes
5. Agent accepts token
6. Query succeeds with RLS ✅

### App Logs (Success):
```
Processing request for user: akash.s@databricks.com
Using OBO REDACTED_SECRET
Calling agent at: https://.../invocations
✅ Successfully received response
```

### No More 403 Errors ✅

---

**ACTION REQUIRED:** Update the app's User Authorization scopes in Databricks UI.
