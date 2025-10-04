import os
import json
import requests
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import snowflake.connector  # ✅ added for connecting to Snowflake directly
from dotenv import load_dotenv

# -----------------------
# Configuration / credentials
# -----------------------

load_dotenv()

# These environment variables or secrets should be set beforehand
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_API_KEY = os.getenv("SNOWFLAKE_API_KEY")  # your Snowflake password or API key
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")  # default role if not provided
SNOWFLAKE_HOST = os.getenv("SNOWFLAKE_HOST")


print("user",SNOWFLAKE_USER)
print("account", SNOWFLAKE_ACCOUNT)
print("key", SNOWFLAKE_API_KEY)
print("role", SNOWFLAKE_ROLE)
print("host", SNOWFLAKE_HOST)

API_ENDPOINT = "/api/v2/cortex/inference:complete"
API_TIMEOUT = 50000
MODEL_NAME = "claude-3-5-sonnet"  # or llama3.1-70b, mistral-large2, etc.

# -----------------------
# Helper: connect to Snowflake and call LLM (non-streaming)
# -----------------------

def get_snowflake_connection():
    """Connects to Snowflake using connector; returns a live connection."""
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_API_KEY,
            account=SNOWFLAKE_ACCOUNT,
            host=SNOWFLAKE_HOST,
            port=443,
            role=SNOWFLAKE_ROLE
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Snowflake: {e}")


def call_snowflake_llm(messages, model=MODEL_NAME, temperature=0.0, max_tokens=300):
    """
    Sends a full POST request (non-streaming) to Snowflake Cortex LLM endpoint.
    """
    conn = get_snowflake_connection()
    token = conn.rest.token  # ✅ reuse the REST token from an authenticated connection

    headers = {
        "Authorization": f'Snowflake Token="{token}"',
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    # ✅ Non-streaming request (waits for full response)
    resp = requests.post(
        f"https://{SNOWFLAKE_HOST}{API_ENDPOINT}",
        headers=headers,
        json=payload,
        timeout=60
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Snowflake API error {resp.status_code}: {resp.text}")

    data = resp.json()
    # ✅ Extract the model’s text response (same structure as Streamlit example)
    content = data["choices"][0]["message"]["content"]
    conn.close()
    return content


# -----------------------
# Dash app
# -----------------------

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Snowflake Chat"

app.layout = dbc.Container([
    html.H2("💬 Chat with Snowflake LLM", className="text-center mt-3"),

    dbc.Card([
        dbc.CardBody([
            html.Div(id="chat-history", style={
                "height": "400px",
                "overflowY": "auto",
                "backgroundColor": "#1e1e1e",
                "padding": "10px",
                "borderRadius": "10px",
                "whiteSpace": "pre-wrap"
            }),
        ])
    ], className="mt-3"),

    dbc.InputGroup([
        dbc.Input(id="user-input", placeholder="Type your message...", type="text"),
        dbc.Button("Send", id="send-button", n_clicks=0, color="primary")
    ], className="mt-3"),

    dcc.Store(id="chat-memory", data=[])
], fluid=True)


@app.callback(
    Output("chat-history", "children"),
    Output("chat-memory", "data"),
    Input("send-button", "n_clicks"),
    State("user-input", "value"),
    State("chat-memory", "data"),
    prevent_initial_call=True
)
def on_user_send(n_clicks, user_text, memory):
    if not user_text or user_text.strip() == "":
        return dash.no_update, memory

    # Add user message
    memory.append({"role": "user", "content": user_text})

    # Call Snowflake LLM (non-streaming)
    try:
        assistant_text = call_snowflake_llm(memory)
    except Exception as e:
        assistant_text = f"Error: {e}"

    # Add assistant message
    memory.append({"role": "assistant", "content": assistant_text})

    # Build formatted chat
    display = []
    for msg in memory:
        sender = msg["role"]
        content = msg["content"]
        align = "right" if sender == "user" else "left"
        color = "#f0ad4e" if sender == "user" else "#5bc0de"
        display.append(
            html.Div([
                html.Span(f"{sender}: ", style={"fontWeight": "bold", "color": color}),
                html.Span(content)
            ], style={"textAlign": align, "margin": "4px"})
        )

    return display, memory


if __name__ == "__main__":
    app.run(debug=True)