"""Minimal Piper helper to speak narration.

Only dependency besides Piper itself: the standard-library *winsound* module
(Windows only).  No extra audio libraries are introduced.
"""

from __future__ import annotations

from __future__ import annotations

import tempfile
import wave
import winsound
from pathlib import Path
from typing import Optional

from piper import PiperVoice, SynthesisConfig
from zork_logging import system_log

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
# Load game configuration
import json, os
_CFG_PATH = BASE_DIR / "config.json"
with _CFG_PATH.open("r", encoding="utf-8") as _cf:
    _CFG = json.load(_cf)

VOICE_DIR = BASE_DIR / _CFG.get("voicepath", "res/voices")
TMP_DIR = BASE_DIR / _CFG.get("audiopath", "res/wavtmp")
VOICE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Desired voice file stem (e.g. "en_US-lessac-high")
_VOICE_STEM: str | None = (_CFG.get("voice_settings", {}).get("voice"))

# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------
_VOICE: Optional[PiperVoice] = None
_CONFIG: SynthesisConfig = SynthesisConfig()  # default params

# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download_voice(model_id: str) -> None:
    """Download *model_id* into VOICE_DIR using Piper's Python API."""
    system_log(f"Downloading Piper voice '{model_id}' …")
    from piper.download_voices import download_voice  # local import to avoid heavy cost at startup
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        download_voice(model_id, str(VOICE_DIR))
        system_log("Voice download completed")
    except Exception as exc:
        system_log(f"Voice download failed: {exc}")
        raise

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _find_default_model() -> Path:
    """Return the first *.onnx file inside VOICE_DIR."""
    pattern = f"{_VOICE_STEM}*.onnx" if _VOICE_STEM else "*.onnx"
    matches = list(VOICE_DIR.glob(pattern))
    if not matches:
        if _VOICE_STEM:
            _download_voice(_VOICE_STEM)
            matches = list(VOICE_DIR.glob(pattern))
        if not matches:
            raise FileNotFoundError("Voice model not found and download failed")
    return matches[0]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_voice(model_path: str | Path | None = None, *, use_cuda: bool = False) -> None:
    """Load a Piper voice ready for synthesis.

    If *model_path* is omitted, the first model in *res/voices* is used.
    """
    global _VOICE
    path = Path(model_path) if model_path else _find_default_model()
    _VOICE = PiperVoice.load(str(path), use_cuda=use_cuda)


def speak(text: str) -> None:
    """Synthesize *text* and play it synchronously."""
    if _VOICE is None:
        init_voice()  # auto-load for convenience
    assert _VOICE is not None  # mypy guard

    # Render to a temporary WAV then play with winsound
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=TMP_DIR, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with wave.open(str(tmp_path), "wb") as wav_file:
            system_log("Synthesizing voice …")
            _VOICE.synthesize_wav(text, wav_file, syn_config=_CONFIG)
            system_log("Synthesis complete")
        winsound.PlaySound(str(tmp_path), winsound.SND_FILENAME)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)  # Python ≥3.8
        except TypeError:
            # older Pythons
            from os import remove
            try:
                remove(tmp_path)
            except FileNotFoundError:
                pass


def stream(text: str):
    """Yield `AudioChunk`s from Piper for caller-managed playback."""
    if _VOICE is None:
        init_voice()
    assert _VOICE is not None
    yield from _VOICE.synthesize(text, syn_config=_CONFIG)


def set_synthesis_config(**kwargs):  # type: ignore[override]
    """Update default synthesis parameters (e.g., volume=0.5)."""
    global _CONFIG
    _CONFIG = SynthesisConfig(**kwargs)

# ---------------------------------------------------------------------------
# Stand-alone quick test: ``python -m zork_voice "Hello world"``
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Quick voice test for Piper helper")
    parser.add_argument("text", nargs="*", help="Text to speak; defaults to a test sentence")
    parser.add_argument("--cuda", action="store_true", help="Use CUDA if available")
    ns = parser.parse_args()

    phrase = " ".join(ns.text) if ns.text else "This is a Piper TTS test."
    try:
        init_voice(use_cuda=ns.cuda)
        speak(phrase)
    except Exception as exc:
        system_log(f"Voice test failed: {exc}")
        print(f"Voice test failed: {exc}", file=sys.stderr)
        sys.exit(1)
