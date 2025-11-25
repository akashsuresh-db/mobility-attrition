# Deploying to Databricks Apps

## Authentication Setup - IMPORTANT! 🔐

**You MUST configure a token** for the app to access the agent endpoint.

### Why?

User OAuth tokens (X-Forwarded-Access-Token) don't have the required scopes to access serving endpoints. The app needs an **app-level token** with explicit "Can Query" permissions on the endpoint.

### Steps to Configure:

#### 1. Create a Personal Access Token (PAT)

- Go to your Databricks workspace
- Click your profile → **Settings** → **Developer**
- Click **Manage** next to Access tokens
- Click **Generate new token**
- Give it a name (e.g., "Mobility Attrition App")
- Set expiration (or choose no expiration for production)
- **Copy the token value** (you won't see it again!)

#### 2. Grant Endpoint Permissions

- Go to **Serving** → **Serving Endpoints**
- Find your endpoint: `agents_akash_s_demo-talent-mobility_attrition`
- Click on it → **Permissions** tab
- Add your user with **"Can Query"** permission
- Click **Save**

#### 3. Configure Token in Databricks App

**Option A: Environment Variable (Simpler)**

1. Go to your Databricks workspace → **Apps**
2. Select your app
3. Click **Settings** or **Environment Configuration**
4. Add Environment Variable:
   - **Key:** `DATABRICKS_TOKEN`
   - **Value:** Paste your PAT from step 1
5. **Save** and **Redeploy** the app

**Option B: Databricks Secrets (More Secure)**

1. Create a secret scope:
   ```bash
   databricks secrets create-scope --scope mobility-attrition
   ```

2. Store your token:
   ```bash
   databricks secrets put --scope mobility-attrition --key databricks-token
   ```
   (Paste your PAT when prompted)

3. The app will automatically read from this secret

### For Local Development

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
   - **Add DATABRICKS_TOKEN environment variable** (see Authentication Setup above)

3. **Deploy:**
   - Click **Deploy**
   - Monitor the logs for any errors
   - The app will use the configured token to access the agent endpoint

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
2. App reads `DATABRICKS_TOKEN` from environment variable or secret
3. App uses this app-level token to authenticate API calls to the serving endpoint
4. All users share the same backend token (but can be individually authenticated at the app level if needed)

**Local Development:**
```bash
export DATABRICKS_TOKEN='your_token_here'
python app.py
```
- App uses the environment variable
- All requests use the same token (yours)

**Note:** We use an app-level token instead of per-user tokens because user OAuth tokens don't have the required scopes to access serving endpoints. This is a Databricks platform limitation.

