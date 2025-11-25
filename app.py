import os
import re
from io import StringIO
from openai import OpenAI
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix
import pandas as pd
import markdown

# Initialize the Dash app with a modern theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Expose the Flask server for production deployments (like Databricks Apps)
server = app.server

# Configure proxy support for Databricks Apps (handles X-Forwarded-* headers)
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

MODEL_NAME = "agents_akash_s_demo-talent-mobility_attrition"
BASE_URL = "https://adb-984752964297111.11.azuredatabricks.net/serving-endpoints"

# Cache client for local development (when using env var)
_cached_client = None


def get_databricks_token():
    """
    Get authentication token from various sources in priority order:
    1. Service Principal (automatic in Databricks Apps) - DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET
    2. Personal Access Token - DATABRICKS_TOKEN environment variable
    3. Databricks Secrets - as fallback
    """
    # First, try to use Service Principal (Databricks Apps automatic authentication)
    client_id = os.environ.get('DATABRICKS_CLIENT_ID')
    client_secret = os.environ.get('DATABRICKS_CLIENT_SECRET')
    
    if client_id and client_secret:
        print("✓ Using Service Principal authentication (Databricks Apps)")
        # For OAuth2 client credentials flow
        import requests
        
        # Extract workspace URL from BASE_URL
        workspace_url = BASE_URL.split('/serving-endpoints')[0]
        token_url = f"{workspace_url}/oidc/v1/token"
        
        try:
            response = requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'scope': 'all-apis'
                },
                auth=(client_id, client_secret),
                timeout=10
            )
            response.raise_for_status()
            token = response.json().get('access_token')
            if token:
                return token
        except Exception as e:
            print(f"⚠ Service Principal auth failed: {e}")
            print("  Falling back to DATABRICKS_TOKEN")
    
    # Fallback to environment variable (for local development or manual config)
    token = os.environ.get('DATABRICKS_TOKEN')
    if token:
        print("✓ Using DATABRICKS_TOKEN from environment")
        return token
    
    # Try to get from Databricks secrets
    try:
        from databricks.sdk.runtime import dbutils
        token = dbutils.secrets.get(scope="mobility-attrition", key="databricks-token")
        if token:
            print("✓ Found token in Databricks secret")
            return token
    except:
        pass
    
    return None


def get_client():
    """
    Get or create OpenAI client with proper authentication.
    
    For Databricks Apps: Automatically uses Service Principal credentials (no manual config needed!)
    For local development: Uses DATABRICKS_TOKEN environment variable
    """
    global _cached_client
    
    # Use cached client if available
    if _cached_client is not None:
        return _cached_client
    
    token = get_databricks_token()
    
    if not token:
        raise ValueError(
            "Authentication not configured. For Databricks Apps, ensure a Service Principal "
            "is configured. For local development, set DATABRICKS_TOKEN environment variable."
        )
    
    # Create OpenAI client
    client = OpenAI(
        api_key=token,
        base_url=BASE_URL,
        max_retries=2,
        timeout=60.0
    )
    
    # Cache the client
    _cached_client = client
    
    return client

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Talent Mobility & Attrition Chatbot", className="text-center my-4"),
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            # Chat history display
            dbc.Card([
                dbc.CardBody([
                    html.Div(
                        id="chat-history",
                        style={
                            "height": "500px",
                            "overflowY": "auto",
                            "padding": "20px",
                            "backgroundColor": "#f8f9fa"
                        }
                    )
                ])
            ], className="mb-3"),
            
            # Input area
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="user-input",
                                placeholder="Type your message here...",
                                type="text",
                                className="mb-2"
                            )
                        ], width=10),
                        dbc.Col([
                            dbc.Button(
                                "Send",
                                id="send-button",
                                color="primary",
                                className="w-100"
                            )
                        ], width=2)
                    ]),
                    dbc.Button(
                        "Clear Chat",
                        id="clear-button",
                        color="secondary",
                        size="sm",
                        className="mt-2"
                    )
                ])
            ])
        ], width=12, lg=8, className="mx-auto")
    ]),
    
    # Store for conversation history
    dcc.Store(id="conversation-history", data=[]),
    
    # Loading component
    dcc.Loading(
        id="loading",
        type="default",
        children=html.Div(id="loading-output")
    )
], fluid=True, className="py-4")


def get_agent_response(conversation_history):
    """Get response from the Databricks agent endpoint"""
    try:
        client = get_client()
        
        # Call the agent endpoint
        response = client.responses.create(
            model=MODEL_NAME,
            input=conversation_history
        )
        
        # Extract text from response - join with newlines to preserve structure
        response_parts = []
        for output in response.output:
            for content in getattr(output, "content", []):
                text = getattr(content, "text", "")
                if text and text.strip():
                    response_parts.append(text.strip())
        
        response_text = "\n".join(response_parts)
        
        if not response_text.strip():
            return "I received your message but got an empty response. Please try again."
        
        return response_text
        
    except ValueError as e:
        # Authentication/configuration error
        return f"Configuration Error: {str(e)}"
    except AttributeError as e:
        # Response structure error
        return f"Response Format Error: {str(e)}. The agent response format may have changed."
    except TypeError as e:
        # Type error (like the proxies issue)
        return f"Client Error: {str(e)}. Please check the OpenAI SDK version."
    except Exception as e:
        # General error with more details
        import traceback
        error_details = traceback.format_exc()
        print(f"Error calling agent: {error_details}")
        
        error_msg = str(e).lower()
        
        # Provide helpful error messages based on the error
        if "invalid scope" in error_msg or "403" in error_msg or "forbidden" in error_msg:
            return (
                f"⚠️ Permission Error: Your account doesn't have access to the agent endpoint.\n\n"
                f"To fix this:\n"
                f"1. Go to your Databricks workspace\n"
                f"2. Navigate to Serving Endpoints\n"
                f"3. Find the endpoint: {MODEL_NAME}\n"
                f"4. Grant 'Can Query' permission to your user or group\n\n"
                f"Technical details: {str(e)}"
            )
        elif "404" in error_msg or "not found" in error_msg:
            return (
                f"⚠️ Endpoint Not Found: The agent endpoint '{MODEL_NAME}' was not found.\n\n"
                f"Please verify:\n"
                f"1. The model name is correct\n"
                f"2. The endpoint exists in your workspace\n"
                f"3. The endpoint URL is correct"
            )
        elif "401" in error_msg or "unauthorized" in error_msg:
            return (
                f"⚠️ Authentication Error: The authentication token is invalid or expired.\n\n"
                f"Please check if your Databricks token is still valid."
            )
        else:
            return f"Error: {str(e)}"


def parse_markdown_table(text):
    """
    Extract markdown tables from text and convert them to pandas DataFrames.
    Returns a list of (table_df, start_pos, end_pos) tuples and the text without tables.
    """
    # More flexible pattern to match markdown tables (including those with empty first column)
    table_pattern = r'\|[^\n]*\|(?:\r?\n|\r)\|[-:\s|]+\|(?:\r?\n|\r)((?:\|[^\n]*\|(?:\r?\n|\r))+)'
    
    tables = []
    matches = list(re.finditer(table_pattern, text, re.MULTILINE))
    
    for match in matches:
        table_text = match.group(0)
        try:
            # Parse the markdown table
            lines = [line.strip() for line in table_text.strip().split('\n') if line.strip() and '|' in line]
            if len(lines) < 2:  # Need at least separator and one data row
                continue
            
            # Extract headers (first line)
            header_line = lines[0]
            headers = [h.strip() for h in header_line.split('|')]
            headers = [h for h in headers if h]  # Remove empty strings
            
            # If first column is empty or just whitespace, use "Index" or row numbers
            if not headers or headers[0] == '' or not headers[0].strip():
                headers[0] = 'Index' if len(headers) > 0 else 'Column'
            
            # Skip separator line (line with dashes)
            separator_idx = None
            for i, line in enumerate(lines):
                if re.match(r'\|[\s\-:|]+\|', line):
                    separator_idx = i
                    break
            
            if separator_idx is None:
                continue
            
            # Extract data rows (after separator)
            data = []
            for line in lines[separator_idx + 1:]:
                cells = [cell.strip() for cell in line.split('|')]
                cells = [c for c in cells if c or c == '0']  # Keep '0' but remove truly empty
                if cells:
                    # Pad or trim to match header length
                    while len(cells) < len(headers):
                        cells.append('')
                    cells = cells[:len(headers)]
                    data.append(cells)
            
            if not data:
                continue
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            tables.append((df, match.start(), match.end()))
        except Exception as e:
            print(f"Error parsing table: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Remove tables from text to get summary
    remaining_text = text
    for _, start, end in reversed(tables):
        remaining_text = remaining_text[:start] + remaining_text[end:]
    
    return tables, remaining_text.strip()


def format_response_content(content):
    """
    Format assistant response with tables and summary text.
    Returns a list of Dash components.
    """
    # Extract agent names and track which agents responded
    agent_names = re.findall(r'<name>(.*?)</name>', content)
    
    # Remove agent name tags
    content_clean = re.sub(r'<name>.*?</name>', '', content).strip()
    
    # Parse tables from the content
    tables, summary_text = parse_markdown_table(content_clean)
    
    components = []
    
    # Add agent badge if we know which agent responded
    if agent_names:
        unique_agents = list(dict.fromkeys(agent_names))  # Remove duplicates, preserve order
        if 'supervisor' not in [a.lower() for a in unique_agents]:
            badges = [
                dbc.Badge(
                    agent.replace('_', ' ').title(),
                    color="info",
                    className="me-2"
                ) for agent in unique_agents
            ]
            components.append(html.Div(badges, className="mb-2"))
    
    # Add summary text if exists
    if summary_text:
        # Split by newlines and create paragraphs
        paragraphs = [p.strip() for p in summary_text.split('\n') if p.strip()]
        if paragraphs:
            for para in paragraphs:
                components.append(html.P(para, className="mb-2"))
    
    # Add tables
    if tables:
        for df, _, _ in tables:
            # Create a styled table
            table_header = html.Thead(
                html.Tr([
                    html.Th(col, style={
                        "padding": "10px",
                        "backgroundColor": "#007bff",
                        "color": "white",
                        "fontWeight": "bold"
                    }) for col in df.columns
                ], style={"backgroundColor": "#007bff"})
            )
            
            table_rows = []
            for idx, row in df.iterrows():
                table_rows.append(
                    html.Tr([
                        html.Td(str(val), style={
                            "padding": "8px",
                            "borderBottom": "1px solid #dee2e6"
                        }) for val in row
                    ])
                )
            
            table_body = html.Tbody(table_rows)
            
            table = dbc.Table(
                [table_header, table_body],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                className="mt-3 mb-3",
                style={
                    "backgroundColor": "white",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
                }
            )
            components.append(table)
    
    # If no components were created, show the original content
    if not components:
        # If content is very short or empty, provide a default message
        if not content_clean or len(content_clean) < 5:
            components.append(html.P(
                "I processed your request. Please let me know if you need more information.",
                className="text-muted"
            ))
        else:
            components.append(html.Span(content_clean))
    
    return components


def create_message_div(role, content):
    """Create a styled message div with support for tables and formatted content"""
    if role == "user":
        return html.Div([
            html.Div([
                html.Strong("You: ", className="me-2"),
                html.Span(content)
            ], className="p-3 mb-2 rounded", 
               style={"backgroundColor": "#007bff", "color": "white", "marginLeft": "20%"})
        ])
    else:
        # Format the content (parse tables, etc.)
        formatted_content = format_response_content(content)
        
        return html.Div([
            html.Div([
                html.Strong("Assistant: ", className="me-2"),
                html.Div(formatted_content)
            ], className="p-3 mb-2 rounded",
               style={"backgroundColor": "#e9ecef", "color": "black", "marginRight": "20%"})
        ])


@app.callback(
    [Output("chat-history", "children"),
     Output("conversation-history", "data"),
     Output("user-input", "value"),
     Output("loading-output", "children")],
    [Input("send-button", "n_clicks"),
     Input("clear-button", "n_clicks"),
     Input("user-input", "n_submit")],
    [State("user-input", "value"),
     State("conversation-history", "data")]
)
def update_chat(send_clicks, clear_clicks, n_submit, user_message, conversation_history):
    """Update chat history and get agent response"""
    ctx = callback_context
    
    if not ctx.triggered:
        return [], [], "", ""
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Clear chat
    if button_id == "clear-button":
        return [], [], "", ""
    
    # Send message
    if button_id in ["send-button", "user-input"] and user_message and user_message.strip():
        # Add user message to conversation history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get agent response
        agent_response = get_agent_response(conversation_history)
        
        # Add agent response to conversation history
        conversation_history.append({
            "role": "assistant",
            "content": agent_response
        })
        
        # Create chat display
        chat_display = []
        for msg in conversation_history:
            chat_display.append(create_message_div(msg["role"], msg["content"]))
        
        return chat_display, conversation_history, "", ""
    
    # Default: just display current history
    chat_display = []
    for msg in conversation_history:
        chat_display.append(create_message_div(msg["role"], msg["content"]))
    
    return chat_display, conversation_history, "", ""


if __name__ == "__main__":
    print("=" * 60)
    print("Talent Mobility & Attrition Chatbot")
    print("=" * 60)
    
    # Check authentication setup
    has_env_token = bool(os.environ.get('DATABRICKS_TOKEN'))
    
    if has_env_token:
        print("✓ DATABRICKS_TOKEN environment variable found")
        print("  → Will use this token for local development")
    else:
        print("ℹ No DATABRICKS_TOKEN environment variable")
        print("  → Will use X-Forwarded-Access-Token header (Databricks Apps)")
    
    print("\nAuthentication mode:")
    if has_env_token:
        print("  → Local development (using environment variable)")
        try:
            get_client()
            print("  → ✓ Successfully authenticated")
        except Exception as e:
            print(f"  → ✗ Error: {e}")
    else:
        print("  → Databricks Apps (using on-behalf-of authentication)")
        print("  → Token will be validated per-request")
    
    # Get port from environment (Databricks Apps sets this)
    port = int(os.environ.get('PORT', 8050))
    
    # Disable debug mode in production (Databricks Apps)
    debug_mode = has_env_token  # Only debug in local development
    
    print("\n" + "=" * 60)
    print(f"Starting server on http://0.0.0.0:{port}")
    print(f"Debug mode: {debug_mode}")
    print("=" * 60 + "\n")
    
    app.run_server(debug=debug_mode, host="0.0.0.0", port=port)

