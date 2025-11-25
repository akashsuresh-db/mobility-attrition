import os
from openai import OpenAI
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from flask import request

# Initialize the Dash app with a modern theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

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
    
    client = OpenAI(
        api_key=token,
        base_url=BASE_URL
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
        
        return response_text
    except ValueError as e:
        # Authentication/configuration error
        return f"Configuration Error: {str(e)}"
    except Exception as e:
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
    
    print("\n" + "=" * 60)
    print(f"Starting server on http://0.0.0.0:8050")
    print("=" * 60 + "\n")
    
    app.run_server(debug=True, host="0.0.0.0", port=8050)

