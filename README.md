# 🎬 AI Video Studio (v2)

Turn any topic into a complete YouTube video — story, script, voiceover, moving
visuals and subtitles — in **Bengali, English or Hindi**. You only type the topic.
Everything the AI makes can be edited by you before the video is created.

**What is new in v2**
- 🎥 **Real moving footage mode** — the app can fetch real cinematic video clips
  (Pexels) instead of still images. Choose "Auto: real footage first, AI image if
  none" for the best mix.
- 🎞️ **Richer cinematic motion** — AI-image scenes now move with eased film-style
  zooms and side pans (not just a single zoom).
- 🎙️ **Sarvam AI voices (recommended)** — very natural, expressive Indian-language
  voices (Bengali/Hindi/English). Free credits when you sign up at
  dashboard.sarvam.ai. The free Microsoft Edge neural voices remain as the
  no-signup option.

| Part | Free tool used |
|---|---|
| Story & script writing | Google Gemini API (free tier — needs a free key) |
| Best voices (recommended) | Sarvam AI Bulbul (free signup credits) |
| Backup voices | Microsoft Edge neural voices (free, no key) |
| Real moving footage | Pexels API (free key) |
| AI pictures | Pollinations AI (free, no key) |
| Video assembly | MoviePy + ffmpeg (free open-source) |
| Running the app | Streamlit Community Cloud (free forever) or your own computer |

---

## Step 1 — Free API keys (each takes 1–3 minutes)

1. **Gemini (required)** — https://aistudio.google.com/apikey → sign in with
   Google → "Create API key" → copy it. This writes the story & script.
2. **Sarvam (recommended)** — https://dashboard.sarvam.ai → sign up → copy your
   API key. Gives free credits, used for the most natural Bengali/Hindi/English
   voices. Without it, the app uses free Edge neural voices.
3. **Pexels (optional, for real footage)** — https://www.pexels.com/api/ → sign
   up → instant free key. Lets the app use real moving cinematic footage.

You paste these keys in the app's sidebar — nothing else to configure.

---

## Step 2 — Put the app online, FREE forever (Streamlit Cloud)

Your app gets a link like `https://yourname-ai-video-studio.streamlit.app`.

**If you already have a GitHub repo (e.g. `AI-VIDEO`):**

1. Go to your repo page on github.com → **"Add file" → "Upload files"**.
2. Open this `ai-video-studio` folder, select ALL files and folders inside it
   (app.py, pipeline.py, requirements.txt, packages.txt, README.md, run.bat,
   run.sh, the `fonts` folder, the `.streamlit` folder) and **drag them together**
   into the upload page.
   - The `fonts` folder must appear with its `.ttf` files inside, `.streamlit`
     with `config.toml` inside. (On Windows: View → Show → Hidden items, to see
     `.streamlit`.)
3. Click **"Commit changes"** — this "pushes" the files to your repo.
4. Go to https://share.streamlit.io → sign in with GitHub → **New app** →
   Repository: `your-name/AI-VIDEO` (or `ai-video-studio`) → Branch `main` →
   Main file `app.py` → **Deploy**.
5. Wait 2–3 minutes. Your app is live — bookmark the link. It sleeps after days
   of no use and wakes when you open the link (normal, still free).

**If you don't have a repo yet:** create one at github.com (+ → New repository →
Public → Create), then follow the same upload steps.

Alternative: install the free **GitHub Desktop** app → sign in → "Add existing
repository" or drag the folder into it → write any message → "Commit to main" →
"Push origin". No commands needed.

---

## Step 2 (alternative) — Run it on your own computer

1. Install Python from https://www.python.org/downloads/ (tick **"Add Python to
   PATH"**).
2. Unzip this folder anywhere (Desktop).
3. Double-click **run.bat** (Windows) or run `sh run.sh` (Mac/Linux).
4. Your browser opens the app at http://localhost:8501.

---

## Using the app

1. Paste your keys in the sidebar.
2. Choose language, voice engine, voice, video length (1 min Short up to 30 min)
   and visual style.
3. For visuals pick: AI images with cinematic motion, or real moving footage
   (Pexels key needed), or Auto (footage first, AI image when nothing matches).
4. Type your topic — history, prehistory, present, future — anything.
5. Click **✨ Generate story & script** → get title, description, tags, scenes.
6. Edit anything: words, picture ideas, title, tags. Listen to any scene,
   preview its picture, add/delete scenes.
7. Click **🎞️ Create my video** (keep the page open) → download MP4 + SRT.
8. Upload to YouTube; paste the ready title/description/tags; upload the SRT as
   captions; add free music from YouTube's Audio Library if you like.

---

## Honest limitations (please read)

- **About "moving video":** fully AI-generated motion video (Google Veo, Sora,
  Kling) still costs money — there is no reliable free API for it today. The
  free path is: (a) **real stock footage** for scenes that exist on camera
  (nature, cities, rivers, temples, space, technology…), and (b) **AI images
  with cinematic eased zooms and pans** for scenes that don't (specific ancient
  events, future worlds, prehistoric life). The "Auto" mode combines both.
- **Voices:** the sample video you first heard used the emergency backup voice
  because of a network restriction where it was rendered. Use the **Sarvam**
  engine for the most natural, expressive narration, or the free Edge neural
  voices — both sound like a real human narrator. gTTS is only a last-resort
  fallback.
- **Long videos:** 20–30 minute videos take a while. Do a 1–3 minute test
  first; for very long videos consider making 2 parts.
- **Free limits:** Gemini free tier ≈ 10–15 script requests/minute; Sarvam free
  credits are limited (then it's ₹30 per 10,000 characters); Pexels free tier is
  generous (200 requests/hour).
- **Facts:** double-check important historical facts before publishing.
- **Pexels footage:** free to use on YouTube under the Pexels license, no
  attribution required.

## Troubleshooting

- **"Script generation failed"** — check the Gemini key, wait 1 minute, retry.
- **Voice sounds basic** — you are on the fallback (gTTS). Check the "Voice
  engine" choice and your Sarvam key, or try another network.
- **No footage found for a scene** — in Auto/stock mode the app automatically
  falls back to an AI image so the video is never lost.
- **Video creation failed** — usually a slow network: keep the page open and
  retry; scenes already downloaded are reused.

Made with free tools: Google Gemini · Sarvam AI · Microsoft Edge voices ·
Pexels · Pollinations · MoviePy · Streamlit.
