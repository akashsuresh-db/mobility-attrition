import os
from openai import OpenAI
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix

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


def get_client():
    """
    Get or create OpenAI client with proper authentication.
    
    For Databricks Apps: Uses DATABRICKS_TOKEN from environment variable or secret.
    This should be a service principal token or PAT with serving endpoint access.
    
    For local development: Falls back to DATABRICKS_TOKEN environment variable.
    
    Note: User tokens from X-Forwarded-Access-Token don't have the required OAuth
    scopes to access serving endpoints, so we use an app-level token instead.
    """
    global _cached_client
    
    # Use cached client if available (token doesn't change per request for serving endpoints)
    if _cached_client is not None:
        return _cached_client
    
    token = None
    
    # Try to get token from environment variable (works in both local and Databricks Apps)
    token = os.environ.get('DATABRICKS_TOKEN')
    
    # Try to get from Databricks secrets if available (for Databricks Apps)
    if not token:
        try:
            # Try common secret scopes
            from databricks.sdk.runtime import dbutils
            secret_scopes = ["mobility-attrition", "app-secrets", "default"]
            for scope in secret_scopes:
                try:
                    token = dbutils.secrets.get(scope=scope, key="databricks-token")
                    if token:
                        print(f"✓ Found token in secret scope: {scope}")
                        break
                except:
                    continue
        except Exception as e:
            print(f"Could not access Databricks secrets: {e}")
            pass
    
    if not token:
        raise ValueError(
            "Authentication not configured. Set DATABRICKS_TOKEN as an environment variable "
            "in your Databricks App configuration. This should be a service principal token "
            "or personal access token with 'Can Query' permission on the serving endpoint."
        )
    
    # Create OpenAI client with explicit settings
    client = OpenAI(
        api_key=token,
        base_url=BASE_URL,
        max_retries=2,
        timeout=60.0
    )
    
    # Cache the client
    _cached_client = client
    
    return client

# Check if token is configured
def check_token_configured():
    """Check if DATABRICKS_TOKEN is available"""
    token = os.environ.get('DATABRICKS_TOKEN')
    if token:
        return True
    
    # Check secrets
    try:
        from databricks.sdk.runtime import dbutils
        for scope in ["mobility-attrition", "app-secrets", "default"]:
            try:
                token = dbutils.secrets.get(scope=scope, key="databricks-token")
                if token:
                    return True
            except:
                continue
    except:
        pass
    
    return False

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Talent Mobility & Attrition Chatbot", className="text-center my-4"),
        ])
    ]),
    
    # Configuration status banner
    dbc.Row([
        dbc.Col([
            html.Div(id="config-status-banner", className="mb-3")
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
        
        # Extract text from response
        response_text = " ".join(
            getattr(content, "text", "") 
            for output in response.output 
            for content in getattr(output, "content", [])
        )
        
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


def create_message_div(role, content):
    """Create a styled message div"""
    if role == "user":
        return html.Div([
            html.Div([
                html.Strong("You: ", className="me-2"),
                html.Span(content)
            ], className="p-3 mb-2 rounded", 
               style={"backgroundColor": "#007bff", "color": "white", "marginLeft": "20%"})
        ])
    else:
        return html.Div([
            html.Div([
                html.Strong("Assistant: ", className="me-2"),
                html.Span(content)
            ], className="p-3 mb-2 rounded",
               style={"backgroundColor": "#e9ecef", "color": "black", "marginRight": "20%"})
        ])


@app.callback(
    Output("config-status-banner", "children"),
    Input("config-status-banner", "id")
)
def update_config_status(_):
    """Display configuration status banner"""
    is_configured = check_token_configured()
    
    if is_configured:
        # Show success banner
        return dbc.Alert([
            html.I(className="bi bi-check-circle-fill me-2"),
            html.Strong("✓ Configuration OK"),
            " - The app is properly configured and ready to use."
        ], color="success", className="mb-0", dismissable=True)
    else:
        # Show warning banner with setup instructions
        return dbc.Alert([
            html.H5([
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                "⚠️ Configuration Required"
            ], className="alert-heading"),
            html.Hr(),
            html.P([
                "The app needs a ", html.Strong("DATABRICKS_TOKEN"), " to access the agent endpoint."
            ]),
            html.P("To fix this:", className="mb-2"),
            html.Ol([
                html.Li([
                    html.Strong("Create a Personal Access Token: "),
                    "Go to your Databricks workspace → Your Profile → Settings → Developer → Generate new token"
                ]),
                html.Li([
                    html.Strong("Grant endpoint permissions: "),
                    f"Go to Serving → Serving Endpoints → {MODEL_NAME} → Permissions → Grant your user 'Can Query' permission"
                ]),
                html.Li([
                    html.Strong("Configure the token: "),
                    "In your Databricks App settings, add an environment variable with Key: ",
                    html.Code("DATABRICKS_TOKEN"),
                    " and Value: your token"
                ]),
                html.Li([
                    html.Strong("Redeploy the app"),
                    " to apply the changes"
                ])
            ], className="mb-2"),
            html.P([
                "See ",
                html.A("DATABRICKS_APPS_SETUP.md", 
                       href="https://github.com/akashsuresh-db/mobility-attrition/blob/main/DATABRICKS_APPS_SETUP.md",
                       target="_blank"),
                " for detailed instructions."
            ], className="mb-0")
        ], color="warning", className="mb-0")


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
        # Show welcome message on initial load
        welcome_msg = []
        if check_token_configured():
            welcome_msg = [
                create_message_div("assistant", 
                    "👋 Hello! I'm your Talent Mobility & Attrition assistant. "
                    "I can help you analyze attrition patterns, mobility trends, and workforce insights. "
                    "Ask me anything about your organization's talent data!"
                )
            ]
        else:
            welcome_msg = [
                create_message_div("assistant",
                    "⚠️ Welcome! I'm ready to help with talent mobility and attrition insights, "
                    "but the app needs to be configured first. "
                    "Please see the yellow banner above for setup instructions."
                )
            ]
        return welcome_msg, [], "", ""
    
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

