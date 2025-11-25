# Deploying to Databricks Apps

## Authentication (Automatic!)

Good news! The app now uses **on-behalf-of-user authentication** via HTTP headers, which means:

✅ **No manual token configuration needed in Databricks Apps**  
✅ Each user authenticates with their own token automatically  
✅ More secure - users only have access to what they're authorized for

### How It Works

When running in Databricks Apps, the app automatically receives the user's access token via the `X-Forwarded-Access-Token` HTTP header. The app detects this and uses it to authenticate API calls to your agent endpoint.

### For Local Development

When running locally, you still need to set the environment variable:

```bash
export DATABRICKS_TOKEN='your_databricks_token_here'
python app.py
```

## Deployment Steps

1. **Prepare your files:**
   - Ensure `app.py` and `requirements.txt` are in your workspace

2. **Create/Update Databricks App:**
   - Navigate to your Databricks workspace
   - Go to **Apps** in the sidebar
   - Click **Create App** or select your existing app
   - Set the source file to `app.py`
   - **No additional configuration needed!** ✨

3. **Deploy:**
   - Click **Deploy**
   - Monitor the logs for any errors
   - The app will automatically authenticate using the user's token

## Troubleshooting

### "Authentication not configured" Error

This error means the app can't get a valid token. Possible causes:

**In Databricks Apps:**
- The `X-Forwarded-Access-Token` header is not being passed (this should happen automatically)
- Check your Databricks Apps version and configuration

**Local Development:**
- Make sure you've set the `DATABRICKS_TOKEN` environment variable:
  ```bash
  export DATABRICKS_TOKEN='your_token_here'
  ```

### "Configuration Error" in Chat

This appears when the authentication fails. Check:
- Does your user/token have permissions to access the serving endpoint?
- Is the serving endpoint URL correct in `app.py`?
- Is the model name correct?

### Check App Logs

In Databricks Apps, you can view logs to see detailed error messages:
1. Go to your app in the Apps section
2. Click on the **Logs** tab
3. Look for error messages or authentication failures

## Authentication Flow

**Databricks Apps (Production):**
1. User accesses the app
2. Databricks Apps automatically adds `X-Forwarded-Access-Token` header with user's token
3. App uses this token to authenticate API calls
4. Each user's requests use their own credentials

**Local Development:**
```bash
export DATABRICKS_TOKEN='your_token_here'
python app.py
```
- App uses the environment variable
- All requests use the same token (yours)

