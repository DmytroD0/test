# Scroll-caption video: text scrolls up over photos. Needs Python 3.9+, Pillow, ffmpeg in PATH.
#   pip install pillow
#   python scroll_video.py text.txt photos_folder out.mp4 [--ratio 4:5|9:16|1:1] [--music music.mp3] [--wps 2.7] [--font X.ttf]
# text.txt: paragraphs separated by a blank line; **words** = yellow highlight.
# Photos are shown in name order, evenly split over the video length.
import argparse, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---- settings ----
W, H = 1080, 1350          # 4:5 feed. For 9:16 reels: 1080, 1920
WPS = 2.7                  # reading speed, words per second
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "Montserrat.ttf")   # Thai: pass --font Sarabun-Bold.ttf / Kanit-Bold.ttf
SIZE, LINE_H, PARA_GAP, SIDE_PAD = 56, 1.48, 48, 85
STROKE, SHADOW = 3, True
WHITE, YELLOW = (255, 255, 255), (255, 212, 0)
START_Y = 0.52             # where the first line sits at frame 0 (fraction of height)
MUSIC = None               # --music path; music.mp3 next to the text file is picked up automatically
FPS = 25
# ------------------

RATIOS = {"4:5": (1080, 1350), "9:16": (1080, 1920), "1:1": (1080, 1080)}
ap = argparse.ArgumentParser()
ap.add_argument("text"); ap.add_argument("photos"); ap.add_argument("out")
ap.add_argument("--ratio", choices=list(RATIOS), default="4:5")
ap.add_argument("--music"); ap.add_argument("--wps", type=float, default=WPS); ap.add_argument("--font", default=FONT)
a = ap.parse_args()
txt, photos_dir, out = a.text, a.photos, a.out
W, H = RATIOS[a.ratio]; WPS = a.wps; FONT = a.font
MUSIC = a.music or os.path.join(os.path.dirname(os.path.abspath(txt)), "music.mp3")
font = ImageFont.truetype(FONT, SIZE)
try: font.set_variation_by_name("Bold")   # variable fonts (Google Fonts download)
except Exception: pass
paras = [p.strip() for p in re.split(r"\n\s*\n", open(txt, encoding="utf-8").read()) if p.strip()]
words_total = len(re.sub(r"\*\*", "", " ".join(paras)).split())
dur = words_total / WPS

def tokens(p):  # [(word, highlighted)]
    out = []
    for i, part in enumerate(re.split(r"\*\*", p)):
        out += [(w, i % 2 == 1) for w in part.split()]
    return out

maxw = W - 2 * SIDE_PAD
space = font.getlength(" ")
lines = []   # list of (list of (word, hl)) or None for paragraph gap
for p in paras:
    cur, cw = [], 0
    for w, hl in tokens(p):
        ww = font.getlength(w)
        if cur and cw + space + ww > maxw:
            lines.append(cur); cur, cw = [], 0
        cw += (space if cur else 0) + ww; cur.append((w, hl))
    if cur: lines.append(cur)
    lines.append(None)

lh = int(SIZE * LINE_H)
th = sum(lh if l else PARA_GAP for l in lines) + 40
canvas = Image.new("RGBA", (W, th), (0, 0, 0, 0))
d = ImageDraw.Draw(canvas)
y = 0
for l in lines:
    if l is None:
        y += PARA_GAP; continue
    lw = sum(font.getlength(w) for w, _ in l) + space * (len(l) - 1)
    x = (W - lw) / 2
    for w, hl in l:
        d.text((x, y), w, font=font, fill=YELLOW if hl else WHITE, stroke_width=STROKE, stroke_fill=(0, 0, 0))
        x += font.getlength(w) + space
    y += lh
if SHADOW:
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh.putalpha(canvas.getchannel("A").point(lambda a: int(a * 0.9)))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    base = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); base.alpha_composite(sh, (0, 3)); base.alpha_composite(canvas)
    canvas = base
text_png = os.path.join(tempfile.mkdtemp(), "_text.png")
canvas.save(text_png)

photos = sorted(f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
seg = dur / len(photos)
inputs, filt = [], []
for i, f in enumerate(photos):
    inputs += ["-loop", "1", "-t", f"{seg:.3f}", "-i", os.path.join(photos_dir, f)]
    fr = int(seg * FPS)
    filt.append(f"[{i}]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                f"zoompan=z='1+0.07*on/{fr}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS},setsar=1[p{i}]")
n = len(photos)
filt.append("".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[bg]")
inputs += ["-loop", "1", "-i", text_png]
y0 = int(H * START_Y)
filt.append(f"[bg][{n}]overlay=x=0:y='{y0}-t*({y0}+{th})/{dur:.3f}':shortest=1,format=yuv420p[v]")
cmd = ["ffmpeg", "-y"] + inputs
amap = []
if MUSIC and os.path.exists(MUSIC):
    cmd += ["-stream_loop", "-1", "-i", MUSIC]
    amap = ["-map", f"{n+1}:a", "-af", f"afade=t=out:st={max(0,dur-2.5):.2f}:d=2.5", "-c:a", "aac", "-b:a", "128k"]
cmd += ["-filter_complex", ";".join(filt), "-map", "[v]"] + amap + \
       ["-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-movflags", "+faststart", out]
print(f"{words_total} words -> {dur:.1f} s, {n} photos")
subprocess.run(cmd, check=True)
os.remove(text_png)
