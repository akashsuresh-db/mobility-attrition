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
    
    In Databricks Apps, this uses the X-Forwarded-Access-Token header
    which contains the user's access token (on-behalf-of authentication).
    
    For local development, falls back to DATABRICKS_TOKEN environment variable.
    """
    global _cached_client
    
    token = None
    use_cache = False
    
    # First, try to get token from Databricks Apps HTTP headers
    # This header is automatically set by Databricks Apps with the user's token
    try:
        if request:
            token = request.headers.get('X-Forwarded-Access-Token')
            if token:
                # Don't cache when using per-request tokens
                use_cache = False
    except RuntimeError:
        # Not in a request context (e.g., during startup)
        pass
    
    # Fall back to environment variable for local development
    if not token:
        token = os.environ.get('DATABRICKS_TOKEN')
        use_cache = True  # Cache when using env var
    
    # If we're using cache and have a cached client, return it
    if use_cache and _cached_client is not None:
        return _cached_client
    
    if not token:
        raise ValueError(
            "Authentication not configured. For Databricks Apps, ensure the app has access to user tokens. "
            "For local development, set DATABRICKS_TOKEN environment variable."
        )
    
    # Create OpenAI client with explicit settings to avoid proxy issues
    client = OpenAI(
        api_key=token,
        base_url=BASE_URL,
        max_retries=2,
        timeout=60.0
    )
    
    # Cache if using env var
    if use_cache:
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

