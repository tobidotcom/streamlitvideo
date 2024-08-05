import streamlit as st
import requests
from moviepy.editor import TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from io import BytesIO
import tempfile

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

# Function to create a video clip from text and audio
def create_video_clip(text, audio_data, position):
    try:
        audio_clip = AudioFileClip(audio_data)
        duration = audio_clip.duration
        text_clip = TextClip(text, fontsize=24, color='white', size=(600, None), method='caption')
        text_clip = text_clip.set_position(position).set_duration(duration)
        return CompositeVideoClip([text_clip.set_audio(audio_clip)]).set_duration(duration)
    except Exception as e:
        st.error(f"Error creating video clip: {e}")
        raise

# Function to get available voices from OpenAI
def get_available_voices(openai_api_key):
    url = "https://api.openai.com/v1/audio/voices"
    headers = {
        "Authorization": f"Bearer {openai_api_key}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()["voices"]

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

    # Fetch available voices
    try:
        voices = get_available_voices(openai_api_key)
        voice_options = [voice["name"] for voice in voices]
    except Exception as e:
        st.error(f"Error fetching voices: {e}")
        voice_options = []

    prompt = st.text_input("Enter your video prompt:")
    selected_voice = st.selectbox("Select Voice", options=voice_options)

    if st.button("Generate Video"):
        if prompt:
            try:
                # Step 1: Generate story
                story = generate_story(prompt, openai_api_key)
                st.write("Generated Story:")
                st.write(story)

                # Step 2: Split story into dialogues
                dialogues = story.split("\n")
                video_clips = []

                # Step 3: Convert dialogues to speech and create video clips
                for i, dialogue in enumerate(dialogues):
                    if ':' in dialogue:
                        speaker, text = dialogue.split(":", 1)
                        audio_data = text_to_speech(text.strip(), selected_voice, openai_api_key)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
                            audio_file.write(audio_data)
                        position = ('left', 'center') if i % 2 == 0 else ('right', 'center')
                        video_clip = create_video_clip(dialogue, audio_file.name, position)
                        video_clips.append(video_clip)
                        st.write(f"Processed dialogue: {dialogue}")
                    else:
                        st.warning(f"Skipping invalid dialogue: {dialogue}")

                # Step 4: Concatenate video clips
                if video_clips:
                    try:
                        final_video = concatenate_videoclips(video_clips)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                            final_video.write_videofile(temp_file.name, fps=24)
                            st.video(temp_file.name)
                    except Exception as e:
                        st.error(f"Error creating final video: {e}")
                else:
                    st.error("No valid video clips were created. Please check the dialogues.")
            except Exception as e:
                st.error(f"Error generating video: {e}")

