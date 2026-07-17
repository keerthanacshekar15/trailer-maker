"""
AI Trailer Studio (MVP)
------------------------
A minimal but fully working Streamlit video editor:
- Upload multiple videos
- Trim clips and arrange them on a timeline
- Add title cards / text overlays in multiple fonts
- Apply effects (fade in, fade out, black & white, speed change)
- AI voice narration (gTTS) + background music mixing
- Export final MP4

Run locally:  streamlit run main.py
Deploy on Streamlit Community Cloud: push requirements.txt, packages.txt, main.py to a repo.
"""

import os
import time
import tempfile
import uuid

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import fadein, fadeout, blackwhite, speedx
from moviepy.audio.fx.all import audio_loop, volumex

# --------------------------------------------------------------------------------------
# Config / constants
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="AI Trailer Studio", page_icon="🎬", layout="wide")

TARGET_HEIGHT = 480  # keep renders fast + reliable for a demo
CANVAS_SIZE = (854, 480)

FONT_OPTIONS = {
    "Bold Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "Serif Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "Mono Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "Sans Oblique": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
}

if "workdir" not in st.session_state:
    st.session_state.workdir = tempfile.mkdtemp(prefix="trailer_")
if "timeline" not in st.session_state:
    st.session_state.timeline = []  # list of dicts: path, start, end, name
if "uploaded_names" not in st.session_state:
    st.session_state.uploaded_names = set()

WORKDIR = st.session_state.workdir


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def get_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def wrap_text_size(draw, text, font):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[0], bbox[1]


def make_title_image(text, font_path, fontsize, text_color, bg_color, size=CANVAS_SIZE):
    img = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(img)
    font = get_font(font_path, fontsize)
    w, h, ox, oy = wrap_text_size(draw, text, font)
    x = (size[0] - w) // 2 - ox
    y = (size[1] - h) // 2 - oy
    draw.multiline_text((x, y), text, font=font, fill=text_color, align="center")
    return np.array(img)


def make_overlay_image(text, font_path, fontsize, text_color, position="bottom", size=CANVAS_SIZE):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_font(font_path, fontsize)
    w, h, ox, oy = wrap_text_size(draw, text, font)
    x = (size[0] - w) // 2 - ox
    if position == "bottom":
        y = size[1] - h - 40
    elif position == "top":
        y = 30
    else:
        y = (size[1] - h) // 2 - oy
    # soft shadow for legibility over any footage
    draw.multiline_text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 180), align="center")
    draw.multiline_text((x, y), text, font=font, fill=text_color, align="center")
    return np.array(img)


def save_upload(uploaded_file):
    path = os.path.join(WORKDIR, f"{uuid.uuid4().hex}_{uploaded_file.name}")
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def load_clip_resized(path, start=None, end=None):
    clip = VideoFileClip(path)
    if start is not None and end is not None:
        clip = clip.subclip(start, min(end, clip.duration))
    if clip.h != TARGET_HEIGHT:
        clip = clip.resize(height=TARGET_HEIGHT)
    return clip


# --------------------------------------------------------------------------------------
# Sidebar - workflow steps
# --------------------------------------------------------------------------------------

st.title("🎬 AI Trailer Studio")
st.caption("Upload → Trim → Arrange → Titles → Effects → AI Narration → Export")

tabs = st.tabs(["1. Upload & Trim", "2. Timeline", "3. Titles & Text", "4. Effects", "5. Narration & Music", "6. Export"])

# ---- Tab 1: Upload & Trim ----
with tabs[0]:
    st.subheader("Upload videos")
    uploads = st.file_uploader(
        "Upload one or more video clips",
        type=["mp4", "mov", "avi", "mkv", "webm", "mpeg"],
        accept_multiple_files=True,
    )

    if uploads:
        for uf in uploads:
            key = f"{uf.name}_{uf.size}"
            if key not in st.session_state.uploaded_names:
                path = save_upload(uf)
                st.session_state.uploaded_names.add(key)
                st.session_state.setdefault("saved_paths", {})[key] = path

    saved_paths = st.session_state.get("saved_paths", {})
    for key, path in saved_paths.items():
        with st.expander(f"🎞️ {os.path.basename(path)}", expanded=True):
            try:
                probe = VideoFileClip(path)
                duration = probe.duration
                st.video(path)
                st.write(f"Duration: {duration:.1f}s | Resolution: {probe.w}x{probe.h} | FPS: {probe.fps:.1f}")
                probe.close()
            except Exception as e:
                st.error(f"Could not read this file: {e}")
                continue

            c1, c2 = st.columns(2)
            start = c1.number_input(f"Start (s)", min_value=0.0, max_value=float(duration), value=0.0, key=f"start_{key}")
            end = c2.number_input(f"End (s)", min_value=0.0, max_value=float(duration), value=float(duration), key=f"end_{key}")

            if st.button("➕ Add trimmed clip to timeline", key=f"add_{key}"):
                if end > start:
                    st.session_state.timeline.append({
                        "path": path,
                        "start": start,
                        "end": end,
                        "name": os.path.basename(path),
                        "id": uuid.uuid4().hex,
                    })
                    st.success("Added to timeline. Go to the 'Timeline' tab.")
                else:
                    st.warning("End time must be greater than start time.")

# ---- Tab 2: Timeline ----
with tabs[1]:
    st.subheader("Arrange your clips")
    if not st.session_state.timeline:
        st.info("No clips yet. Add some from the 'Upload & Trim' tab.")
    for i, item in enumerate(st.session_state.timeline):
        c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
        c1.write(f"**{i+1}. {item['name']}**  ({item['start']:.1f}s → {item['end']:.1f}s)")
        if c2.button("⬆️", key=f"up_{item['id']}") and i > 0:
            st.session_state.timeline[i - 1], st.session_state.timeline[i] = (
                st.session_state.timeline[i],
                st.session_state.timeline[i - 1],
            )
            st.rerun()
        if c3.button("⬇️", key=f"down_{item['id']}") and i < len(st.session_state.timeline) - 1:
            st.session_state.timeline[i + 1], st.session_state.timeline[i] = (
                st.session_state.timeline[i],
                st.session_state.timeline[i + 1],
            )
            st.rerun()
        if c4.button("🗑️", key=f"del_{item['id']}"):
            st.session_state.timeline.pop(i)
            st.rerun()

# ---- Tab 3: Titles & Text ----
with tabs[2]:
    st.subheader("Title card (intro)")
    add_title = st.checkbox("Add an intro title card before the trailer", value=True)
    title_text = st.text_input("Title text", value="THIS SUMMER")
    title_font = st.selectbox("Title font", list(FONT_OPTIONS.keys()), key="title_font")
    title_duration = st.slider("Title duration (s)", 1, 8, 3)
    tc1, tc2 = st.columns(2)
    title_color = tc1.color_picker("Text color", "#FFFFFF")
    title_bg = tc2.color_picker("Background color", "#000000")

    st.divider()
    st.subheader("Caption overlay (over the whole trailer)")
    add_overlay = st.checkbox("Add a text overlay across the trailer", value=False)
    overlay_text = st.text_input("Overlay text", value="A JOURNEY BEYOND IMAGINATION")
    overlay_font = st.selectbox("Overlay font", list(FONT_OPTIONS.keys()), key="overlay_font")
    overlay_position = st.selectbox("Position", ["bottom", "center", "top"])
    overlay_color = st.color_picker("Overlay text color", "#FFD700")

# ---- Tab 4: Effects ----
with tabs[3]:
    st.subheader("Choose effects")
    fx_fadein = st.checkbox("Fade in (start)", value=True)
    fx_fadeout = st.checkbox("Fade out (end)", value=True)
    fx_bw = st.checkbox("Black & white grade")
    fx_speed = st.slider("Playback speed", 0.5, 2.0, 1.0, 0.1)

# ---- Tab 5: Narration & Music ----
with tabs[4]:
    st.subheader("AI voice narration (text-to-speech)")
    add_narration = st.checkbox("Generate AI narration")
    narration_text = st.text_area("Narration script", value="In a world where anything is possible...")
    narration_lang = st.selectbox("Language", ["en", "en-uk", "hi", "es", "fr"], index=0)

    st.divider()
    st.subheader("Background music")
    music_file = st.file_uploader("Upload background music (mp3/wav)", type=["mp3", "wav"])
    music_volume = st.slider("Music volume", 0.0, 1.0, 0.3)
    keep_original_audio = st.checkbox("Keep original video audio too", value=False)

# ---- Tab 6: Export ----
with tabs[5]:
    st.subheader("Render your trailer")
    export_quality = st.selectbox("Export resolution", ["480p (fast)", "720p"])
    render_btn = st.button("🎬 Render Trailer", type="primary")

    if render_btn:
        if not st.session_state.timeline:
            st.error("Add at least one clip to the timeline first.")
        else:
            try:
                with st.spinner("Rendering... this can take a minute depending on clip length."):
                    clips = []

                    # 1. Title card
                    if add_title and title_text.strip():
                        title_img = make_title_image(
                            title_text, FONT_OPTIONS[title_font], 60, title_color, title_bg
                        )
                        title_clip = ImageClip(title_img).set_duration(title_duration)
                        clips.append(title_clip)

                    # 2. Timeline clips
                    for item in st.session_state.timeline:
                        clip = load_clip_resized(item["path"], item["start"], item["end"])
                        clips.append(clip)

                    main_clip = concatenate_videoclips(clips, method="compose")

                    # 3. Effects
                    if fx_speed != 1.0:
                        main_clip = speedx(main_clip, factor=fx_speed)
                    if fx_bw:
                        main_clip = blackwhite(main_clip)
                    if fx_fadein:
                        main_clip = fadein(main_clip, 1)
                    if fx_fadeout:
                        main_clip = fadeout(main_clip, 1)

                    # 4. Text overlay across whole trailer
                    if add_overlay and overlay_text.strip():
                        overlay_img = make_overlay_image(
                            overlay_text, FONT_OPTIONS[overlay_font], 40, overlay_color, overlay_position
                        )
                        overlay_clip = ImageClip(overlay_img).set_duration(main_clip.duration)
                        main_clip = CompositeVideoClip([main_clip, overlay_clip])

                    # 5. Audio: narration + music
                    audio_tracks = []
                    if keep_original_audio and main_clip.audio is not None:
                        audio_tracks.append(main_clip.audio)

                    narration_path = None
                    if add_narration and narration_text.strip():
                        narration_path = os.path.join(WORKDIR, f"narration_{uuid.uuid4().hex}.mp3")
                        gTTS(text=narration_text, lang=narration_lang.split("-")[0]).save(narration_path)
                        narration_audio = AudioFileClip(narration_path)
                        audio_tracks.append(narration_audio)

                    if music_file is not None:
                        music_path = os.path.join(WORKDIR, f"music_{uuid.uuid4().hex}_{music_file.name}")
                        with open(music_path, "wb") as f:
                            f.write(music_file.getbuffer())
                        bg_audio = AudioFileClip(music_path)
                        if bg_audio.duration < main_clip.duration:
                            bg_audio = audio_loop(bg_audio, duration=main_clip.duration)
                        else:
                            bg_audio = bg_audio.subclip(0, main_clip.duration)
                        bg_audio = volumex(bg_audio, music_volume)
                        audio_tracks.append(bg_audio)

                    if audio_tracks:
                        final_audio = CompositeAudioClip(audio_tracks).set_duration(main_clip.duration)
                        main_clip = main_clip.set_audio(final_audio)

                    # 6. Export
                    out_path = os.path.join(WORKDIR, f"trailer_{uuid.uuid4().hex}.mp4")
                    main_clip.write_videofile(
                        out_path,
                        fps=24,
                        codec="libx264",
                        audio_codec="aac",
                        preset="ultrafast",
                        threads=4,
                        logger=None,
                    )

                st.success("Trailer rendered!")
                st.video(out_path)
                with open(out_path, "rb") as f:
                    st.download_button("⬇️ Download trailer (MP4)", f, file_name="trailer.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"Render failed: {e}")
                st.info("Try shorter clips, simpler effects, or fewer tracks and render again.")

st.divider()
st.caption("AI Trailer Studio — MVP build. Uses gTTS for AI narration and DejaVu system fonts for titles/captions.")
