# Troubleshooting Guide

## "Invalid scope" or "OAuth token does not have required scopes" Error

This error means the authentication token doesn't have the required OAuth scopes to access serving endpoints.

### Root Cause:

User OAuth tokens (like X-Forwarded-Access-Token) don't include the scopes needed for serving endpoints. You need to configure an **app-level token** (PAT or service principal) instead.

### Solution:

#### Step 1: Set DATABRICKS_TOKEN Environment Variable

The app needs a Personal Access Token (PAT) configured:

1. **Create a PAT:**
   - Go to Databricks → Your Profile → Settings → Developer
   - Generate new token
   - Copy the token value

2. **Grant permissions to your user:**
   - Go to **Serving** → **Serving Endpoints**
   - Find: `agents_akash_s_demo-talent-mobility_attrition`
   - Click Permissions → Add your user
   - Grant **"Can Query"** permission

3. **Configure in Databricks App:**
   - Go to your app settings
   - Add Environment Variable:
     - Key: `DATABRICKS_TOKEN`
     - Value: Your PAT from step 1
   - Save and **Redeploy**

#### Step 2: Verify Configuration

- Check the endpoint name in `app.py`:
  ```python
  MODEL_NAME = "agents_akash_s_demo-talent-mobility_attrition"
  ```

- Verify the base URL matches your workspace:
  ```python
  BASE_URL = "https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints"
  ```

- Ensure the endpoint is "Ready" (not stopped)

See [DATABRICKS_APPS_SETUP.md](DATABRICKS_APPS_SETUP.md) for detailed setup instructions.

---

## Other Common Errors

### "Endpoint Not Found" (404)

**Cause:** The model name or endpoint URL is incorrect.

**Solution:**
1. Verify the endpoint exists in your workspace
2. Check the exact name (case-sensitive)
3. Ensure the endpoint is deployed and running

### "Authentication Error" (401)

**Cause:** Token is invalid or expired.

**Solution:**
1. In Databricks Apps, this should auto-refresh with the user's token
2. For local development, regenerate your personal access token
3. Ensure the token hasn't been revoked

### "App not available"

**Cause:** App can't bind to the correct port.

**Solution:**
- This should be fixed in the latest version
- Ensure `server = app.server` is present in `app.py`
- Check that `ProxyFix` middleware is configured

### Empty Response

**Cause:** Agent returned no content.

**Solution:**
1. Check if the agent is properly configured
2. Verify the agent has access to required data sources
3. Test the endpoint directly using the API

---

## Testing the Endpoint Directly

Use the test script to verify endpoint access:

```bash
export DATABRICKS_TOKEN='your_token_here'
python test_auth.py
```

This will tell you if:
- Your token is valid
- You have access to the endpoint
- The endpoint is responding correctly

---

## Getting Help

If you're still having issues:

1. Check the **App Logs** in Databricks Apps for detailed error messages
2. Verify all permissions are correctly set
3. Test with a simple question first: "Hello"
4. Check if the serving endpoint is running and healthy

## Endpoint Permissions Checklist

✅ User has "Can Query" permission on the serving endpoint  
✅ Endpoint is in "Ready" state  
✅ Model name exactly matches the endpoint name  
✅ Base URL matches your workspace URL  
✅ App is using the latest code from the repository

