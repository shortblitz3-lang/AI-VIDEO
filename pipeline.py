"""
AI Video Studio — core pipeline
Topic -> story & script (Google Gemini, free tier) -> voiceover (Edge neural voices, free)
-> cinematic images (Pollinations, free) -> assembled MP4 video (MoviePy + ffmpeg).
"""
import asyncio
import hashlib
import json
import os
import re
import time
import traceback
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

VIDEO_W, VIDEO_H = 1280, 720

# ---------------------------------------------------------------- languages
LANGUAGES = {
    "Bengali": {
        "gtts": "bn",
        "voice_test": "এই গল্পটি শুরু হয়েছিল হাজার বছর আগে, এক প্রাচীন নদীর তীরে।",
        "voices": [
            ("bn-IN-TanishaaNeural", "Tanishaa — female, warm & natural"),
            ("bn-IN-BashkarNeural", "Bashkar — male, deep & steady"),
        ],
    },
    "Hindi": {
        "gtts": "hi",
        "voice_test": "यह कहानी शुरू हुई थी हज़ार साल पहले, एक प्राचीन नदी के किनारे।",
        "voices": [
            ("hi-IN-SwaraNeural", "Swara — female, expressive"),
            ("hi-IN-MadhurNeural", "Madhur — male, rich documentary voice"),
        ],
    },
    "English": {
        "gtts": "en",
        "voice_test": "This story began a thousand years ago, on the banks of an ancient river.",
        "voices": [
            ("en-IN-NeerjaNeural", "Neerja — female (Indian English)"),
            ("en-IN-PrabhatNeural", "Prabhat — male (Indian English)"),
            ("en-US-AriaNeural", "Aria — female (very expressive)"),
            ("en-US-GuyNeural", "Guy — male (energetic)"),
            ("en-GB-SoniaNeural", "Sonia — female (British, documentary)"),
            ("en-GB-RyanNeural", "Ryan — male (British)"),
        ],
    },
}

# ---------------------------------------------------------------- visual styles
STYLES = {
    "Cinematic (realistic film)": (
        "cinematic film still, dramatic volumetric lighting, photorealistic, "
        "epic wide composition, depth of field, 35mm film grain"
    ),
    "3D Animation (Pixar style)": (
        "3D animated movie still, Pixar-style, vibrant colors, soft global "
        "illumination, highly detailed render, cinematic framing"
    ),
    "Anime": (
        "anime movie still, studio-quality animation art, dramatic lighting, "
        "detailed painted background, cinematic"
    ),
    "Epic Historical Painting": (
        "classical oil painting, epic historical scene, rich dramatic colors, "
        "museum quality, painterly detail"
    ),
    "Comic / Graphic Novel": (
        "graphic novel illustration, bold ink lines, dramatic shading, "
        "vintage comic color palette"
    ),
}

def _pick_font(language):
    """Return a font path that covers the language (with fallbacks)."""
    preferred, fallback = {
        "Bengali": ("HindSiliguri-Regular.ttf", "NotoSansBengali-Regular.ttf"),
        "Hindi": ("NotoSansDevanagari-Regular.ttf", None),
        "English": ("NotoSans-Regular.ttf", None),
    }[language]
    fonts_dir = BASE_DIR / "fonts"
    for name in (preferred, fallback):
        if name and (fonts_dir / name).exists():
            return str(fonts_dir / name)
    return str(fonts_dir / "NotoSans-Regular.ttf")


# ================================================================ 1. SCRIPT
def generate_script(api_key, topic, language, minutes, style, extra_instructions=""):
    """Ask Google Gemini (free tier) for a full story + script + scene images."""
    words = max(60, int(minutes * 145))
    n_scenes = max(3, min(90, int(words / 40) + 2))
    lang_name = {
        "Bengali": "Bengali (বাংলা) — write the narration fully in Bengali script",
        "Hindi": "Hindi (हिन्दी) — write the narration fully in Hindi Devanagari script",
        "English": "English",
    }[language]

    prompt = f"""You are a master YouTube storyteller and documentary scriptwriter.
Create a complete narration video script.

TOPIC: {topic}
NARRATION LANGUAGE: {lang_name}
AUDIENCE: general YouTube audience (all ages).
LENGTH: about {words} words of narration in total, spread across {n_scenes} scenes (2-4 sentences per scene).
VISUAL STYLE: {style}

Storytelling rules:
- Open with a powerful hook in the first scene that makes viewers want to stay.
- Build the story scene by scene: vivid details, suspense, emotional peaks and a satisfying ending.
- Write like a passionate human narrator speaking aloud — this text will become the voiceover.
  Use natural spoken rhythm: short breath-length sentences, natural punctuation pauses,
  the way a storyteller really talks. Never stiff, written-style prose.
- Vary the emotional tone (wonder, tension, triumph, reflection) from scene to scene.
- If the topic is history: stay factually accurate. If it is about prehistory or the future: clearly frame speculation as speculation.
- Each "image_prompt" must be ONE clear visual moment described in English, suitable for a single still image. Never ask for text, letters or captions inside the image.
{("- Additional instructions from the creator: " + extra_instructions) if extra_instructions else ""}

Return ONLY valid JSON, exactly this shape:
{{
  "title": "catchy YouTube title in the narration language",
  "youtube_description": "2-3 sentence video description in the narration language",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "scenes": [
    {{"narration": "narration text in the narration language",
      "image_prompt": "one clear image description in English"}}
  ]
}}"""

    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    raw = response.text.strip()
    # tolerate accidental markdown fences
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw)
    data = json.loads(raw)

    script = {
        "title": data.get("title", topic),
        "youtube_description": data.get("youtube_description", ""),
        "tags": data.get("tags", []),
        "scenes": [
            {
                "narration": s.get("narration", "").strip(),
                "image_prompt": s.get("image_prompt", topic).strip(),
            }
            for s in data.get("scenes", [])
            if s.get("narration", "").strip()
        ],
    }
    if not script["scenes"]:
        raise ValueError("The AI returned an empty script. Please try again.")
    return script


def parse_manual_script(text, topic):
    """Manual mode: paragraphs separated by blank lines become scenes.
    A line starting with 'image:' inside a paragraph sets that scene's image idea."""
    scenes = []
    for para in re.split(r"\n\s*\n", text.strip()):
        lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
        narration_lines, image_prompt = [], ""
        for ln in lines:
            m = re.match(r"^image\s*:\s*(.+)$", ln, re.I)
            if m:
                image_prompt = m.group(1).strip()
            else:
                narration_lines.append(ln)
        narration = " ".join(narration_lines)
        if narration:
            scenes.append({"narration": narration, "image_prompt": image_prompt or topic})
    if not scenes:
        raise ValueError("Please write at least one paragraph of narration.")
    return {
        "title": topic or "My video",
        "youtube_description": "",
        "tags": [],
        "scenes": scenes,
    }


# ================================================================ 2. VOICE
SARVAM_LANG = {"Bengali": "bn-IN", "Hindi": "hi-IN", "English": "en-IN"}
SARVAM_SPEAKERS = [
    "shubh", "aditya", "ritu", "priya", "neha", "rahul",
    "pooja", "rohan", "simran", "tanya", "ishita", "shreya",
]


def _tts_sarvam(text, language, key, speaker, pace, temperature, out_path):
    """Sarvam AI Bulbul v3 — very natural Indian-language voices with emotion."""
    import base64

    r = requests.post(
        "https://api.sarvam.ai/text-to-speech",
        headers={"api-subscription-key": key, "Content-Type": "application/json"},
        json={
            "text": text[:2500],
            "language_code": SARVAM_LANG[language],
            "speaker": speaker,
            "model": "bulbul:v3",
            "pace": min(2.0, max(0.5, pace)),
            "temperature": min(2.0, max(0.01, temperature)),
            "output_audio_codec": "mp3",
            "speech_sample_rate": "44100",
        },
        timeout=120,
    )
    r.raise_for_status()
    audio = base64.b64decode(r.json()["audios"][0])
    with open(out_path, "wb") as f:
        f.write(audio)


def synthesize_speech(
    text, voice, language, out_path, rate_pct=0, pitch_hz=0,
    sarvam_key=None, sarvam_speaker="shubh", sarvam_temperature=0.7,
):
    """Voiceover with the best available free engine, in order:
    1. Sarvam Bulbul v3 (if a free Sarvam key is given) — most natural & expressive
    2. Microsoft Edge neural voices (free, no key)
    3. gTTS (simple offline-tolerant fallback)
    Returns the engine name that was actually used."""
    out_path = str(out_path)
    if sarvam_key:
        try:
            _tts_sarvam(
                text, language, sarvam_key, sarvam_speaker,
                1.0 + rate_pct / 100.0, sarvam_temperature, out_path,
            )
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                return "sarvam-bulbul-v3"
        except Exception:
            pass
    try:
        import edge_tts

        rate = f"{rate_pct:+d}%"
        pitch = f"{pitch_hz:+d}Hz"

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(out_path)

        asyncio.run(_run())
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return "edge-tts"
        raise RuntimeError("empty audio")
    except Exception:
        from gtts import gTTS

        gTTS(text=text, lang=LANGUAGES[language]["gtts"]).save(out_path)
        return "gTTS-fallback"


# ================================================================ 3. IMAGES
def fetch_scene_image(prompt, style, out_path, seed=None):
    """Free cinematic images via Pollinations (Flux model, no API key needed)."""
    style_suffix = STYLES.get(style, STYLES["Cinematic (realistic film)"])
    full_prompt = f"{prompt}, {style_suffix}"
    if seed is None:
        seed = int(hashlib.md5(full_prompt.encode()).hexdigest()[:6], 16)
    key = hashlib.md5(f"{full_prompt}|{seed}".encode()).hexdigest()[:16]
    cache_file = CACHE_DIR / f"img_{key}.jpg"

    if cache_file.exists():
        with open(cache_file, "rb") as f:
            data = f.read()
        with open(out_path, "wb") as f:
            f.write(data)
        return str(out_path)

    url = (
        "https://image.pollinations.ai/prompt/"
        + requests.utils.quote(full_prompt[:900])
        + f"?width={VIDEO_W}&height={VIDEO_H}&nologo=true&model=flux&seed={seed}"
    )
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and len(r.content) > 15000 and r.headers.get(
                "content-type", ""
            ).startswith("image"):
                with open(out_path, "wb") as f:
                    f.write(r.content)
                with open(cache_file, "wb") as f:
                    f.write(r.content)
                return str(out_path)
        except Exception:
            pass
        time.sleep(3 * (attempt + 1))

    # never fail the whole video: generate a dark gradient placeholder
    _placeholder(out_path, prompt)
    return str(out_path)


def _placeholder(out_path, prompt):
    img = Image.new("RGB", (VIDEO_W, VIDEO_H))
    px = np.linspace(0, 1, VIDEO_W)
    gradient = (px * 60 + 10).astype(np.uint8)
    arr = np.stack([gradient, gradient * 0.65, gradient * 0.9], axis=-1)
    arr = np.repeat(arr[:, None, :], VIDEO_H, axis=1)
    pil = Image.fromarray(arr)
    d = ImageDraw.Draw(pil)
    d.text((40, VIDEO_H - 60), prompt[:90], fill=(220, 220, 220))
    pil.save(out_path, quality=90)


# ---------------------------------------------------------------- stock footage
def _search_query(image_prompt):
    """Turn a scene description into short keywords for footage search."""
    words = [w for w in re.split(r"[^a-zA-Z]+", image_prompt) if w]
    return " ".join(words[:8])


def fetch_stock_video(query, pexels_key, out_path):
    """Free real moving footage from Pexels (free key from pexels.com/api).
    Returns the file path, or None if nothing suitable was found."""
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query[:100], "orientation": "landscape", "per_page": 10},
            headers={"Authorization": pexels_key},
            timeout=30,
        )
        if r.status_code != 200:
            return None
        for video in r.json().get("videos", []):
            files = [
                f for f in video.get("video_files", [])
                if f.get("file_type") == "h264"
                and (f.get("width") or 0) >= 1280
                and (f.get("height") or 0) >= 720
                and (f.get("fps") or 30) <= 31
            ]
            files.sort(key=lambda f: (f.get("width") or 99999))
            for f in files:
                try:
                    d = requests.get(f["link"], timeout=180)
                    if d.status_code == 200 and len(d.content) > 200000:
                        with open(out_path, "wb") as fh:
                            fh.write(d.content)
                        return str(out_path)
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _video_scene_clip(path, dur):
    """Turn a downloaded footage file into a scene clip of exactly `dur` seconds,
    cropped to 16:9. Short clips are looped automatically."""
    from moviepy import VideoFileClip, vfx

    vc = VideoFileClip(path).without_audio()
    if vc.duration < dur - 0.05:
        try:
            vc = vc.with_effects([vfx.Loop(duration=dur)])
        except Exception:
            pass
    else:
        vc = vc.subclipped(0, dur)
    if vc.w < VIDEO_W or vc.h < VIDEO_H:
        vc = vc.resized(max(VIDEO_W / vc.w, VIDEO_H / vc.h))
    vc = vc.cropped(
        x_center=vc.w / 2, y_center=vc.h / 2, width=VIDEO_W, height=VIDEO_H
    )
    return vc


# ---------------------------------------------------------------- motion
def _ease(p):
    """Smoothstep easing so camera moves feel filmic, not mechanical."""
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def _motion_clip(arr, dur, index):
    """Cinematic motion for a still image: cycles eased zoom-in / pan / zoom-out
    / pan the other way, so scenes feel alive and varied."""
    from moviepy import ImageClip

    mode = index % 4
    if mode in (0, 2):
        if mode == 0:
            zoom = lambda tt, d=dur: 1 + 0.11 * _ease(tt / d)
        else:
            zoom = lambda tt, d=dur: 1.11 - 0.11 * _ease(tt / d)
        return ImageClip(arr, duration=dur).resized(zoom)
    base = ImageClip(arr, duration=dur).resized(1.12)
    max_x = -(base.w - VIDEO_W)
    fixed_y = -(base.h - VIDEO_H) / 2.0
    if mode == 1:  # pan right
        pos = lambda tt, d=dur: (max_x * _ease(tt / d), fixed_y)
    else:  # pan left
        pos = lambda tt, d=dur: (max_x * (1 - _ease(tt / d)), fixed_y)
    return base.with_position(pos)


# ================================================================ 4. VIDEO
def _fmt_srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scene_timings):
    entries = []
    for i, (start, end, text) in enumerate(scene_timings):
        entries.append(f"{i+1}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{text}\n")
    return "\n".join(entries)


def render_video(
    script,
    language,
    voice,
    workdir,
    style="Cinematic (realistic film)",
    subtitles=True,
    rate_pct=0,
    pitch_hz=0,
    progress=None,  # callable(stage:str, done:int, total:int)
    visual_mode="image",  # "image" | "auto" | "stock"
    pexels_key=None,
    sarvam_key=None,
    sarvam_speaker="shubh",
    sarvam_temperature=0.7,
):
    """Assemble the final MP4. Returns (mp4_path, srt_text, engines_used)."""
    import textwrap

    from moviepy import (AudioFileClip, CompositeAudioClip, CompositeVideoClip,
                         ImageClip, TextClip, vfx)

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    scenes = script["scenes"]
    total = len(scenes)

    def report(stage, done):
        if progress:
            progress(stage, done, total)

    video_clips, audio_clips, scene_timings = [], [], []
    engines = set()
    gap = 0.35  # natural pause between scenes
    font_path = _pick_font(language)

    t = 0.0
    for i, scene in enumerate(scenes):
        narration = scene["narration"].strip()
        image_prompt = scene["image_prompt"].strip() or narration

        # --- voice
        audio_path = workdir / f"voice_{i:03d}.mp3"
        try:
            engines.add(
                synthesize_speech(
                    narration, voice, language, audio_path,
                    rate_pct=rate_pct, pitch_hz=pitch_hz,
                    sarvam_key=sarvam_key, sarvam_speaker=sarvam_speaker,
                    sarvam_temperature=sarvam_temperature,
                )
            )
            audio_clip = AudioFileClip(str(audio_path))
            voice_dur = audio_clip.duration
        except Exception:
            audio_clip = None
            voice_dur = max(3.0, len(narration) / 14.0)

        dur = voice_dur + gap

        # --- visuals: real moving footage first (if enabled), else AI image
        scene_clip = None
        if visual_mode in ("auto", "stock") and pexels_key:
            footage_path = workdir / f"footage_{i:03d}.mp4"
            got = fetch_stock_video(_search_query(image_prompt), pexels_key, footage_path)
            if got:
                try:
                    scene_clip = _video_scene_clip(got, dur)
                except Exception:
                    scene_clip = None

        if scene_clip is None:
            image_path = workdir / f"image_{i:03d}.jpg"
            try:
                fetch_scene_image(image_prompt, style, image_path)
            except Exception:
                _placeholder(image_path, image_prompt)
            pil = Image.open(image_path).convert("RGB").resize((VIDEO_W, VIDEO_H))
            frame = np.array(pil)
            scene_clip = _motion_clip(frame, dur, i)

        v = scene_clip.with_start(t)

        if i == 0:
            v = v.with_effects([vfx.FadeIn(0.8)])
        if i == total - 1:
            v = v.with_effects([vfx.FadeOut(1.0)])

        video_clips.append(v)

        # --- subtitles
        if subtitles and narration:
            wrapped = textwrap.fill(narration, width=44, max_lines=4, placeholder=" …")
            try:
                txt = TextClip(
                    font=font_path,
                    text=wrapped,
                    font_size=40,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    method="caption",
                    size=(VIDEO_W - 120, None),
                    text_align="center",
                )
                # place the whole caption block safely above the bottom edge
                try:
                    y = VIDEO_H - txt.h - 34
                except Exception:
                    y = VIDEO_H - 200
                txt = (
                    txt.with_start(t + 0.15)
                    .with_duration(max(0.2, dur - 0.3))
                    .with_position(("center", max(y, VIDEO_H // 2)))
                )
                video_clips.append(txt)
            except Exception:
                traceback.print_exc()

        # --- audio on the timeline
        if audio_clip is not None:
            audio_clips.append(audio_clip.with_start(t))

        scene_timings.append((t, t + dur, narration))
        t += dur
        report("voices+images", i + 1)

    final = CompositeVideoClip(video_clips, size=(VIDEO_W, VIDEO_H))
    if audio_clips:
        final = final.with_audio(CompositeAudioClip(audio_clips))

    out_path = workdir / "final_video.mp4"
    report("render", 0)
    final.write_videofile(
        str(out_path),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="160k",
        preset="medium",
        threads=os.cpu_count() or 2,
        logger=None,
    )
    final.close()
    for c in video_clips:
        try:
            c.close()
        except Exception:
            pass
    report("render", total)

    srt_text = build_srt(scene_timings)
    return str(out_path), srt_text, engines
