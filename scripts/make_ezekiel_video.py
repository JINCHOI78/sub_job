#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
에스겔 30:10-26 묵상 영상 렌더러.
Pillow로 프레임을 합성해 imageio-ffmpeg(libx264)로 H.264 MP4를 인코딩한다.
내용은 제공된 QT 자료 범위 안에서만 구성 (지어낸 내용 없음).
사용:  python3 make_ezekiel_video.py            # 전체 mp4
       python3 make_ezekiel_video.py --sample   # 샘플 프레임 PNG만
"""
import sys, os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
OUT = os.path.join(HERE, "..", "ezekiel30.mp4")

W, H = 1920, 1080
FPS = 24
SAMPLE = "--sample" in sys.argv

# ---- palette ----
GOLD        = (203, 168,  95)
GOLD_BRIGHT = (230, 201, 130)
SAND        = (232, 224, 207)
SAND_DIM    = (183, 173, 151)

# ---- fonts ----
def load(name, size): return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
F_EYE   = load("NotoSansKR.ttf", 27)
F_COVER = load("NanumMyeongjo.ttf", 96)
F_TITLE = load("NanumMyeongjo.ttf", 62)
F_REF   = load("NanumMyeongjo.ttf", 40)
F_BODY  = load("NanumMyeongjo.ttf", 37)

# ---- content (from provided QT material only) ----
SLIDES = [
 dict(theme="night", dur=6.0, cover=True, eyebrow="말씀 묵상 · QT",
      title=[("강하게도, 약하게도 하시는", SAND), ("역사의 주권자", GOLD_BRIGHT)],
      ref="에스겔 30 : 10 – 26"),
 dict(theme="night", dur=7.6, eyebrow="본문 배경",
      title=[("포로지에서 들려온 말씀", SAND)],
      body="기원전 6세기 초, 유다는 바벨론 제국에 멸망하여 포로로 끌려갔습니다. "
           "선지자 에스겔은 그 절망의 포로지에서 하나님의 말씀을 대언합니다."),
 dict(theme="river", dur=8.2, eyebrow="두 제국",
      title=[("바벨론 그리고 애굽", SAND)],
      body="느부갓네살이 이끄는 신흥 강국 바벨론, 오랜 전통의 제국 애굽. "
           "유다는 하나님보다 애굽의 군사력을 의지했으나, 애굽은 끝내 유다를 구하지 못했습니다."),
 dict(theme="fire", dur=8.0, eyebrow="에스겔 30 : 10 – 11",
      title=[("바벨론의 손을 빌린 심판", SAND)],
      body="하나님은 바벨론 왕 느부갓네살의 손을 도구 삼아 애굽의 교만과 번영을 끝내겠다 선포하십니다. "
           "그 군대는 하나님의 심판을 집행하는 도구였습니다."),
 dict(theme="river", dur=8.2, eyebrow="에스겔 30 : 12 – 13",
      title=[("마르는 나일, 무너지는 우상", SAND)],
      body="“나일 강의 물줄기를 말리리라.” 애굽 풍요의 근원이자 그들이 신으로 섬기던 강을 "
           "하나님이 직접 무너뜨리시고, 온 땅의 우상을 멸하십니다."),
 dict(theme="fire", dur=8.0, eyebrow="에스겔 30 : 14 – 19",
      title=[("불타오르는 도시들", SAND)],
      body="바드로스 · 소안 · 신 · 놉(멤피스) · 아웬 — 애굽의 군사와 종교와 경제의 중심지들이 "
           "불타고 파괴되며, 백성은 포로로 끌려갑니다."),
 dict(theme="break", dur=8.6, eyebrow="에스겔 30 : 20 – 22 · ‘팔’",
      title=[("꺾인 바로의 팔", SAND)],
      body="고대 근동에서 왕의 ‘팔’은 곧 힘과 군사력. 하나님은 바로의 팔을 꺾으시고, "
           "붕대를 감아도 낫지 않아 다시는 칼을 쥐지 못하게 하십니다."),
 dict(theme="night", dur=8.2, eyebrow="에스겔 30 : 24 – 25",
      title=[("강하여진 바벨론의 팔", SAND)],
      body="반대로 바벨론 왕의 팔은 강하게 하시고 “그의 손에 내 칼을 주리라” 하십니다. "
           "그 승리는 그들의 능력이 아니라, 하나님이 주신 권세였습니다."),
 dict(theme="light", dur=9.0, eyebrow="에스겔 30 : 26 · 심판의 목적",
      title=[("내가 여호와인 줄 알리라", GOLD_BRIGHT)],
      body="흩어짐과 심판의 모든 과정을 통해 하나님은 말씀하십니다. "
           "세상의 참된 주관자는 바로도, 우상도 아닌 오직 여호와이심을 알게 하려 하심입니다."),
 dict(theme="light", dur=9.4, eyebrow="묵상",
      title=[("역사의 주권자", SAND)],
      body="강대국들의 패권 다툼처럼 보이는 그 배후에서, 국가의 흥망성쇠를 주관하시며 "
           "한 팔을 꺾고 다른 팔을 세우시는 분 — 그분이 바로 하나님이십니다."),
]

# ---------------- backgrounds ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
nx, ny = xx / W, yy / H

def lerp(a, b, t): return a + (b - a) * t

def gradient(top, bot, glow_xy, glow_col, glow_r, glow_str, rays=False):
    base = np.empty((H, W, 3), np.float32)
    for c in range(3):
        base[..., c] = lerp(top[c], bot[c], ny)
    gx, gy = glow_xy
    d = np.sqrt(((nx - gx) * 1.7) ** 2 + (ny - gy) ** 2) / glow_r
    inten = np.clip(1 - d, 0, 1) ** 1.6 * glow_str
    for c in range(3):
        base[..., c] += glow_col[c] * inten
    if rays:
        for k in range(5):
            cx = 0.18 + 0.16 * k
            band = np.exp(-(((nx - cx) / 0.05) ** 2)) * np.clip(1 - ny, 0, 1)
            for c in range(3):
                base[..., c] += (232, 201, 130)[c] * 0.05 * band
    return np.clip(base, 0, 255)

BG = {
 "night": gradient((13,16,24),(10,12,19),(0.5,0.22),(28,35,56),0.75,0.9),
 "river": gradient((11,20,27),(8,19,26),(0.5,0.70),(18,53,64),0.85,0.9),
 "fire":  gradient((18,12,13),(11,7,9),(0.5,0.94),(58,22,8),0.9,1.0),
 "break": gradient((12,14,21),(9,10,15),(0.5,0.40),(26,29,42),0.9,0.7),
 "light": gradient((19,16,25),(12,9,16),(0.5,0.04),(74,58,26),0.6,1.0,rays=True),
}

# vignette (multiplicative)
vd = np.sqrt(((nx - 0.5) * 1.15) ** 2 + ((ny - 0.42) * 1.0) ** 2)
VIGN = np.clip(1.0 - np.clip((vd - 0.42) / 0.62, 0, 1) * 0.62, 0, 1).astype(np.float32)[..., None]

# ---------------- particles ----------------
def dot_kernel(r):
    s = r * 2 + 1
    ax = np.arange(s) - r
    gx, gy = np.meshgrid(ax, ax)
    k = np.exp(-(gx ** 2 + gy ** 2) / (2 * (r / 2.2) ** 2))
    return (k / k.max()).astype(np.float32)

def streak_kernel(w=64, h=5):
    ax = np.arange(h) - h // 2
    vert = np.exp(-(ax ** 2) / (2 * (h / 3.0) ** 2))
    ramp = np.linspace(0, 1, w) ** 1.5   # tail on the left
    k = np.outer(vert, ramp)
    return (k / k.max()).astype(np.float32)

K_DOT = dot_kernel(9)
K_DOT_BIG = dot_kernel(13)
K_STREAK = streak_kernel()

THEME_CFG = {
 "night": dict(n=70, mode="rise", vy=(-0.10,-0.35), vx=(-0.06,0.06), a=(0.10,0.5),
               cols=[(230,201,130),(203,168,95),(150,168,200)], kern="dot"),
 "river": dict(n=30, mode="flow", vy=(-0.02,0.02), vx=(0.6,1.6), a=(0.08,0.4),
               cols=[(120,190,200),(203,168,95),(200,220,225)], kern="streak"),
 "fire":  dict(n=95, mode="rise", vy=(-0.7,-1.9), vx=(-0.28,0.28), a=(0.15,0.6),
               cols=[(232,150,60),(181,83,58),(230,201,130)], kern="big"),
 "break": dict(n=42, mode="fall", vy=(0.18,0.6), vx=(-0.1,0.1), a=(0.08,0.32),
               cols=[(150,150,160),(120,124,140),(180,175,165)], kern="dot"),
 "light": dict(n=60, mode="rise", vy=(-0.14,-0.45), vx=(-0.03,0.08), a=(0.10,0.45),
               cols=[(232,201,130),(247,225,170),(203,168,95)], kern="dot"),
}

rng = np.random.default_rng(30)  # fixed seed -> deterministic

class PS:
    def __init__(self, cfg):
        self.cfg = cfg; n = cfg["n"]
        def U(lohi, k):
            lo, hi = lohi; return rng.uniform(min(lo, hi), max(lo, hi), k)
        self.x = rng.uniform(0, W, n); self.y = rng.uniform(0, H, n)
        self.vx = U(cfg["vx"], n) * FPS/24
        self.vy = U(cfg["vy"], n) * FPS/24
        self.a = U(cfg["a"], n)
        self.ph = rng.uniform(0, 2*math.pi, n)
        self.col = np.array([cfg["cols"][i % len(cfg["cols"])] for i in range(n)], np.float32)
        self.kern = {"dot":K_DOT, "big":K_DOT_BIG, "streak":K_STREAK}[cfg["kern"]]
    def step(self):
        self.x += self.vx; self.y += self.vy; self.ph += 0.09
        m = self.cfg["mode"]
        if m == "rise":
            off = self.y < -12; self.y[off] = H + 12; self.x[off] = rng.uniform(0, W, off.sum())
        elif m == "fall":
            off = self.y > H + 12; self.y[off] = -12; self.x[off] = rng.uniform(0, W, off.sum())
        self.x[self.x < -140] = W + 20; self.x[self.x > W + 140] = -20
    def render(self, buf, weight=1.0):
        k = self.kern; kh, kw = k.shape
        tw = 0.6 + 0.4 * np.sin(self.ph)
        streak = self.cfg["kern"] == "streak"
        for i in range(len(self.x)):
            a = self.a[i] * tw[i] * weight
            if a <= 0.01: continue
            cx, cy = int(self.x[i]), int(self.y[i])
            if streak:
                x0, y0 = cx - kw, cy - kh // 2
            else:
                x0, y0 = cx - kw // 2, cy - kh // 2
            x1, y1 = x0 + kw, y0 + kh
            sx0, sy0 = max(0, x0), max(0, y0); sx1, sy1 = min(W, x1), min(H, y1)
            if sx0 >= sx1 or sy0 >= sy1: continue
            ks = k[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
            buf[sy0:sy1, sx0:sx1] += ks[..., None] * self.col[i] * a

SYS = [PS(THEME_CFG[s["theme"]]) for s in SLIDES]

# ---------------- text layers ----------------
def wrap(text, font, maxw):
    words = text.split(" "); lines = []; cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def draw_tracked(d, cx, y, text, font, fill, track):
    total = sum(font.getlength(ch) + track for ch in text) - track
    x = cx - total / 2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + track
    return total

def text_layer(s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx = W // 2; cover = s.get("cover")
    # measure block height
    blocks = []
    blocks.append(("eyebrow", s["eyebrow"]))
    tfont = F_COVER if cover else F_TITLE
    for ln, col in s["title"]:
        blocks.append(("title", (ln, col)))
    if s.get("ref"): blocks.append(("ref", s["ref"]))
    body_lines = wrap(s["body"], F_BODY, 1180) if s.get("body") else []
    for bl in body_lines: blocks.append(("body", bl))

    lh_title = int(tfont.size * 1.26)
    lh_body = 70
    heights = {"eyebrow": 40, "title": lh_title, "ref": 58, "body": lh_body}
    gap_after = {"eyebrow": 46, "title": 22, "ref": 20, "body": 8}
    total = 0; prev = None
    for kind, _ in blocks:
        if prev is not None: total += gap_after[prev]
        # extra gap between title group and body
        total += heights[kind]; prev = kind
    if cover: total += 60  # divider zone
    y = (H * 0.50) - total / 2 - 10

    prev = None
    for kind, val in blocks:
        if prev is not None: y += gap_after[prev]
        if kind == "eyebrow":
            tw = sum(F_EYE.getlength(ch) + 6 for ch in val) - 6
            draw_tracked(d, cx, y, val, F_EYE, GOLD + (255,), 6)
            ly = y + F_EYE.size * 0.55
            for sgn in (-1, 1):
                x2 = cx + sgn * (tw / 2 + 22)
                x1 = x2 + sgn * 46
                d.line([(min(x1, x2), ly), (max(x1, x2), ly)], fill=GOLD + (150,), width=1)
            y += heights["eyebrow"]
        elif kind == "title":
            ln, col = val
            tw = tfont.getlength(ln)
            d.text((cx - tw / 2, y), ln, font=tfont, fill=col + (255,))
            y += heights["title"]
        elif kind == "ref":
            tw = sum(F_REF.getlength(ch) + 4 for ch in val) - 4
            draw_tracked(d, cx, y, val, F_REF, GOLD + (255,), 4)
            y += heights["ref"]
        elif kind == "body":
            tw = F_BODY.getlength(val)
            d.text((cx - tw / 2, y), val, font=F_BODY, fill=SAND_DIM + (255,))
            y += heights["body"]
        prev = kind
    if cover:
        y += 34
        d.line([(cx - 30, y), (cx + 30, y)], fill=GOLD + (170,), width=1)
    arr = np.asarray(img).astype(np.float32)
    return arr[..., :3], arr[..., 3:4] / 255.0   # rgb, alpha(0..1)

TXT = [text_layer(s) for s in SLIDES]

# ---------------- timeline ----------------
starts = []; t = 0.0
for s in SLIDES:
    starts.append(t); t += s["dur"]
TOTAL = t
TR = 0.7  # bg crossfade half-window handled below

def smooth(a, b, x):
    if x <= a: return 0.0
    if x >= b: return 1.0
    u = (x - a) / (b - a); return u * u * (3 - 2 * u)

def frame_at(t):
    # active slide
    i = 0
    for k in range(len(SLIDES)):
        if t >= starts[k]: i = k
    Si = starts[i]; Di = SLIDES[i]["dur"]; Ei = Si + Di
    # ---- background (crossfade across boundary) ----
    bg = BG[SLIDES[i]["theme"]]
    if i + 1 < len(SLIDES):
        b = Ei  # boundary
        if t > b - TR / 2:
            u = smooth(b - TR / 2, b + TR / 2, t)
            bg = bg * (1 - u) + BG[SLIDES[i + 1]["theme"]] * u
    if i > 0:
        b = Si
        if t < b + TR / 2:
            u = smooth(b - TR / 2, b + TR / 2, t)
            bg = BG[SLIDES[i - 1]["theme"]] * (1 - u) + bg * u
    frame = bg * VIGN
    # ---- particles ----
    light = np.zeros((H, W, 3), np.float32)
    SYS[i].render(light, 1.0)
    if i + 1 < len(SLIDES) and t > Ei - TR / 2:
        u = smooth(Ei - TR / 2, Ei + TR / 2, t)
        SYS[i].render(light, -0.0)  # (already added)
        SYS[i + 1].render(light, u)
    frame += light
    # ---- text envelope ----
    tin = Si + 0.5; tout = Ei - 0.45
    o = smooth(tin, tin + 0.9, t) * (1 - smooth(tout - 0.7, tout, t))
    if o > 0.003:
        rgb, al = TXT[i]
        dy = int((1 - smooth(tin, tin + 0.9, t)) * 30)
        a = al * o
        if dy:
            a = np.roll(a, dy, axis=0); rgb2 = np.roll(rgb, dy, axis=0)
        else:
            rgb2 = rgb
        frame = frame * (1 - a) + rgb2 * a
    # ---- progress bar ----
    p = t / TOTAL; bw = int(W * p)
    frame[H - 4:H, 0:bw] = np.array(GOLD, np.float32)
    return np.clip(frame, 0, 255).astype(np.uint8)

# ---------------- step particles up to a time (for determinism in full run) ----------------
def render_all():
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    nframes = int(round(TOTAL * FPS))
    cmd = [exe, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-crf", "19", "-preset", "medium", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in range(nframes):
        for ps in SYS: ps.step()
        t = f / FPS
        p.stdin.write(frame_at(t).tobytes())
        if f % 120 == 0:
            print(f"  frame {f}/{nframes}  ({t:5.1f}s)", flush=True)
    p.stdin.close(); p.wait()
    print("done ->", OUT, os.path.getsize(OUT), "bytes")

def render_samples():
    picks = [(0, 3.0), (4, None), (6, None), (8, None)]
    imgs = []
    for i, tt in picks:
        # advance particles a bit for liveliness
        for _ in range(40):
            for ps in SYS: ps.step()
        t = tt if tt is not None else starts[i] + SLIDES[i]["dur"] * 0.55
        imgs.append(Image.fromarray(frame_at(t)))
    grid = Image.new("RGB", (W, H * len(imgs) // 2 if False else H // 2 * len(imgs)))
    # simple 2x2 thumbnail grid
    tw, th = W // 2, H // 2
    grid = Image.new("RGB", (tw * 2, th * 2), (0, 0, 0))
    for idx, im in enumerate(imgs):
        th_im = im.resize((tw, th))
        grid.paste(th_im, ((idx % 2) * tw, (idx // 2) * th))
    out = os.path.join(HERE, "..", ".fonts_tmp", "sample_grid.png")
    grid.save(out); print("sample ->", out)

if __name__ == "__main__":
    if SAMPLE: render_samples()
    else: render_all()
