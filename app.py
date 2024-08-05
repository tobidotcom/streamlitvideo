import streamlit as st
import requests
from moviepy.editor import VideoClip, concatenate_videoclips, TextClip, CompositeVideoClip
from io import BytesIO
import tempfile
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

# Function to convert text to speech using ElevenLabs
def text_to_speech(text, voice_id, elevenlabs_api_key):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Authorization": f"Bearer {elevenlabs_api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.content

# Function to create a video clip from text and audio
def create_video_clip(text, audio_data, duration, position):
    try:
        text_clip = TextClip(text, fontsize=24, color='white', size=(600, None), method='caption')
        text_clip = text_clip.set_position(position).set_duration(duration)
        audio_clip = VideoClip(lambda t: None, duration=duration).set_audio(audio_data)
        return CompositeVideoClip([text_clip, audio_clip])
    except Exception as e:
        st.error(f"Error creating video clip: {e}")
        raise

# Streamlit UI
st.title("AI Video Generator")

# Settings Menu
with st.sidebar:
    st.header("Settings")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    elevenlabs_api_key = st.text_input("ElevenLabs API Key", type="password")
    voice_id_1 = st.text_input("Voice ID 1", value="voice_id_1")
    voice_id_2 = st.text_input("Voice ID 2", value="voice_id_2")
    
    if st.button("Save API Keys"):
        st.session_state["openai_api_key"] = openai_api_key
        st.session_state["elevenlabs_api_key"] = elevenlabs_api_key
        st.session_state["voice_id_1"] = voice_id_1
        st.session_state["voice_id_2"] = voice_id_2
        st.success("API keys saved!")

# Check if API keys are available
if "openai_api_key" not in st.session_state or "elevenlabs_api_key" not in st.session_state:
    st.warning("Please enter your API keys in the settings menu.")
else:
    prompt = st.text_input("Enter your video prompt:")
    if st.button("Generate Video"):
        if prompt:
            openai_api_key = st.session_state["openai_api_key"]
            elevenlabs_api_key = st.session_state["elevenlabs_api_key"]
            voice_id_1 = st.session_state["voice_id_1"]
            voice_id_2 = st.session_state["voice_id_2"]
            
            # Step 1: Generate story
            try:
                story = generate_story(prompt, openai_api_key)
                st.write("Generated Story:")
                st.write(story)
            except Exception as e:
                st.error(f"Error generating story: {e}")
                st.stop()
            
            # Step 2: Split story into dialogues
            dialogues = story.split("\n")
            audio_clips = []
            video_clips = []
            
            # Step 3: Convert dialogues to speech and create video clips
            try:
                for i, dialogue in enumerate(dialogues):
                    if ':' in dialogue:
                        speaker, text = dialogue.split(":", 1)
                        voice_id = voice_id_1 if i % 2 == 0 else voice_id_2
                        audio_data = text_to_speech(text.strip(), voice_id, elevenlabs_api_key)
                        audio_clip = BytesIO(audio_data)
                        duration = len(audio_data) / 32000  # Estimate duration from audio size (assuming 32 kbps)
                        position = ('left', 'center') if i % 2 == 0 else ('right', 'center')
                        video_clip = create_video_clip(dialogue, audio_clip, duration, position)
                        video_clips.append(video_clip)
            except Exception as e:
                st.error(f"Error processing dialogues: {e}")
                st.stop()
            
            # Step 4: Concatenate video clips
            try:
                final_video = concatenate_videoclips(video_clips)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                    final_video.write_videofile(temp_file.name, fps=24)
                    st.video(temp_file.name)
            except Exception as e:
                st.error(f"Error creating final video: {e}")
                st.stop()
