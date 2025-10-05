from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
from responseTextAudio import generate_text_and_audio

# Create the app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "Fate Weaver"

# Layout
app.layout = dbc.Container([
    dbc.Row([
        # Left Column - 35% for vertically centered image
        html.H1("Fate Weaver", className="text-center mt-3"),
        dbc.Col([
            html.Div(
                html.Img(
                    src="https://plus.unsplash.com/premium_photo-1664474619075-644dd191935f?fm=jpg&q=60&w=3000&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MXx8aW1hZ2V8ZW58MHx8MHx8fDA%3D",
                    style={
                        "width": "100%",
                        "height": "auto",
                        "borderRadius": "10px",
                        "display": "block"
                    }
                ),
                style={
                    "height": "100%",
                    "display": "flex",
                    "alignItems": "center",      # vertical center
                    "justifyContent": "center"   # horizontal center
                }
            )
        ], width=4, style={"minHeight": "100vh"}),

        # Right Column - 65% chat
        dbc.Col([
            html.Div([
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
                ], className="mt-3", style={"width": "100%"}),

                dbc.InputGroup([
                    dbc.Input(id="user-input", placeholder="Type a message...", type="text"),
                    dbc.Button("Send", id="send-button", n_clicks=0, color="primary")
                ], className="mt-3"),

                html.Audio(id="audio-player", controls=False, autoPlay=True),
                dcc.Store(id="memory", data=[])
            ], style={
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",        # horizontal center
                "justifyContent": "flex-start",# top align
                "height": "100%",
                "width": "100%"
            })
        ], width=8)
    ], style={"height": "100vh"})  # full viewport height for row
], fluid=True)

# Callbacks
@app.callback(
    Output("chat-history", "children"),
    Output("memory", "data", allow_duplicate=True),
    Output("audio-player", "src"), 
    Output("user-input", "value"),
    Input("send-button", "n_clicks"),
    State("user-input", "value"),
    State("memory", "data"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_message, history):
    if not user_message:
        return [html.Div("")], history, None, ""

    # Append user message
    history.append(("You", user_message))

    # Generate bot response + audio
    result = generate_text_and_audio(user_message, history, audio_cache_dir="assets")
    history.append((result["speaker"], result["text"]))

    # Format chat
    chat_display = []
    for sender, msg in history:
        align = "left" if sender != "You" else "right"
        color = "#5bc0de" if sender == "Bot" else "#f0ad4e"
        chat_display.append(
            html.Div([
                html.Span(f"{sender}: ", style={"color": color, "fontWeight": "bold"}),
                html.Span(msg)
            ], style={"textAlign": align, "margin": "4px"})
        )
    
    audio_src = "/" + result["audio_path"].replace("\\", "/") if os.path.exists(result["audio_path"]) else None

    return chat_display, history, audio_src, ""

# Client-side callback to play audio automatically
app.clientside_callback(
    """
    function(src, history) {
        if(src){
            var audio = document.getElementById('audio-player');
            audio.load();
            audio.play();
        }
        return history;
    }
    """,
    Output("memory", "data", allow_duplicate=True),  # dummy output
    Input("audio-player", "src"),
    State("memory", "data"),
    prevent_initial_call=True
)

if __name__ == "__main__":
    app.run(port=8050, debug=True)
