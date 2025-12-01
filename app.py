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

# Initialize the Dash app with a dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# Expose the Flask server for production deployments (like Databricks Apps)
server = app.server

# Configure proxy support for Databricks Apps (handles X-Forwarded-* headers)
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

MODEL_NAME = "agents_akash_s_demo-talent-talent_agent_v1"
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


def get_client(user_token=None):
    """
    Get or create OpenAI client with proper authentication.
    
    Args:
        user_token: Optional user's access token from X-Forwarded-Access-Token header.
                    If provided, uses user's token for OBO. If not, falls back to app token.
    
    For Databricks Apps with OBO: Pass user token from request headers
    For Databricks Apps without OBO: Uses Service Principal credentials
    For local development: Uses DATABRICKS_TOKEN environment variable
    """
    global _cached_client
    
    # If user token provided, create a new client (don't cache - each user is different!)
    if user_token:
        return OpenAI(
            api_key=user_token,
            base_url=BASE_URL
        )
    
    # Use cached client if available (for app token)
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
                            "backgroundColor": "#1a1a1a"
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


def get_agent_response(conversation_history, user_token=None):
    """
    Get response from the Databricks agent endpoint.
    
    Args:
        conversation_history: List of conversation messages
        user_token: Optional user's access token for OBO. If provided, agent will
                    execute queries on behalf of the user (RLS enforced).
    """
    try:
        client = get_client(user_token=user_token)
        
        # Call the agent endpoint
        print(f"Calling agent with history: {len(conversation_history)} messages")
        response = client.responses.create(
            model=MODEL_NAME,
            input=conversation_history
        )
        
        # Debug: Print raw response structure
        print(f"Response object type: {type(response)}")
        print(f"Response output: {response.output if hasattr(response, 'output') else 'No output attr'}")
        
        # Extract text from response - join with newlines to preserve structure
        response_parts = []
        for output in response.output:
            print(f"Output type: {type(output)}, Output: {output}")
            for content in getattr(output, "content", []):
                print(f"Content type: {type(content)}, Content: {content}")
                text = getattr(content, "text", "")
                print(f"Extracted text: '{text}'")
                if text and text.strip():
                    response_parts.append(text.strip())
        
        response_text = "\n".join(response_parts)
        print(f"Final response text length: {len(response_text)}")
        print(f"Final response text: '{response_text}'")
        
        if not response_text.strip():
            return "⚠️ I received your message but got an empty response from the agent. This could mean:\n\n1. The agent endpoint is running but not processing queries correctly\n2. There might be an issue with the data sources or permissions\n3. The query might need to be rephrased\n\nPlease try rephrasing your question or check the agent endpoint logs."
        
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
    tables = []
    
    # Try multiple table patterns
    patterns = [
        # Standard markdown with pipes: | col1 | col2 |
        r'\|[^\n]*\|(?:\r?\n|\r)\|[-:\s|]+\|(?:\r?\n|\r)((?:\|[^\n]*\|(?:\r?\n|\r))+)',
        # Tab-separated or space-separated with header and separator
        r'([^\n]+\t[^\n]+(?:\r?\n|\r)[-:\s\t]+(?:\r?\n|\r)(?:[^\n]+\t[^\n]+(?:\r?\n|\r))+)',
    ]
    
    # Try pipe-delimited tables first
    pipe_pattern = patterns[0]
    matches = list(re.finditer(pipe_pattern, text, re.MULTILINE))
    
    print(f"DEBUG parse_markdown_table - Found {len(matches)} potential pipe tables")
    
    for match in matches:
        table_text = match.group(0)
        print(f"DEBUG parse_markdown_table - Processing table text:\n{table_text[:200]}")
        try:
            lines = [line.strip() for line in table_text.strip().split('\n') if line.strip() and '|' in line]
            print(f"DEBUG parse_markdown_table - Extracted {len(lines)} lines from table")
            if len(lines) < 2:
                print(f"DEBUG parse_markdown_table - Skipping: too few lines")
                continue
            
            # Find separator line (must contain dashes, not just spaces)
            separator_idx = None
            for i, line in enumerate(lines):
                # Separator line must have pipes and dashes
                if '|' in line and '-' in line:
                    # Check if line is only separators (|, -, :, spaces)
                    cleaned = line.replace('|', '').replace('-', '').replace(':', '').replace(' ', '').replace('\t', '')
                    if not cleaned:
                        separator_idx = i
                        print(f"DEBUG parse_markdown_table - Found separator at line {i}: {line}")
                        break
            
            if separator_idx is None:
                print(f"DEBUG parse_markdown_table - Skipping: no separator found")
                continue
            if separator_idx == 0:
                print(f"DEBUG parse_markdown_table - Skipping: separator at index 0")
                continue
            
            # Extract headers - strip empty leading/trailing cells
            header_line = lines[separator_idx - 1] if separator_idx > 0 else lines[0]
            raw_headers = [h.strip() for h in header_line.split('|')]
            
            # Remove empty cells from start and end
            while raw_headers and raw_headers[0] == '':
                raw_headers.pop(0)
            while raw_headers and raw_headers[-1] == '':
                raw_headers.pop()
            
            headers = raw_headers
            if not headers:
                continue
            
            num_cols = len(headers)
            print(f"DEBUG parse_markdown_table - Parsed {num_cols} headers: {headers}")
            
            # Extract data rows - dynamically handle any number of columns
            data = []
            print(f"DEBUG parse_markdown_table - Processing {len(lines) - separator_idx - 1} data rows")
            for row_idx, line in enumerate(lines[separator_idx + 1:]):
                raw_cells = [cell.strip() for cell in line.split('|')]
                print(f"DEBUG parse_markdown_table - Row {row_idx}: raw_cells = {raw_cells}")
                
                # Remove empty cells from start and end
                while raw_cells and raw_cells[0] == '':
                    raw_cells.pop(0)
                while raw_cells and raw_cells[-1] == '':
                    raw_cells.pop()
                
                print(f"DEBUG parse_markdown_table - Row {row_idx}: after cleanup = {raw_cells} (len={len(raw_cells)} vs headers={num_cols})")
                
                if not raw_cells:
                    print(f"DEBUG parse_markdown_table - Row {row_idx}: skipping empty row")
                    continue
                
                # Smart column extraction:
                # If we have MORE cells than headers, check if first cell is a pandas index
                if len(raw_cells) > num_cols:
                    # Check if first cell looks like a pandas index (only digits)
                    if raw_cells[0].isdigit():
                        # Skip the index, take the rest
                        cells = raw_cells[1:num_cols+1]
                        print(f"DEBUG parse_markdown_table - Row {row_idx}: detected pandas index, cells = {cells}")
                    else:
                        # Take first N columns
                        cells = raw_cells[:num_cols]
                        print(f"DEBUG parse_markdown_table - Row {row_idx}: taking first {num_cols} cells = {cells}")
                elif len(raw_cells) == num_cols:
                    # Perfect match
                    cells = raw_cells
                    print(f"DEBUG parse_markdown_table - Row {row_idx}: perfect match, cells = {cells}")
                else:
                    # Fewer cells than headers - pad with empty strings
                    cells = raw_cells + [''] * (num_cols - len(raw_cells))
                    print(f"DEBUG parse_markdown_table - Row {row_idx}: padded cells = {cells}")
                
                # Ensure we have exactly the right number of columns
                cells = cells[:num_cols]
                while len(cells) < num_cols:
                    cells.append('')
                
                # Skip rows with all empty values
                if cells and any(c for c in cells):
                    data.append(cells)
                    print(f"DEBUG parse_markdown_table - Row {row_idx}: ✅ added to data")
                else:
                    print(f"DEBUG parse_markdown_table - Row {row_idx}: ❌ skipped (all empty)")
            
            print(f"DEBUG parse_markdown_table - Extracted {len(data)} data rows")
            if data:
                df = pd.DataFrame(data, columns=headers)
                print(f"DEBUG parse_markdown_table - ✅ Successfully parsed table with {len(df)} rows and {len(df.columns)} columns")
                print(f"DEBUG parse_markdown_table - Columns: {df.columns.tolist()}")
                print(f"DEBUG parse_markdown_table - Sample rows: {data[:2]}")
                tables.append((df, match.start(), match.end()))
            else:
                print(f"DEBUG parse_markdown_table - ❌ No data rows extracted from table")
                
        except Exception as e:
            print(f"Error parsing pipe table: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Try tab-separated format: column1\tcolumn2\n---:---\nval1\tval2
    tab_pattern = r'([^\n\|]+\t[^\n\|]+)\s*\n\s*([:-]+\s+[:-]+.*?)\s*\n((?:[^\n\|]+\t[^\n\|]+\s*\n?)+)'
    tab_matches = list(re.finditer(tab_pattern, text, re.MULTILINE))
    
    for match in tab_matches:
        try:
            header_line = match.group(1).strip()
            data_lines = match.group(3).strip().split('\n')
            
            headers = [h.strip() for h in header_line.split('\t') if h.strip()]
            if not headers:
                continue
            
            data = []
            for line in data_lines:
                if line.strip():
                    cells = [c.strip() for c in line.split('\t')]
                    if len(cells) == len(headers):
                        data.append(cells)
            
            if data:
                df = pd.DataFrame(data, columns=headers)
                tables.append((df, match.start(), match.end()))
                
        except Exception as e:
            print(f"Error parsing tab table: {e}")
            continue
    
    # Remove tables from text to get summary
    remaining_text = text
    for _, start, end in reversed(sorted(tables, key=lambda x: x[1])):
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
    
    # Remove common unhelpful phrases
    content_clean = re.sub(r'\bEMPTY\b', '', content_clean, flags=re.IGNORECASE)
    
    # Parse tables from the content (BEFORE normalizing whitespace to preserve table structure)
    tables, summary_text = parse_markdown_table(content_clean)
    
    # Debug logging
    print(f"DEBUG format_response - Found {len(tables)} tables")
    print(f"DEBUG format_response - Summary text length: {len(summary_text)}")
    print(f"DEBUG format_response - Summary text: '{summary_text}'")
    print(f"DEBUG format_response - Content clean preview: {content_clean[:300]}")
    
    # Now normalize whitespace in the summary text only (not the whole content with tables)
    summary_text = re.sub(r'[ \t]+', ' ', summary_text).strip()  # Normalize spaces/tabs but keep newlines
    
    components = []
    
    # Add agent badge if we know which agent responded
    if agent_names:
        unique_agents = list(dict.fromkeys(agent_names))  # Remove duplicates, preserve order
        # Filter out supervisor and show only actual worker agents
        worker_agents = [a for a in unique_agents if 'supervisor' not in a.lower()]
        if worker_agents:
            badges = [
                dbc.Badge(
                    agent.replace('_', ' ').title(),
                    color="info",
                    className="me-2",
                    style={"fontSize": "0.85em"}
                ) for agent in worker_agents
            ]
            components.append(html.Div(badges, className="mb-2"))
    
    # Add summary text if exists (and it's meaningful)
    if summary_text:
        # Split by newlines and create paragraphs
        paragraphs = [p.strip() for p in summary_text.split('\n') if p.strip() and len(p.strip()) > 3]
        print(f"DEBUG format_response - Found {len(paragraphs)} paragraphs in summary")
        if paragraphs:
            for idx, para in enumerate(paragraphs):
                print(f"DEBUG format_response - Paragraph {idx}: {para[:100]}")
                # Skip if it looks like table remnants
                if not re.match(r'^[-:\s|]+$', para) and '|' not in para[:10]:
                    components.append(html.P(para, className="mb-2"))
                    print(f"DEBUG format_response - ✅ Added paragraph {idx}")
                else:
                    print(f"DEBUG format_response - ❌ Skipped paragraph {idx} (table remnant)")
    
    # Add tables - only show the LAST table (from supervisor_summarizer, not duplicates from genie)
    if tables:
        print(f"DEBUG format_response - Processing {len(tables)} tables for display")
        
        # Only use the last table if we have duplicates
        tables_to_display = [tables[-1]] if len(tables) > 1 else tables
        print(f"DEBUG format_response - Displaying {len(tables_to_display)} table(s) (last one only)")
        
        for table_idx, (df, _, _) in enumerate(tables_to_display):
            print(f"DEBUG format_response - Table {table_idx}: {len(df)} rows, {len(df.columns)} cols")
            # Skip tables with no meaningful data
            if df.empty or len(df) == 0:
                print(f"DEBUG format_response - ❌ Skipping table {table_idx}: empty")
                continue
            
            # Check if table has any non-empty values
            has_data = False
            for col in df.columns:
                if df[col].notna().any() and (df[col] != '').any():
                    has_data = True
                    break
            
            if not has_data:
                print(f"DEBUG format_response - ❌ Skipping table {table_idx}: no data")
                continue
            
            print(f"DEBUG format_response - ✅ Adding table {table_idx} to display")
            # Create a styled table
            table_header = html.Thead(
                html.Tr([
                    html.Th(col, style={
                        "padding": "10px",
                        "backgroundColor": "#0d6efd",
                        "color": "white",
                        "fontWeight": "bold",
                        "textAlign": "left"
                    }) for col in df.columns
                ], style={"backgroundColor": "#0d6efd"})
            )
            
            table_rows = []
            for idx, row in df.iterrows():
                # Create cells with better formatting
                cells = []
                for val in row:
                    # Clean up cell value
                    cell_val = str(val).strip()
                    if cell_val in ['', 'nan', 'None']:
                        cell_val = '—'  # Em dash for empty values
                    
                    cells.append(
                        html.Td(cell_val, style={
                            "padding": "8px",
                            "borderBottom": "1px solid #495057",
                            "textAlign": "left",
                            "color": "#e9ecef"
                        })
                    )
                table_rows.append(html.Tr(cells))
            
            table_body = html.Tbody(table_rows)
            
            table = dbc.Table(
                [table_header, table_body],
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                size="sm",
                className="mt-3 mb-3",
                dark=True,
                style={
                    "backgroundColor": "#212529",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.3)",
                    "borderRadius": "4px",
                    "overflow": "hidden"
                }
            )
            components.append(table)
    
    # If no components were created, show the original content
    if not components:
        # If content is very short or empty, provide a default message
        if not content_clean or len(content_clean) < 5:
            components.append(html.P(
                "⚠️ The agent returned an empty or incomplete response. Please try rephrasing your question.",
                className="text-muted"
            ))
        # Check if it's just a header with no content
        elif content_clean.startswith('**') and len(content_clean) < 50:
            components.append(html.Div([
                html.P(content_clean, className="mb-2"),
                html.P(
                    "⚠️ The agent acknowledged your request but didn't provide a complete answer. "
                    "This might indicate an issue with the agent configuration or data access.",
                    className="text-warning small"
                )
            ]))
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
               style={"backgroundColor": "#0d6efd", "color": "white", "marginLeft": "20%"})
        ])
    else:
        # Format the content (parse tables, etc.)
        formatted_content = format_response_content(content)
        
        return html.Div([
            html.Div([
                html.Strong("Assistant: ", className="me-2"),
                html.Div(formatted_content)
            ], className="p-3 mb-2 rounded",
               style={"backgroundColor": "#2d3238", "color": "#e9ecef", "marginRight": "20%"})
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
        
        # Get user's token from request headers (for OBO authentication)
        # This allows the agent to execute queries on behalf of the user
        user_token = request.headers.get('X-Forwarded-Access-Token')
        
        # Get user's email for logging
        user_email = request.headers.get('X-Forwarded-Email', 'unknown')
        print(f"Processing request for user: {user_email}")
        print(f"Using OBO token: {'Yes' if user_token else 'No (fallback to app token)'}")
        
        # TEMPORARY: Disable OBO for testing (use app token instead)
        # TODO: Enable OBO after adding 'serving.serving-endpoints' scope in app settings
        use_obo = False  # Set to True after adding scope
        
        # Get agent response with user's token (if OBO enabled)
        agent_response = get_agent_response(
            conversation_history, 
            user_token=user_token if use_obo else None
        )
        
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

