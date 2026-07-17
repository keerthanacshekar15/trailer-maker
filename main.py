# ==========================================================
# AI Trailer Studio
# Part 1 - Imports, Configuration & Session State
# MoviePy 2.x Compatible
# ==========================================================

import os
import uuid
import tempfile
from pathlib import Path

import streamlit as st

from gtts import gTTS

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    TextClip,
    ColorClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
)

# ----------------------------------------------------------
# Streamlit Page Config
# ----------------------------------------------------------

st.set_page_config(
    page_title="AI Trailer Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Trailer Studio")
st.caption("Create cinematic trailers directly inside Streamlit.")

# ----------------------------------------------------------
# Temporary Working Directory
# ----------------------------------------------------------

TEMP_DIR = Path(tempfile.gettempdir()) / "ai_trailer_studio"

TEMP_DIR.mkdir(exist_ok=True)

# ----------------------------------------------------------
# Session State Initialization
# ----------------------------------------------------------

if "timeline" not in st.session_state:
    st.session_state.timeline = []

if "music_path" not in st.session_state:
    st.session_state.music_path = None

if "narration_path" not in st.session_state:
    st.session_state.narration_path = None

if "render_complete" not in st.session_state:
    st.session_state.render_complete = False

if "output_video" not in st.session_state:
    st.session_state.output_video = None

# ----------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------

def save_uploaded_file(uploaded_file):
    """
    Saves uploaded files into the temporary directory.

    Returns
    -------
    str
        Absolute path of saved file.
    """

    extension = Path(uploaded_file.name).suffix

    filename = f"{uuid.uuid4()}{extension}"

    destination = TEMP_DIR / filename

    with open(destination, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return str(destination)


def get_clip_duration(video_path):
    """
    Returns video duration in seconds.
    """

    clip = VideoFileClip(video_path)

    duration = clip.duration

    clip.close()

    return duration


def reset_output():
    """
    Clears previous render.
    """

    st.session_state.render_complete = False
    st.session_state.output_video = None


# ----------------------------------------------------------
# Sidebar
# ----------------------------------------------------------

st.sidebar.header("Project")

if st.sidebar.button("🗑 Clear Timeline"):

    st.session_state.timeline = []

    reset_output()

    st.sidebar.success("Timeline cleared.")

st.sidebar.markdown("---")

st.sidebar.write(
    f"Clips in timeline: **{len(st.session_state.timeline)}**"
)

# ----------------------------------------------------------
# Upload Section
# ----------------------------------------------------------

st.header("1️⃣ Upload Videos")

uploaded_videos = st.file_uploader(
    "Upload one or more video clips",
    type=["mp4", "mov", "avi", "mkv"],
    accept_multiple_files=True,
)

if uploaded_videos:

    for uploaded in uploaded_videos:

        file_path = save_uploaded_file(uploaded)

        duration = get_clip_duration(file_path)

        st.session_state.timeline.append(
            {
                "id": str(uuid.uuid4()),
                "name": uploaded.name,
                "path": file_path,
                "start": 0.0,
                "end": duration,
                "duration": duration,
            }
        )

    reset_output()

    st.success(f"Added {len(uploaded_videos)} clip(s) to the timeline.")

# ----------------------------------------------------------
# Timeline Editor
# ----------------------------------------------------------

st.header("2️⃣ Timeline Editor")

if not st.session_state.timeline:
    st.info("Upload one or more videos to begin editing.")

else:

    delete_index = None
    move_up_index = None
    move_down_index = None

    # Display every clip currently in the timeline
    for index, clip in enumerate(st.session_state.timeline):

        st.markdown("---")

        col1, col2 = st.columns([2, 1])

        # ----------------------------------------------
        # Left Column
        # ----------------------------------------------

        with col1:

            st.subheader(f"{index + 1}. {clip['name']}")

            # Preview video
            try:
                st.video(clip["path"])
            except Exception:
                st.warning("Preview unavailable.")

            # Trimming controls
            start_time, end_time = st.slider(
                "Trim Clip",
                min_value=0.0,
                max_value=float(clip["duration"]),
                value=(
                    float(clip["start"]),
                    float(clip["end"]),
                ),
                step=0.1,
                key=f"trim_{clip['id']}",
            )

            clip["start"] = start_time
            clip["end"] = end_time

            trimmed_duration = round(end_time - start_time, 2)

            st.write(f"Trimmed Duration: **{trimmed_duration} sec**")

        # ----------------------------------------------
        # Right Column
        # ----------------------------------------------

        with col2:

            st.write("### Actions")

            if st.button(
                "⬆ Move Up",
                key=f"up_{clip['id']}",
                disabled=index == 0,
            ):
                move_up_index = index

            if st.button(
                "⬇ Move Down",
                key=f"down_{clip['id']}",
                disabled=index == len(st.session_state.timeline) - 1,
            ):
                move_down_index = index

            if st.button(
                "❌ Delete",
                key=f"delete_{clip['id']}",
            ):
                delete_index = index

    # ----------------------------------------------
    # Perform Move Up
    # ----------------------------------------------

    if move_up_index is not None:

        timeline = st.session_state.timeline

        timeline[move_up_index], timeline[move_up_index - 1] = (
            timeline[move_up_index - 1],
            timeline[move_up_index],
        )

        reset_output()

        st.rerun()

    # ----------------------------------------------
    # Perform Move Down
    # ----------------------------------------------

    if move_down_index is not None:

        timeline = st.session_state.timeline

        timeline[move_down_index], timeline[move_down_index + 1] = (
            timeline[move_down_index + 1],
            timeline[move_down_index],
        )

        reset_output()

        st.rerun()

    # ----------------------------------------------
    # Delete Clip
    # ----------------------------------------------

    if delete_index is not None:

        st.session_state.timeline.pop(delete_index)

        reset_output()

        st.rerun()

# ----------------------------------------------------------
# Timeline Summary
# ----------------------------------------------------------

if st.session_state.timeline:

    st.markdown("---")

    total_duration = 0

    for clip in st.session_state.timeline:
        total_duration += clip["end"] - clip["start"]

    st.success(
        f"Timeline contains **{len(st.session_state.timeline)}** clip(s)"
    )

    st.write(
        f"Estimated trailer length: **{round(total_duration,2)} seconds**"
    )

# ----------------------------------------------------------
# 3️⃣ Title Screen
# ----------------------------------------------------------

st.header("3️⃣ Title Screen")

enable_title = st.checkbox(
    "Add title screen at beginning",
    value=False
)

title_text = st.text_input(
    "Main Title",
    value="MY CINEMATIC TRAILER"
)

subtitle_text = st.text_input(
    "Subtitle",
    value="Created with AI Trailer Studio"
)

title_duration = st.slider(
    "Title Duration (seconds)",
    min_value=1,
    max_value=10,
    value=3
)

# ----------------------------------------------------------
# 4️⃣ Text Overlay
# ----------------------------------------------------------

st.header("4️⃣ Text Overlay")

enable_overlay = st.checkbox(
    "Enable text overlay",
    value=False
)

overlay_text = st.text_input(
    "Overlay Text",
    value=""
)

overlay_position = st.selectbox(
    "Overlay Position",
    [
        "center",
        "top",
        "bottom",
        "left",
        "right",
    ]
)

overlay_fontsize = st.slider(
    "Overlay Font Size",
    20,
    90,
    45
)

# ----------------------------------------------------------
# Helper Function
# ----------------------------------------------------------

def convert_position(position):

    positions = {
        "center": ("center", "center"),
        "top": ("center", "top"),
        "bottom": ("center", "bottom"),
        "left": ("left", "center"),
        "right": ("right", "center"),
    }

    return positions[position]

# ----------------------------------------------------------
# 5️⃣ AI Narration
# ----------------------------------------------------------

st.header("5️⃣ AI Narration")

enable_narration = st.checkbox(
    "Generate AI Narration",
    value=False
)

narration_text = st.text_area(
    "Narration Script",
    height=150,
    placeholder="Enter narration..."
)

if enable_narration:

    if st.button("Generate Narration"):

        if narration_text.strip() == "":

            st.error("Narration text cannot be empty.")

        else:

            try:

                narration_file = TEMP_DIR / "narration.mp3"

                tts = gTTS(
                    text=narration_text,
                    lang="en",
                    slow=False
                )

                tts.save(str(narration_file))

                st.session_state.narration_path = str(
                    narration_file
                )

                st.success("Narration generated!")

                st.audio(str(narration_file))

            except Exception as error:

                st.error(error)

# ----------------------------------------------------------
# 6️⃣ Background Music
# ----------------------------------------------------------

st.header("6️⃣ Background Music")

music = st.file_uploader(
    "Upload MP3/WAV Music",
    type=["mp3", "wav"]
)

if music is not None:

    try:

        music_path = save_uploaded_file(music)

        st.session_state.music_path = music_path

        st.success("Music uploaded.")

        st.audio(music_path)

    except Exception as error:

        st.error(error)

# ----------------------------------------------------------
# Asset Summary
# ----------------------------------------------------------

st.markdown("---")

with st.expander("Current Project Assets", expanded=True):

    st.write(
        f"Title Screen: {'✅' if enable_title else '❌'}"
    )

    st.write(
        f"Text Overlay: {'✅' if enable_overlay else '❌'}"
    )

    st.write(
        f"Narration: {'✅' if st.session_state.narration_path else '❌'}"
    )

    st.write(
        f"Background Music: {'✅' if st.session_state.music_path else '❌'}"
    )

# ----------------------------------------------------------
# 7️⃣ Render Trailer
# ----------------------------------------------------------

st.header("7️⃣ Export Trailer")

output_filename = st.text_input(
    "Output File Name",
    value="AI_Trailer.mp4"
)

render_button = st.button(
    "🎬 Render Trailer",
    type="primary",
    use_container_width=True
)

# ----------------------------------------------------------
# Rendering
# ----------------------------------------------------------

if render_button:

    if len(st.session_state.timeline) == 0:

        st.error("Please upload at least one video.")

    else:

        progress = st.progress(0)

        status = st.empty()

        clips = []

        try:

            # --------------------------------------
            # Load timeline clips
            # --------------------------------------

            total = len(st.session_state.timeline)

            for index, clip_info in enumerate(
                st.session_state.timeline
            ):

                status.write(
                    f"Loading clip {index+1}/{total}"
                )

                clip = VideoFileClip(
                    clip_info["path"]
                ).subclipped(
                    clip_info["start"],
                    clip_info["end"]
                )

                # ----------------------------------
                # Optional Text Overlay
                # ----------------------------------

                if (
                    enable_overlay
                    and overlay_text.strip() != ""
                ):

                    txt = (
                        TextClip(
                            text=overlay_text,
                            font_size=overlay_fontsize,
                            color="white",
                        )
                        .with_position(
                            convert_position(
                                overlay_position
                            )
                        )
                        .with_duration(
                            clip.duration
                        )
                    )

                    clip = CompositeVideoClip(
                        [clip, txt]
                    )

                clips.append(clip)

                progress.progress(
                    int(
                        ((index + 1) / total) * 40
                    )
                )

            # --------------------------------------
            # Concatenate clips
            # --------------------------------------

            status.write(
                "Combining timeline..."
            )

            final_video = concatenate_videoclips(
                clips,
                method="compose"
            )

            progress.progress(55)

            # --------------------------------------
            # Optional Title Screen
            # --------------------------------------

            if enable_title:

                status.write(
                    "Creating title screen..."
                )

                background = ColorClip(
                    size=final_video.size,
                    color=(0, 0, 0),
                    duration=title_duration,
                )

                title = (
                    TextClip(
                        text=title_text,
                        font_size=70,
                        color="white",
                    )
                    .with_position(("center", "center"))
                    .with_duration(title_duration)
                )

                subtitle = (
                    TextClip(
                        text=subtitle_text,
                        font_size=35,
                        color="gray",
                    )
                    .with_position(
                        ("center", "bottom")
                    )
                    .with_duration(title_duration)
                )

                title_clip = CompositeVideoClip(
                    [
                        background,
                        title,
                        subtitle,
                    ]
                )

                final_video = concatenate_videoclips(
                    [
                        title_clip,
                        final_video,
                    ],
                    method="compose",
                )

            progress.progress(70)

            # --------------------------------------
            # Optional AI Narration
            # --------------------------------------

            audio_layers = []

            # Keep original video audio (if any)
            if final_video.audio is not None:
                audio_layers.append(final_video.audio)

            if st.session_state.narration_path is not None:

                status.write("Adding AI narration...")

                narration_audio = AudioFileClip(
                    st.session_state.narration_path
                )

                # Trim narration if longer than video
                if narration_audio.duration > final_video.duration:
                    narration_audio = narration_audio.subclipped(
                        0,
                        final_video.duration
                    )

                audio_layers.append(narration_audio)

            progress.progress(80)

            # --------------------------------------
            # Optional Background Music
            # --------------------------------------

            if st.session_state.music_path is not None:

                status.write("Adding background music...")

                music = AudioFileClip(
                    st.session_state.music_path
                )

                # Trim music to match trailer length
                if music.duration > final_video.duration:

                    music = music.subclipped(
                        0,
                        final_video.duration
                    )

                # Lower background music volume
                # (MoviePy 2.x uses with_volume_scaled())
                music = music.with_volume_scaled(0.25)

                audio_layers.append(music)

            # --------------------------------------
            # Combine Audio
            # --------------------------------------

            if len(audio_layers) > 0:

                status.write("Mixing audio...")

                mixed_audio = CompositeAudioClip(
                    audio_layers
                )

                final_video = final_video.with_audio(
                    mixed_audio
                )

            progress.progress(90)

            # --------------------------------------
            # Output Path
            # --------------------------------------

            output_path = TEMP_DIR / output_filename

            status.write("Rendering final trailer...")

            final_video.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=24,
                logger=None,
            )

            progress.progress(100)

            # --------------------------------------
            # Cleanup MoviePy Objects
            # --------------------------------------

            final_video.close()

            for clip in clips:
                clip.close()

            st.session_state.output_video = str(
                output_path
            )

            st.session_state.render_complete = True

            status.success(
                "Trailer rendered successfully!"
            )

        except Exception as error:

            st.error("Rendering failed.")

            st.exception(error)

# ----------------------------------------------------------
# Download Section
# ----------------------------------------------------------

if (
    st.session_state.render_complete
    and st.session_state.output_video
):

    st.markdown("---")

    st.header("8️⃣ Download")

    st.video(st.session_state.output_video)

    with open(
        st.session_state.output_video,
        "rb"
    ) as video_file:

        st.download_button(
            label="⬇ Download Trailer",
            data=video_file,
            file_name=output_filename,
            mime="video/mp4",
            use_container_width=True,
        )

# ----------------------------------------------------------
# Footer
# ----------------------------------------------------------

st.markdown("---")

st.caption(
    "AI Trailer Studio • Streamlit • MoviePy 2.x • gTTS"
)
