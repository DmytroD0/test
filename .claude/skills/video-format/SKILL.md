---
name: video-format
description: Convert ad videos between 9:16, 4:5, 1:1 and 16:9 (Reels/Stories ↔ Facebook feed) without stretching — smart crop or blurred-background pad, preview before encoding, keeps audio and duration, fits under 200 MB. Use when the user asks to "make this video 4:5 / 9:16 / square", "адаптуй відео під 4:5", "зроби 9:16", "переведи у формат фіду", or drops video files and names a target aspect ratio.
---

# Video format conversion (9:16 ↔ 4:5 ↔ 1:1 ↔ 16:9)

Tool: `scripts/vformat.py` in this skill folder (Python 3 + ffmpeg/ffprobe only). Call it by its full path, e.g.
`python3 "<skill_dir>/scripts/vformat.py" info "video.mp4"` (on Windows use `python` instead of `python3` if needed).

## Rules (never break them)
1. NEVER stretch or squash the picture. Only crop or pad.
2. Keep audio and the full duration. Never cut the start or the end.
3. Output = H.264 MP4, 1080 px wide (4:5 → 1080×1350, 9:16 → 1080×1920, 1:1 → 1080×1080, 16:9 → 1920×1080 with `--width 1920`), file ≤ 200 MB (the script switches to two-pass automatically).
4. Don't touch the original file. Results go next to it with a suffix (`_4x5.mp4`, `_9x16.mp4`…) unless the user names an output path.
5. ALWAYS make a preview and LOOK at it before the full encode (step 3 below). Don't deliver without checking the result frames.

## Which mode
- Target is WIDER than the source (9:16 → 4:5, 9:16 → 1:1, 4:5 → 1:1): `crop` (default). Choose the crop window with `--pos`:
  - `center` (default) — talking heads, product shots, most UGC.
  - a number 0..1 for the vertical window position (0 = keep the top, 1 = keep the bottom). Use it when faces, a headline, burned-in subtitles or a CTA plate sit high or low in the frame, e.g. `--pos 0.35` keeps more of the top, `--pos 0.7` keeps more of the bottom.
  - Scroll-caption videos (text scrolling over a photo): `center` is fine — lines entering/leaving at the edges are expected.
- Target is TALLER than the source (4:5 → 9:16, 1:1 → 9:16, 16:9 → 4:5/9:16): `pad` (default) — the whole frame is kept, the empty top/bottom is filled with a blurred, slightly darkened copy of the same video. Use `--mode crop` only if the user explicitly wants a full-bleed crop and the preview shows nothing important is cut.

## Workflow
1. `info` on each file → note size, aspect, duration, audio.
2. If the source already has the target aspect, say so and only re-encode/compress if asked.
3. `preview <file> --to 4:5 [--pos …]` → a PNG with 4 moments of the RESULT (start, ⅓, ⅔, end). Open/read that PNG and check: faces and heads not cut, burned-in subtitles/headlines/CTA plate fully visible, product visible, no black bars. If something is cut, change `--pos` (or switch mode) and preview again. For important videos also check one or two extra moments where the subtitles/plates appear.
4. `convert <file> --to 4:5 [--pos …]` (or `batch <folder> --to 4:5` for many files with the same layout — preview one of them first).
5. Verify: the script prints size, duration (must equal the source duration), MB, audio=true. Report to the user: file path, resolution, duration, size, which mode/position you used and why.

## Commands
```
python3 vformat.py info    video.mp4
python3 vformat.py preview video.mp4 --to 4:5 [--pos center|top|bottom|0..1] [--mode crop|pad]
python3 vformat.py convert video.mp4 --to 4:5 [--pos …] [--mode …] [-o out.mp4] [--max-mb 200] [--crf 21]
python3 vformat.py batch   folder/   --to 9:16 [--pos …] [--mode …]      # → folder/9x16/*.mp4
```
Targets: `9:16`, `4:5`, `1:1`, `16:9`, `3:4`.

## Troubleshooting
- "ffmpeg not found": install it — macOS `brew install ffmpeg`; Windows `winget install Gyan.FFmpeg` (then reopen the terminal); Linux `sudo apt install ffmpeg`.
- Very long videos encode for several minutes — tell the user it's running; don't start a second encode of the same file.
- iPhone/vertical files with rotation metadata are handled (the script reads the rotation).
