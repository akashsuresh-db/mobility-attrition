# Talent Mobility & Attrition Chatbot

A simple Dash-based chatbot application that interfaces with a Databricks agent endpoint.

## Setup

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Databricks token:**
   ```bash
   export DATABRICKS_TOKEN='your_databricks_token_here'
   ```

   To get your Databricks token, follow: https://docs.databricks.com/en/dev-tools/auth/pat.html

3. **Test your authentication (optional but recommended):**
   ```bash
   python test_auth.py
   ```

   This will verify your token is valid and the endpoint is accessible.

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   Navigate to `http://localhost:8050`

### Deploying to Databricks Apps

The app uses **automatic on-behalf-of-user authentication** in Databricks Apps - no manual token configuration needed! 

Simply deploy your app to Databricks Apps and it will automatically authenticate using each user's credentials via the `X-Forwarded-Access-Token` header.

See [DATABRICKS_APPS_SETUP.md](DATABRICKS_APPS_SETUP.md) for detailed deployment instructions and troubleshooting.

## Features

- Clean, modern chat interface using Dash Bootstrap Components
- Real-time conversation with the Databricks agent endpoint
- Conversation history maintained during the session
- Clear chat functionality to start fresh
- Responsive design that works on different screen sizes
- Loading indicator while waiting for agent responses

## Usage

1. Type your message in the input box
2. Click "Send" or press Enter to submit
3. Wait for the agent's response
4. Continue the conversation - the full history is sent to the agent
5. Click "Clear Chat" to start a new conversation

## Configuration

You can modify the following in `app.py`:
- `MODEL_NAME`: Change to your specific agent model name
- `base_url`: Update if using a different Databricks workspace
- Port and host settings in `app.run_server()`

