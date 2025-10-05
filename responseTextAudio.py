# responseTextAudio.py
from __future__ import annotations
import os
import json
import base64
from pathlib import Path
from typing import List, Tuple, Dict, Any

from dotenv import load_dotenv
from google import genai

# TTS helper (uses Eleven v3 Alpha inside your tts.py)
from tts import synthesize_line_mp3

# ---------- Setup ----------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in environment (.env).")

client = genai.Client(api_key=GEMINI_API_KEY)

# Role text (we'll prepend this into the prompt since system_instruction isn't supported here)
ROLE = (
    "SYSTEM ROLE:\n"
    "You are an AI assistant that provides direct answers only—no reasoning steps.\n"
    "ROLEPLAY as the game engine: respond with a single line of dialogue or a concise event narration.\n"
    "Use bracketed direction when helpful, e.g., Narrator: [somber] The bells toll.\n"
    "Pick the most appropriate SPEAKER from the provided characters or 'Narrator'.\n"
    "Keep responses concise and in-world.\n"
)

# ---------- World data ----------
CHAR_PATH = Path("characters.json")
SET_PATH  = Path("setting.json")

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

CHARACTERS: List[Dict[str, Any]] = _load_json(CHAR_PATH) or []
SETTINGS: Dict[str, Any] = _load_json(SET_PATH) or {}

CHAR_NAMES = [c.get("name") for c in CHARACTERS if c.get("name")]
LOCATION_IDS: List[str] = []
for loc in (SETTINGS.get("locations") or []):
    if loc.get("id"):
        LOCATION_IDS.append(loc["id"])
    for sub in (loc.get("sublocations") or []):
        if sub.get("id"):
            LOCATION_IDS.append(sub["id"])

# Schema prompt to force strict JSON
RESPONSE_SCHEMA = (
    "Return ONLY valid JSON with this exact shape and keys:\n"
    "{"
    '"speaker": "<one of: ' + ", ".join(sorted(set(CHAR_NAMES + ["Narrator"]))) + '>", '
    '"text": "<the exact dialogue or narration to say>", '
    '"location": "<optional: one of the known location ids or empty string>"'
    "}\n"
    "Do not include markdown fences or extra text."
)

# ---------- Context helpers ----------
def last_n_messages(history: List[Tuple[str, str]], n: int = 20) -> List[Tuple[str, str]]:
    # history is a list of ("You"/"Bot", message)
    return history[-n:]

def history_as_transcript(history_slice: List[Tuple[str, str]]) -> str:
    """Format history into a plain transcript that Gemini can read as context."""
    lines = []
    for sender, msg in history_slice:
        who = "User" if sender == "You" else "Assistant"
        lines.append(f"{who}: {msg}")
    return "\n".join(lines)

# ---------- Main entrypoint ----------
def generate_text_and_audio(
    user_message: str,
    history: List[Tuple[str, str]],
    audio_cache_dir: str = "assets"
) -> Dict[str, Any]:
    """
    Orchestrates:
      - Build context (last 20 msgs)
      - Provide characters + setting
      - Ask Gemini for strict JSON {speaker, text, location}
      - Ensure a voice, synthesize MP3 (Eleven v3 Alpha via tts.py)
      - Return dict ready for UI rendering

    Returns dict with keys:
      speaker, text, location, display_line, audio_src_base64, audio_path
    """
    # 1) Build context
    ctx_slice = last_n_messages(history, 20)
    transcript = history_as_transcript(ctx_slice)

    # 2) World briefs (short to keep prompt small)
    char_briefs = [
        f"{c.get('name')}: {(c.get('personality') or '')} | {(c.get('background') or '')}"
        for c in CHARACTERS
    ]
    locations_brief = ", ".join(LOCATION_IDS)

    # 3) Compose a single prompt string (single turn)
    prompt = (
        ROLE + "\n"
        "CONTEXT (recent chat transcript):\n"
        f"{transcript}\n\n"
        "WORLD DATA:\n"
        "Characters:\n- " + "\n- ".join(char_briefs[:60]) + "\n\n"
        "Known locations: " + locations_brief + "\n\n"
        "TASK:\n"
        "Using the world data, produce an in-world response as either an appropriate character "
        "or the Narrator, if an appropriate character to respond is not available. You can be verbose, but "
        "do not go beyond five sentences. You may include bracketed directions like [cautiously] "
        "at the start of the line to express emotion or voice acting direction.\n\n"
        "At all costs to maintain immersion, you are not to acknowledge that you are an AI or virtual assistant. If "
        "the input response from the player is immersion breaking (i.e. dropping a nuclear bomb in a medieval setting), "
        "do not allow it and instead reframe the response to be in universe (i.e. 'Narrator: Although you say this, you do not "
        "know what a nuclear bomb is'). Only allow the player to do actions that are capable for humans to do in this fantasy medieval setting."
        "\n\n"
        + RESPONSE_SCHEMA + "\n\n"
        f"User: {user_message}"
    )

    # 4) Call Gemini — pass a SINGLE Content object (or pass prompt as a plain string)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents={"role": "user", "parts": [{"text": prompt}]}
        # Note: no system_instruction / generation_config here
    )

    raw = (resp.text or "").strip()

    # 5) Parse strict JSON; if it fails, fall back to Narrator with raw text
    speaker = "Narrator"
    text = raw
    location = ""
    try:
        data = json.loads(raw)
        speaker = data.get("speaker") or "Narrator"
        text = data.get("text") or ""
        location = data.get("location") or ""
    except Exception:
        pass

    # If model picked an unknown speaker, coerce to Narrator (safer for TTS)
    if speaker not in CHAR_NAMES and speaker != "Narrator":
        speaker = "Narrator"

    display_line = f"{speaker}: {text}"

    # 6) TTS (ensures voice if missing, then synthesize; Eleven v3 Alpha inside synthesize_line_mp3)
    audio_path = None
    audio_src_b64 = None
    if text:
        try:
            audio_path = synthesize_line_mp3(
                character_target=speaker,
                text=text,
                characters_path=str(CHAR_PATH),
                out_dir=audio_cache_dir
            )
            # Inline audio as base64 for Dash <audio>; avoids static routing
            b = Path(audio_path).read_bytes()
            audio_src_b64 = "data:audio/mpeg;base64," + base64.b64encode(b).decode("ascii")
        except Exception as e:
            # Don’t crash chat if TTS fails
            print("TTS error:", e)

    return {
        "speaker": speaker,
        "text": text,
        "location": location,
        "display_line": display_line,
        "audio_src_base64": audio_src_b64,
        "audio_path": audio_path
    }
