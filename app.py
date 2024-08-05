import streamlit as st
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip, concatenate_videoclips, AudioFileClip
from io import BytesIO
import tempfile
import numpy as np
import os

# Function to generate story using OpenAI's chat/completions endpoint
def generate_story(prompt, openai_api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that writes stories."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150,
        "temperature": 0.7,
        "n": 1
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Function to convert text to speech using OpenAI
def text_to_speech(text, voice, openai_api_key):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "tts-1",
        "input": text,
        "voice": voice
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.content

# Function to create an image with text using PIL
def create_image_with_text(text, character, is_sent):
    img = Image.new('RGB', (640, 480), color = (255, 255, 255))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.load_default()  # Load default font
    except IOError:
        font = ImageFont.load_default()

    bubble_width = 600
    bubble_padding = 10
    bubble_color = "#d4f1f4" if is_sent else "#f1f1f1"
    
    # Calculate text bounding box
    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    bubble_height = text_height + 2 * bubble_padding
    
    # Draw the bubble background
    d.rectangle([(20, 20), (20 + bubble_width, 20 + bubble_height)], fill=bubble_color)
    
    # Draw the text on the bubble
    d.text((30, 30), text, font=font, fill="black")
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# Function to create a video clip from images and audio
def create_video_clip(text, audio_data, character, is_sent):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
        audio_file.write(audio_data)
        audio_file_path = audio_file.name

    audio_clip = AudioFileClip(audio_file_path)
    duration = audio_clip.duration

    img_bytes = create_image_with_text(text, character, is_sent)
    img_array = np.array(Image.open(img_bytes))
    
    # Save image temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as img_file:
        img_file.write(img_array.tobytes())
        img_file_path = img_file.name
    
    image_clip = ImageSequenceClip([img_file_path], fps=24)
    image_clip = image_clip.set_duration(duration).set_audio(audio_clip)
    
    # Clean up the temporary image file after use
    os.remove(img_file_path)
    
    return image_clip

# Manually specify available voices
available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Streamlit UI
st.title("AI Video Generator")

# Settings Menu
with st.sidebar:
    st.header("Settings")
    openai_api_key = st.text_input("OpenAI API Key", type="password")

    if st.button("Save API Key"):
        st.session_state["openai_api_key"] = openai_api_key
        st.success("API key saved!")

# Check if API key is available
if "openai_api_key" not in st.session_state:
    st.warning("Please enter your OpenAI API key in the settings menu.")
else:
    openai_api_key = st.session_state["openai_api_key"]

    prompt = st.text_input("Enter your video prompt:")
    selected_voice = st.selectbox("Select Voice", options=available_voices)

    if st.button("Generate Video"):
        if prompt:
            try:
                # Step 1: Generate story
                story = generate_story(prompt, openai_api_key)
                st.write("Generated Story:")
                st.write(story)

                # Split the story into alternating dialogues
                dialogues = [story[i:i + 300] for i in range(0, len(story), 300)]
                character_names = ["Alice", "Bob"]

                video_clips = []
                for i, dialogue in enumerate(dialogues):
                    character = character_names[i % len(character_names)]
                    audio_data = text_to_speech(dialogue, selected_voice, openai_api_key)
                    is_sent = i % 2 == 0
                    video_clip = create_video_clip(dialogue, audio_data, character, is_sent)
                    video_clips.append(video_clip)
                    st.write(f"Processed dialogue chunk: {dialogue[:50]}...")

                # Step 3: Concatenate video clips
                if video_clips:
                    try:
                        final_video = concatenate_videoclips(video_clips)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                            final_video.write_videofile(temp_file.name, fps=24)
                            st.video(temp_file.name)
                            os.remove(temp_file.name)  # Clean up temp file
                    except Exception as e:
                        st.error(f"Error creating final video: {e}")
                else:
                    st.error("No valid video clips were created. Please check the story.")
            except Exception as e:
                st.error(f"Error generating video: {e}")

