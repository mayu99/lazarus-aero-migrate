#!/usr/bin/env python3
"""Gemini TTS narration: text -> WAV (24kHz mono). Used by build_video.sh when
GEMINI_API_KEY is set, to swap the baseline `say` voice for Gemini's.

  python3 launch/tts_gemini.py "narration text" out.wav

Env overrides:
  GEMINI_API_KEY   (required)
  LAZ_TTS_MODEL    default "gemini-2.5-flash-preview-tts"  (the current TTS model;
                   set to whatever TTS-capable model your key has access to)
  LAZ_TTS_VOICE    default "Charon"  (try Kore, Puck, Aoede, Charon, Fenrir...)
"""
import os, sys, wave
from google import genai
from google.genai import types

def main() -> int:
    if len(sys.argv) != 3:
        print("usage: tts_gemini.py <text> <out.wav>", file=sys.stderr); return 2
    text, out = sys.argv[1], sys.argv[2]
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY not set", file=sys.stderr); return 1

    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=os.environ.get("LAZ_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=os.environ.get("LAZ_TTS_VOICE", "Charon")
                    )
                )
            ),
        ),
    )
    pcm = resp.candidates[0].content.parts[0].inline_data.data  # s16le, 24kHz, mono
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(pcm)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
