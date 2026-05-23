# LAZARUS — launch video

A 60-second, 1080p launch video for LAZARUS. Reproducible from source: brand-styled
HTML slides → headless-Chrome PNGs → ffmpeg (Ken-Burns + fades) → narrated MP4.

## Regenerate

```bash
# 1. slides → launch/slides/*.html
python3 launch/make_slides.py

# 2. render each to PNG (needs Google Chrome) — see build_video step or:
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for f in launch/slides/*.html; do
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --virtual-time-budget=4500 --screenshot="launch/build/$(basename "$f" .html).png" \
    --window-size=1920,1080 "file://$PWD/$f"; done

# 3. narration + assembly → launch/lazarus_launch.mp4
bash launch/build_video.sh
```

## Voice

- **Default:** macOS `say` (no key, baseline).
- **Gemini TTS (preferred):** export a key and re-run — narration is regenerated automatically:
  ```bash
  export GEMINI_API_KEY=...        # never commit this
  export LAZ_TTS_VOICE=Charon      # optional: Kore / Puck / Aoede / Fenrir ...
  bash launch/build_video.sh
  ```
  Uses `launch/tts_gemini.py` (model overridable via `LAZ_TTS_MODEL`).

## Files (source, committed)

- `SCRIPT.md` — the timed 8-beat script + honesty checks
- `make_slides.py` — generates the 8 brand-styled 1080p slides
- `build_video.sh` — narration + Ken-Burns + concat + mux
- `tts_gemini.py` — Gemini TTS helper (text → WAV)

Generated artifacts (`slides/`, `build/`, `audio/`, `*.mp4`) are gitignored — the
final `launch/lazarus_launch.mp4` is produced locally (or attached to a release).
