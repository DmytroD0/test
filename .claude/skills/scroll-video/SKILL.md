---
name: scroll-video
description: Make a scroll-caption video — text slowly scrolls up over photos (slow zoom on each photo), **highlighted** words in yellow, optional music with fade-out, 4:5 / 9:16 / 1:1. Use when the user asks for a "скрол відео", "скрол-субтитри", "текст їде вгору по фото", "scroll caption video", or gives a text plus photos and wants a video from them.
---

# Scroll-caption video (text scrolls up over photos)

Tool: `scripts/scroll_video.py` in this skill folder. Needs Python 3.9+, Pillow (`pip install pillow`) and ffmpeg in PATH.
Font `assets/Montserrat.ttf` is used by default; `assets/example_text.txt` shows the text format.

```
python3 "<skill_dir>/scripts/scroll_video.py" text.txt photos/ out.mp4 [--ratio 4:5|9:16|1:1] [--music music.mp3] [--wps 2.7] [--font Other.ttf]
```

## Inputs
- **text.txt** (UTF-8): paragraphs separated by an EMPTY line. Words in `**double stars**` become yellow.
  If the user pastes the text in chat, write it to a `.txt` yourself. Keep their wording exactly; only add `**…**` where they asked for highlights.
- **photos folder**: .jpg/.jpeg/.png/.webp, shown in filename order (01.jpg, 02.jpg…), time split evenly. Rename files to set the order the user wants.
- **music** (optional): `--music path`, or a `music.mp3` next to the text file. Looped if short, fades out over the last 2.5 s.

## Defaults and knobs
- `--ratio 4:5` (feed) by default; `9:16` for Reels/Stories, `1:1` square.
- Duration = word count / `--wps` (2.7 words per second). Slower reading → lower wps (e.g. 2.3); faster → higher.
- Fine-tuning (font size, line height, paragraph gap, side padding, start position, shadow) is in the settings block at the top of the script: `SIZE, LINE_H, PARA_GAP, SIDE_PAD, START_Y, SHADOW`. Edit a copy only if the user asks for a different look.
- Non-Latin scripts the default font lacks (e.g. Thai): pass `--font` with a matching bold .ttf (Sarabun-Bold, Kanit-Bold from Google Fonts).

## Workflow
1. Collect text, photos and (optional) music; confirm the ratio if the user didn't name one (default 4:5).
2. Run the script. It prints `N words -> X s, M photos`.
3. Check the result: grab 3 frames (start, middle, end) with ffmpeg, e.g.
   `ffmpeg -v error -ss <t> -i out.mp4 -frames:v 1 frame.png`, and look at them — text readable, not cut at the sides, highlights in yellow, photos not stretched.
4. Report: path, resolution, duration, number of photos, music yes/no. To convert the finished video to another ratio later, use the `video-format` skill.
