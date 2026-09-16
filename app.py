"""
🎬 AI Video Studio — topic to YouTube video (Bengali • English • Hindi)
Give a topic → AI writes the story & script → voiceover + cinematic visuals → MP4.
Everything can be edited before the final video is made. 100% free tools.
"""
import shutil
import uuid
from pathlib import Path

import streamlit as st

import pipeline as P

st.set_page_config(page_title="AI Video Studio", page_icon="🎬", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------------------- helpers
def new_workdir():
    d = OUTPUT_DIR / str(uuid.uuid4())[:8]
    d.mkdir(exist_ok=True)
    return d


if "script" not in st.session_state:
    st.session_state.script = None
if "video" not in st.session_state:
    st.session_state.video = None  # (mp4_path, srt_text, meta)

st.title("🎬 AI Video Studio")
st.caption(
    "Type a topic → get a complete YouTube video with story, script, voiceover and "
    "cinematic visuals — in Bengali, English or Hindi. Built on 100% free tools."
)

with st.sidebar:
    st.header("⚙️ Settings")

    st.markdown(
        "**Free Gemini API key** — get one in 2 minutes at "
        "[Google AI Studio](https://aistudio.google.com/apikey)"
    )
    api_key = st.text_input("Paste your free API key here", type="password")

    language = st.selectbox("Narration language", list(P.LANGUAGES))
    lang_cfg = P.LANGUAGES[language]

    voice_engine = st.radio(
        "Voice engine",
        ["Free neural voices (no signup)",
         "Sarvam AI — most natural (default)"],
        index=1,
    )
    sarvam_key = None
    sarvam_speaker = "shubh"
    sarvam_temperature = 0.8
    if voice_engine.startswith("Sarvam"):
        st.markdown(
            "Free key with signup credits: [dashboard.sarvam.ai](https://dashboard.sarvam.ai) "
            "— one key works for Bengali, Hindi and English"
        )
        sarvam_key = st.text_input("Sarvam API key", type="password")
        if not sarvam_key:
            st.caption("Without a key, the free Edge neural voices are used instead.")
        sarvam_speaker = st.selectbox("Sarvam voice (test & pick)", P.SARVAM_SPEAKERS)
        sarvam_temperature = st.slider(
            "Voice expressiveness", 0.1, 1.2, 0.8,
            help="Higher = more emotion and life. Around 0.6–0.9 usually sounds the "
                 "most natural; too high can add small glitches.",
        )

    voice = st.selectbox(
        "Voice for the free engine",
        [v for v, _ in lang_cfg["voices"]],
        format_func=lambda v: dict(lang_cfg["voices"]).get(v, v),
    )

    length_label = st.select_slider(
        "Video length",
        options=[
            "1 min (Short)", "3 min", "5 min", "10 min",
            "15 min", "20 min", "30 min",
        ],
        value="3 min",
    )
    minutes = int(length_label.split()[0])

    style = st.selectbox("Visual style (for AI images)", list(P.STYLES))

    visual_label = st.selectbox(
        "Visuals",
        [
            "AI images with cinematic motion",
            "Auto: real footage first, AI image if none",
            "Real moving footage only (Pexels)",
        ],
    )
    visual_mode = {
        "AI images with cinematic motion": "image",
        "Auto: real footage first, AI image if none": "auto",
        "Real moving footage only (Pexels)": "stock",
    }[visual_label]
    pexels_key = None
    if visual_mode != "image":
        st.markdown(
            "Free key (1 minute): [pexels.com/api](https://www.pexels.com/api/) "
            "— real cinematic footage, free to use on YouTube"
        )
        pexels_key = st.text_input("Pexels API key", type="password")

    st.markdown("**Fine-tune the voice** (optional)")
    rate_pct = st.slider("Speaking speed (%)", -20, 25, 0)
    pitch_hz = st.slider("Pitch (Hz)", -10, 10, 0)

    subtitles = st.checkbox("Burn subtitles into the video", value=True)

    st.divider()
    if st.button("🔊 Test this voice", use_container_width=True):
        with st.spinner("Generating a sample…"):
            try:
                import tempfile, os
                fd, tmp = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                engine = P.synthesize_speech(
                    lang_cfg["voice_test"], voice, language, tmp,
                    rate_pct=rate_pct, pitch_hz=pitch_hz,
                    sarvam_key=sarvam_key, sarvam_speaker=sarvam_speaker,
                    sarvam_temperature=sarvam_temperature,
                )
                with open(tmp, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
                st.caption(f"Engine: {engine}")
                os.remove(tmp)
            except Exception as e:
                st.error(f"Voice test failed: {e}")

# ----------------------------------------------------------------- topic & script
st.header("1 · Your topic")
topic = st.text_input(
    "What is the video about?",
    placeholder="e.g. The rise and fall of the Indus Valley Civilization · "
    "Life of dinosaurs · History of Kolkata · Future of AI in 2050 · "
    "মুঘল সাম্রাজ্যের ইতিহাস · महात्मा गांधी की जीवनी",
)
extra_instructions = st.text_input(
    "Extra instructions (optional)",
    placeholder="e.g. for kids · suspenseful · focus on science · end with a question",
)

manual_mode = st.toggle("✍️ Write my own script instead (skip the AI writer)")

c1, c2 = st.columns([1, 1])
with c1:
    generate_btn = st.button(
        "✨ Generate story & script with AI",
        type="primary",
        disabled=not (api_key and topic and not manual_mode),
        use_container_width=True,
    )
with c2:
    st.caption("You need a free API key (sidebar) and a topic above.")

if manual_mode:
    st.markdown(
        "Write each **scene** as its own paragraph (leave a blank line between scenes).\n\n"
        "Optional: add a line `image: your idea in English` inside a paragraph to "
        "control that scene's picture."
    )
    manual_text = st.text_area(
        "My script",
        height=240,
        placeholder=(
            "The story begins on the banks of the river Ganges, five thousand years ago...\n"
            "image: ancient river bank at sunrise, wide cinematic shot\n\n"
            "(next scene here...)"
        ),
    )
    if st.button("✅ Use my script", type="primary", disabled=not manual_text.strip()):
        try:
            st.session_state.script = P.parse_manual_script(manual_text, topic)
            st.session_state.video = None
            st.rerun()
        except Exception as e:
            st.error(str(e))

if generate_btn:
    with st.status("🧠 The AI is writing your story…", expanded=True) as status:
        try:
            st.write(f"Topic: **{topic}** · Language: **{language}** · Length: ~{minutes} min")
            st.session_state.script = P.generate_script(
                api_key, topic, language, minutes, style, extra_instructions
            )
            n = len(st.session_state.script["scenes"])
            status.update(
                label=f"✅ Script ready — {n} scenes. Review & edit below 👇", state="complete"
            )
            st.session_state.video = None
        except Exception as e:
            status.update(label="❌ Script generation failed", state="error")
            st.error(
                f"Could not generate the script: {e}\n\n"
                "Check that your Gemini API key is correct, and try again in a minute "
                "(free keys have a per-minute limit)."
            )

# ----------------------------------------------------------------- editor
script = st.session_state.script
if script:
    st.header("2 · Review & edit everything")

    st.subheader("📌 YouTube title, description & tags")
    script["title"] = st.text_input("Video title", value=script["title"])
    script["youtube_description"] = st.text_area(
        "YouTube description", value=script["youtube_description"], height=100
    )
    tags_str = st.text_input(
        "Tags (comma separated)", value=", ".join(script.get("tags", []))
    )
    script["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

    st.subheader("🎬 Scenes")
    st.caption("Open a scene to change its words, listen to it, or change its picture idea.")

    col_del = st.columns([1, 1, 1])
    with col_del[0]:
        if st.button("➕ Add empty scene at the end"):
            script["scenes"].append({"narration": "", "image_prompt": ""})
            st.rerun()

    for i, scene in enumerate(script["scenes"]):
        label = scene["narration"][:60] + ("…" if len(scene["narration"]) > 60 else "")
        with st.expander(f"Scene {i+1} · {label or '(empty)'}"):
            scene["narration"] = st.text_area(
                "Narration (voiceover text)", value=scene["narration"],
                key=f"nar{i}", height=110,
            )
            scene["image_prompt"] = st.text_area(
                "Picture idea (English works best)", value=scene["image_prompt"],
                key=f"img{i}", height=70,
            )
            b_listen, b_pic, b_del = st.columns(3)
            if b_listen.button("🎧 Listen", key=f"lis{i}"):
                if scene["narration"].strip():
                    import tempfile, os
                    fd, tmp = tempfile.mkstemp(suffix=".mp3")
                    os.close(fd)
                    P.synthesize_speech(
                        scene["narration"], voice, language, tmp,
                        rate_pct=rate_pct, pitch_hz=pitch_hz,
                        sarvam_key=sarvam_key, sarvam_speaker=sarvam_speaker,
                        sarvam_temperature=sarvam_temperature,
                    )
                    with open(tmp, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    os.remove(tmp)
                else:
                    st.info("Write some narration text first.")
            if b_pic.button("🖼️ Preview picture", key=f"pic{i}"):
                if scene["image_prompt"].strip():
                    import tempfile, os
                    fd, tmp = tempfile.mkstemp(suffix=".jpg")
                    os.close(fd)
                    P.fetch_scene_image(scene["image_prompt"], style, tmp)
                    st.image(tmp)
                    os.remove(tmp)
                else:
                    st.info("Write a picture idea first.")
            if b_del.button("🗑️ Delete scene", key=f"del{i}"):
                script["scenes"].pop(i)
                st.rerun()

    st.divider()
    est_scenes = len(script["scenes"])
    st.header("3 · Make the video")
    st.caption(
        f"{est_scenes} scenes · language {language} · style {style} · "
        f"visuals: {visual_label.split(' (')[0].lower()} · "
        f"voice: {'Sarvam' if sarvam_key else 'free neural'} · "
        f"subtitles {'on' if subtitles else 'off'}. Keep this page open while it works."
    )
    if st.button("🎞️ Create my video", type="primary", use_container_width=True):
        workdir = new_workdir()
        progress_bar = st.progress(0.0, text="Starting…")
        status_area = st.empty()

        def on_progress(stage, done, total):
            frac = (done / total) if total else 1.0
            if stage == "voices+images":
                progress_bar.progress(
                    0.05 + 0.45 * frac,
                    text=f"🎙️ Creating voices & pictures… scene {done}/{total}",
                )
            elif stage == "render":
                progress_bar.progress(0.5, text="🖌️ Assembling the final video… (this is the longest step)")

        try:
            mp4, srt_text, engines = P.render_video(
                script, language, voice, workdir,
                style=style, subtitles=subtitles,
                rate_pct=rate_pct, pitch_hz=pitch_hz,
                progress=on_progress,
                visual_mode=visual_mode, pexels_key=pexels_key,
                sarvam_key=sarvam_key, sarvam_speaker=sarvam_speaker,
                sarvam_temperature=sarvam_temperature,
            )
            progress_bar.progress(1.0, text="✅ Done!")
            st.session_state.video = (mp4, srt_text, {
                "title": script["title"],
                "description": script["youtube_description"],
                "tags": script["tags"],
            })
        except Exception as e:
            progress_bar.empty()
            st.error(f"Video creation failed: {e}")

# ----------------------------------------------------------------- result
if st.session_state.video:
    mp4, srt_text, meta = st.session_state.video
    st.header("4 · Your video 🎉")
    with open(mp4, "rb") as f:
        video_bytes = f.read()
    st.video(video_bytes)

    st.subheader("📌 Ready-to-paste YouTube details")
    st.code(meta["title"], language=None)
    st.text_area("Description", value=meta["description"], height=90)
    st.caption("Tags: " + ", ".join(meta["tags"]))

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ Download video (MP4)",
            data=video_bytes,
            file_name=(meta["title"] or "video")[:50].strip().replace(" ", "_") + ".mp4",
            mime="video/mp4",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "⬇️ Download subtitles (SRT)",
            data=srt_text,
            file_name="subtitles.srt",
            mime="text/plain",
            use_container_width=True,
        )

    st.info(
        "💡 Tip: add background music inside YouTube Studio (free Audio Library) "
        "or any video editor — this keeps the app 100% free and copyright-safe."
    )

st.divider()
with st.expander("ℹ️ How this works & honest limits"):
    st.markdown(
        "- **Story & script:** Google Gemini (free API key from aistudio.google.com)\n"
        "- **Voiceover:** pick one — Sarvam AI Bulbul (most natural Indian voices, "
        "free credits at dashboard.sarvam.ai) or free Microsoft Edge neural voices\n"
        "- **Visuals:** choose **real moving footage** from Pexels (free key, great "
        "for nature/history/place topics) or AI images (Pollinations) with cinematic "
        "zoom & pan motion\n"
        "- **Assembly:** MoviePy + ffmpeg — slow eased camera moves, cross-scene "
        "variety, burned-in subtitles\n\n"
        "**Honest limits:** truly AI-generated motion video (like Google Veo) still "
        "costs money — that's why real footage + cinematic motion is the free path. "
        "For scenes no footage matches (e.g. a specific ancient king), the app uses "
        "the AI image instead. Long videos (20–30 min) take a while — start small."
    )
