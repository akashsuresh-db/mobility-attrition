# Talent Mobility & Attrition Chatbot

A Dash-based chatbot application that interfaces with a Databricks agent endpoint.

## Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Databricks token:**
   ```bash
   export DATABRICKS_TOKEN='your_databricks_token_here'
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:8050`

### Deploying to Databricks Apps

1. **Create a Personal Access Token** in Databricks
2. **Grant "Can Query" permission** on the serving endpoint to your user
3. **Add DATABRICKS_TOKEN** as an environment variable in your Databricks App
4. **Deploy** the app

The app will show a configuration banner if the token is not set.

## Features

- ✅ Clean chat interface with conversation history
- ✅ Automatic configuration detection
- ✅ Helpful setup guidance in the UI
- ✅ Error handling with actionable messages
- ✅ Works in both local and Databricks Apps environments

## Configuration

The app requires `DATABRICKS_TOKEN` to be set either as:
- Environment variable
- Databricks secret (in scopes: `mobility-attrition`, `app-secrets`, or `default`)

## Documentation

- Setup guide and troubleshooting information are shown in the app UI
- Configuration status banner appears automatically

## Model Configuration

Update these in `app.py` if your endpoint details differ:
- `MODEL_NAME`: Your agent endpoint name
- `BASE_URL`: Your Databricks workspace serving endpoints URL

