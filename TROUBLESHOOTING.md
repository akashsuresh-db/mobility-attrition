# Troubleshooting Guide

## "Invalid scope" Error

This error means your user account doesn't have permission to query the agent endpoint.

### Solution:

1. **Go to Databricks Workspace** → **Serving** → **Serving Endpoints**

2. **Find your endpoint:** `agents_akash_s_demo-talent-mobility_attrition`

3. **Click on the endpoint** to open its details

4. **Go to the Permissions tab**

5. **Add permissions:**
   - Click "Grant" or "Add"
   - Add your user or a group you belong to
   - Grant **"Can Query"** permission
   - Click "Save"

6. **Redeploy or refresh your Databricks App**

### Additional Checks:

- Verify the endpoint name is correct in `app.py` (line 10):
  ```python
  MODEL_NAME = "agents_akash_s_demo-talent-mobility_attrition"
  ```

- Check the base URL matches your workspace (line 11):
  ```python
  BASE_URL = "https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints"
  ```

- Ensure the endpoint is in a "Ready" state (not stopped or failed)

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

