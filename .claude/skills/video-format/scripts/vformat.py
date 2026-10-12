#!/usr/bin/env python3
"""vformat.py — convert ad videos between 9:16, 4:5, 1:1 and 16:9 without stretching.

Needs only Python 3.8+ and ffmpeg/ffprobe in PATH.

Commands
  info     <video>                          size, aspect, duration, fps, bitrate
  preview  <video> --to 4:5 [opts]          writes a contact sheet PNG (4 moments) of the result, NO full encode
  convert  <video> --to 4:5 [opts] [-o out] full encode
  batch    <folder> --to 4:5 [opts]         every .mp4/.mov in the folder -> <folder>/<to>/

Options
  --mode crop|pad|auto   crop = cut the extra height/width (default when going 9:16->4:5)
                         pad  = keep the whole frame, fill the empty area with a blurred copy (default when going 4:5->9:16)
                         auto (default) = pad when the target is TALLER/narrower than the source, crop when it is wider
  --pos center|top|bottom|<0..1>   where the crop window sits (vertical crops: 0=top edge, 1=bottom edge; horizontal: 0=left, 1=right)
  --width 1080           output width (height follows the aspect)
  --max-mb 200           target max file size (two-pass bitrate if the plain encode would be bigger)
  --crf 21               quality for the plain encode
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

RATIOS = {"9:16": (9, 16), "4:5": (4, 5), "1:1": (1, 1), "16:9": (16, 9), "3:4": (3, 4)}
EXTS = (".mp4", ".mov", ".m4v", ".mkv", ".webm")


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg error:\n" + (r.stderr[-2000:] if r.stderr else ""))
    return r.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path])
    d = json.loads(out)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = abs(int(float(sd["rotation"])))
    if rot in (90, 270):
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    has_audio = any(s["codec_type"] == "audio" for s in d["streams"])
    size_mb = os.path.getsize(path) / 1048576
    return dict(w=w, h=h, fps=fps, dur=dur, audio=has_audio, mb=size_mb)


def target_size(to, width):
    a, b = RATIOS[to]
    W = width - width % 2
    H = round(W * b / a)
    return W, H - H % 2


def pos_value(pos):
    if pos in ("center", None):
        return 0.5
    if pos == "top" or pos == "left":
        return 0.0
    if pos == "bottom" or pos == "right":
        return 1.0
    return max(0.0, min(1.0, float(pos)))


def build_filter(info, to, mode, pos, width):
    W, H = target_size(to, width)
    sw, sh = info["w"], info["h"]
    src_ratio, dst_ratio = sw / sh, W / H
    if mode in ("auto", None):
        mode = "pad" if dst_ratio < src_ratio - 1e-3 else "crop"
    p = pos_value(pos)
    if abs(dst_ratio - src_ratio) < 1e-3:
        return f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v]", W, H, "scale"
    if mode == "crop":
        if dst_ratio < src_ratio:  # cut sides
            cw = f"ih*{W}/{H}"
            return (f"[0:v]crop={cw}:ih:(iw-{cw})*{p}:0,scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v]", W, H, "crop")
        ch = f"iw*{H}/{W}"  # cut top/bottom
        return (f"[0:v]crop=iw:{ch}:0:(ih-{ch})*{p},scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v]", W, H, "crop")
    # pad with blurred background
    return (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.08[bg];"
            f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v]", W, H, "pad")


def default_mode(info, to):
    W, H = target_size(to, 1080)
    return "pad" if (W / H) < (info["w"] / info["h"]) - 1e-3 else "crop"


def preview(path, to, mode, pos, width, out_png):
    info = probe(path)
    mode = mode or default_mode(info, to)
    flt, W, H, used = build_filter(info, to, mode, pos, width)
    tmp = tempfile.mkdtemp()
    times = [min(info["dur"] * f, max(info["dur"] - 0.5, 0)) for f in (0.02, 0.33, 0.66, 0.97)]
    frames = []
    for i, t in enumerate(times):
        f = os.path.join(tmp, f"p{i}.png")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-filter_complex", flt.replace("[v]", ",scale=360:-2[v]"),
             "-map", "[v]", "-frames:v", "1", f])
        frames.append(f)
    inputs = sum([["-i", f] for f in frames], [])
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", f"hstack=inputs={len(frames)}", out_png])
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(dict(preview=out_png, mode=used, pos=pos or "center", out=f"{W}x{H}", src=f"{info['w']}x{info['h']}",
                          moments_sec=[round(t, 1) for t in times]), ensure_ascii=False))


def convert(path, to, mode, pos, width, out, max_mb, crf):
    info = probe(path)
    mode = mode or default_mode(info, to)
    flt, W, H, used = build_filter(info, to, mode, pos, width)
    fps = min(max(round(info["fps"]), 24), 60)
    flt = flt.replace("format=yuv420p[v]", f"fps={fps},format=yuv420p[v]")
    amap = ["-map", "0:a?", "-c:a", "aac", "-b:a", "128k"] if info["audio"] else []
    base = ["ffmpeg", "-y", "-v", "error", "-i", path, "-filter_complex", flt, "-map", "[v]"]
    run(base + amap + ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
    mb = os.path.getsize(out) / 1048576
    if max_mb and mb > max_mb and info["dur"] > 0:
        vk = int((max_mb * 0.97 * 8 * 1024) / info["dur"] - (130 if info["audio"] else 0))
        log = tempfile.mktemp()
        run(["ffmpeg", "-y", "-v", "error", "-i", path, "-filter_complex", flt, "-map", "[v]", "-c:v", "libx264", "-preset", "slow",
             "-b:v", f"{vk}k", "-pass", "1", "-passlogfile", log, "-an", "-f", "null", os.devnull])
        run(base + amap + ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{vk}k", "-pass", "2", "-passlogfile", log,
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
        for f in os.listdir(os.path.dirname(log) or "."):
            if f.startswith(os.path.basename(log)):
                try: os.remove(os.path.join(os.path.dirname(log), f))
                except OSError: pass
        mb = os.path.getsize(out) / 1048576
    o = probe(out)
    print(json.dumps(dict(out=out, mode=used, pos=pos or "center", size=f"{o['w']}x{o['h']}", duration=round(o["dur"], 2),
                          src_duration=round(info["dur"], 2), mb=round(mb, 1), audio=o["audio"]), ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["info", "preview", "convert", "batch"])
    ap.add_argument("path")
    ap.add_argument("--to", choices=list(RATIOS))
    ap.add_argument("--mode", choices=["crop", "pad", "auto"])
    ap.add_argument("--pos", default=None)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("-o", "--out")
    ap.add_argument("--max-mb", type=float, default=200)
    ap.add_argument("--crf", type=int, default=21)
    a = ap.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found in PATH — install ffmpeg first (see SKILL.md)")
    mode = None if a.mode == "auto" else a.mode
    if a.cmd == "info":
        i = probe(a.path)
        g = __import__("math").gcd(i["w"], i["h"])
        print(json.dumps(dict(size=f"{i['w']}x{i['h']}", aspect=f"{i['w']//g}:{i['h']//g}", ratio=round(i["w"] / i["h"], 4),
                              duration=round(i["dur"], 2), fps=round(i["fps"], 2), audio=i["audio"], mb=round(i["mb"], 1))))
        return
    if not a.to:
        sys.exit("--to is required (9:16, 4:5, 1:1, 16:9, 3:4)")
    tag = a.to.replace(":", "x")
    if a.cmd == "preview":
        out = a.out or os.path.splitext(a.path)[0] + f"_{tag}_preview.png"
        preview(a.path, a.to, mode, a.pos, a.width, out)
    elif a.cmd == "convert":
        out = a.out or os.path.splitext(a.path)[0] + f"_{tag}.mp4"
        convert(a.path, a.to, mode, a.pos, a.width, out, a.max_mb, a.crf)
    else:
        od = os.path.join(a.path, tag); os.makedirs(od, exist_ok=True)
        for f in sorted(os.listdir(a.path)):
            if f.lower().endswith(EXTS):
                convert(os.path.join(a.path, f), a.to, mode, a.pos, a.width,
                        os.path.join(od, os.path.splitext(f)[0] + f"_{tag}.mp4"), a.max_mb, a.crf)


if __name__ == "__main__":
    main()
