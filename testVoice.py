# tts_sample_v3.py
import os
import hashlib
import random
from pathlib import Path
from typing import Tuple, Union
import argparse
import requests
from dotenv import load_dotenv

# Import your previously defined function (adjust path/module if needed)
# from ensure_voice import ensure_voice_id_for_character_in_file
# If ensure_voice.py is in the same dir, this import works:
from tts import ensure_voice_id_for_character_in_file

load_dotenv()
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
BASE = "https://api.elevenlabs.io/v1"


class ElevenError(RuntimeError):
    pass


def _headers_for_tts():
    if not ELEVEN_API_KEY:
        raise ElevenError("Missing ELEVEN_API_KEY in environment (.env).")
    return {
        "xi-api-key": ELEVEN_API_KEY,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }


def _safe_filename(s: str) -> str:
    return "".join(c for c in s.lower().replace(" ", "-") if c.isalnum() or c in ("-", "_"))


def _hash_for(text: str, voice_id: str) -> str:
    return hashlib.sha256((voice_id + "||" + text).encode("utf-8")).hexdigest()[:12]


# ------------------ Random directional line (v3 style) ------------------

_DIRECTIONS = [
    "whispering", "giggling", "cautiously", "warmly", "teasing", "sternly",
    "tired", "excited", "muttering", "commanding", "nervously", "softly",
    "deadpan", "confidently", "hastily", "suspiciously", "dreamily",
    "cheerfully", "grimly", "relieved", "annoyed", "wistfully"
]

_LINE_TEMPLATES = [
    "[{dir}] That's really funny!",
    "[{dir}] Hello, is this seat taken?",
    "[{dir}] I shouldn't be here, but here we are.",
    "[{dir}] Careful—one wrong step and it's the river.",
    "[{dir}] I knew you'd say that.",
    "[{dir}] Tell me the truth, slowly.",
    "[{dir}] Oh! You scared me for a moment.",
    "[{dir}] Look at the bridge—do you hear the bells?",
    "[{dir}] No deals after dark. Not here.",
    "[{dir}] One more question, then I'll go.",
    "[{dir}] Do you smell smoke, or is that just the docks?",
    "[{dir}] Keep your voice down; walls have ears.",
    "[{dir}] That's the plan... probably.",
    "[{dir}] A toast to small victories.",
    "[{dir}] Hush. Footsteps on the stairs."
]


def random_directional_line(rng: random.Random | None = None) -> str:
    r = rng or random
    direction = r.choice(_DIRECTIONS)
    template = r.choice(_LINE_TEMPLATES)
    return template.format(dir=direction)


# ------------------ Public entrypoint ------------------

def synthesize_random_directional_sample_mp3(
    character_target: Union[str, int],
    characters_path: str = "characters.json",
    out_dir: str = "audio_cache",
    model_id: str = "eleven_v3"  # v3 alpha
) -> Tuple[str, str]:
    """
    Ensures a voice for the character, generates a random directional line,
    and saves an MP3 using Eleven v3 alpha to audio_cache/.
    Returns: (mp3_path, text_used)
    """
    # 1) Ensure we have a voiceId for the character
    voice_id = ensure_voice_id_for_character_in_file(character_target, characters_path)

    # 2) Create a directional line
    text = random_directional_line()

    # 3) Prepare output path (cache by voice+text)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    name_part = _safe_filename(str(character_target))
    hash_part = _hash_for(text, voice_id)
    out_path = Path(out_dir) / f"{name_part or 'character'}-{hash_part}.mp3"
    if out_path.exists():
        return str(out_path), text

    # 4) Call ElevenLabs TTS (v3 alpha model)
    url = f"{BASE}/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        # Optionally tune voice settings if supported:
        # "voice_settings": {"stability": 0.4, "similarity_boost": 0.75}
    }

    r = requests.post(url, headers=_headers_for_tts(), json=payload, timeout=120)
    if r.status_code >= 400:
        raise ElevenError(f"TTS failed: {r.status_code} {r.text}")

    out_path.write_bytes(r.content)
    return str(out_path), text


# ------------------ CLI Test ------------------

def main():
    parser = argparse.ArgumentParser(description="Synthesize a random directional sample (Eleven v3 alpha) for a character.")
    parser.add_argument("target", help="Character name (str) or index (int) in characters.json")
    parser.add_argument("--characters", default="characters.json", help="Path to characters.json (default: characters.json)")
    parser.add_argument("--out", default="audio_cache", help="Output folder for MP3 (default: audio_cache)")
    parser.add_argument("--model", default="eleven_v3", help="Model id (default: eleven_v3)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible line selection")
    args = parser.parse_args()

    # Interpret target as index if it's an int
    target: Union[str, int]
    if args.target.isdigit():
        target = int(args.target)
    else:
        target = args.target

    if args.seed is not None:
        random.seed(args.seed)

    try:
        mp3_path, text_used = synthesize_random_directional_sample_mp3(
            character_target=target,
            characters_path=args.characters,
            out_dir=args.out,
            model_id=args.model
        )
        print("MP3 saved to:", mp3_path)
        print("Line used:", text_used)
    except Exception as e:
        print("Error:", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
