# Talent Mobility & Attrition Chatbot

A simple Dash-based chatbot application that interfaces with a Databricks agent endpoint.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Databricks token:**
   ```bash
   export DATABRICKS_TOKEN='your_databricks_token_here'
   ```

   To get your Databricks token, follow: https://docs.databricks.com/en/dev-tools/auth/pat.html

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   Navigate to `http://localhost:8050`

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

