from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create the app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Local Chat"

# Layout
app.layout = dbc.Container([
    html.H2("💬 Local Chat", className="text-center mt-3"),

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
        dbc.Input(id="user-input", placeholder="Type a message...", type="text"),
        dbc.Button("Send", id="send-button", n_clicks=0, color="primary")
    ], className="mt-3"),

    dcc.Store(id="memory", data=[])
], fluid=True)

# Callbacks
@app.callback(
    Output("chat-history", "children"),
    Output("memory", "data"),
    Input("send-button", "n_clicks"),
    State("user-input", "value"),
    State("memory", "data"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_message, history):
    if not user_message:
        return [html.Div(""), history]

    # Append user message
    history.append(("You", user_message))

    # (Optional) Simple AI echo or bot response

    response = client.models.generate_content(model="gemini-2.5-flash", contents="Explain how AI works in a few words")
    print(response.text)
    
    bot_response = f"Echo: {response.text}"
    history.append(("Bot", bot_response))

    # Format chat
    chat_display = []
    for sender, msg in history:
        align = "left" if sender == "Bot" else "right"
        color = "#5bc0de" if sender == "Bot" else "#f0ad4e"
        chat_display.append(
            html.Div([
                html.Span(f"{sender}: ", style={"color": color, "fontWeight": "bold"}),
                html.Span(msg)
            ], style={"textAlign": align, "margin": "4px"})
        )

    return chat_display, history

if __name__ == "__main__":
    app.run(debug=True)
