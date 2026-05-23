#!/usr/bin/env bash
# Assemble the 60s launch video: per-beat narration -> Ken-Burns slide clips
# sized to each line -> concat + mux. Voice: Gemini TTS if GEMINI_API_KEY is set
# (launch/tts_gemini.py), else macOS `say` (baseline). Reproducible.
set -euo pipefail
cd "$(dirname "$0")/.."
B=launch/build; A=launch/audio; C=launch/build/clips
mkdir -p "$A" "$C"
FPS=30; PAD=0.35; VOICE="${LAZ_VOICE:-Samantha}"; RATE="${LAZ_RATE:-186}"; INCR=0.00045; FADE=0.35
TEMPO="${LAZ_TEMPO:-1.0}"   # >1 speeds narration (Gemini paces slow); slides auto-resize

slides=(01-crisis 02-scale 03-lazarus 04-proof 05-forge 06-google 07-uses 08-close)
texts=(
"In 2020, New Jersey's unemployment system collapsed under a sixteen hundred percent surge, and the governor begged for volunteers who could still read COBOL."
"Sixty years of code still runs our banks, benefits, and hospitals, with business rules nobody wrote down. The cost of that debt: two point four trillion dollars."
"Meet Lazarus. Drop in legacy COBOL, and it recovers the lost business rules and rewrites them as clean, modern Python."
"Here is the difference: it does not grade its own homework. Lazarus proves its Python against the original COBOL, through a real compiler, byte for byte. Red, to green."
"Hit an idiom it doesn't know? It writes itself a new skill, re-reads it, and retries, until the proof holds."
"Built on Google's newest: Gemini three point five Flash, with a million token context, and the Managed Agents API, running real code in a live sandbox that keeps the skills it forges."
"Government benefits, banking, insurance, healthcare. Anywhere dead code still runs the world."
"Lazarus. Proven, autonomous modernization."
)

tts () { # $1=text  $2=out.wav  -> 44.1k stereo wav
  if [ -n "${GEMINI_API_KEY:-}" ] && [ -f launch/tts_gemini.py ]; then
    if .venv/bin/python launch/tts_gemini.py "$1" "/tmp/_g.wav" 2>/tmp/_tts.err; then
      ffmpeg -y -i /tmp/_g.wav -af "atempo=$TEMPO" -ar 44100 -ac 2 "$2" >/dev/null 2>&1; return
    fi
    echo "  (gemini tts failed, falling back to say: $(tail -1 /tmp/_tts.err))" >&2
  fi
  say -r "$RATE" -v "$VOICE" -o /tmp/_s.aiff "$1"
  ffmpeg -y -i /tmp/_s.aiff -af "atempo=$TEMPO" -ar 44100 -ac 2 "$2" >/dev/null 2>&1
}

echo "[1/4] narration ($([ -n "${GEMINI_API_KEY:-}" ] && echo Gemini || echo 'say '))..."
durs=()
for i in "${!texts[@]}"; do
  tts "${texts[$i]}" "$A/n$i.wav"
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$A/n$i.wav")
  D=$(python3 -c "print(round($d + $PAD, 3))"); durs+=("$D")
  printf "   beat %d  %-11s  %ss\n" "$i" "${slides[$i]}" "$D"
done

echo "[2/4] Ken-Burns slide clips..."
for i in "${!slides[@]}"; do
  D="${durs[$i]}"; F=$(python3 -c "print(int($D*$FPS))")
  FO=$(python3 -c "print(round($D-$FADE,3))")
  ffmpeg -y -loop 1 -i "$B/${slides[$i]}.png" -t "$D" -r $FPS -vf \
   "scale=1920:1080,zoompan=z='min(zoom+$INCR,1.09)':d=$F:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=$FPS,fade=t=in:st=0:d=$FADE,fade=t=out:st=$FO:d=$FADE,format=yuv420p" \
   -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "$C/c$i.mp4" >/dev/null 2>&1
done

echo "[3/4] concat video + audio..."
: > /tmp/vlist.txt; : > /tmp/alist.txt
for i in "${!slides[@]}"; do
  echo "file '$PWD/$C/c$i.mp4'" >> /tmp/vlist.txt
  ffmpeg -y -i "$A/n$i.wav" -af "apad,atrim=0:${durs[$i]}" -ar 44100 -ac 2 "$A/p$i.wav" >/dev/null 2>&1
  echo "file '$PWD/$A/p$i.wav'" >> /tmp/alist.txt
done
ffmpeg -y -f concat -safe 0 -i /tmp/vlist.txt -c copy "$B/video.mp4" >/dev/null 2>&1
ffmpeg -y -f concat -safe 0 -i /tmp/alist.txt -c copy "$A/narration.wav" >/dev/null 2>&1

echo "[4/4] mux -> launch/lazarus_launch.mp4"
ffmpeg -y -i "$B/video.mp4" -i "$A/narration.wav" \
  -c:v copy -c:a aac -b:a 192k -shortest launch/lazarus_launch.mp4 >/dev/null 2>&1
echo "DONE  $(ffprobe -v error -show_entries format=duration -of csv=p=0 launch/lazarus_launch.mp4)s  $(du -h launch/lazarus_launch.mp4 | cut -f1)"
