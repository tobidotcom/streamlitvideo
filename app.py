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
def create_video_clip(text, audio_data):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as audio_file:
            audio_file.write(audio_data)
            audio_file_path = audio_file.name

        audio_clip = AudioFileClip(audio_file_path)
        duration = audio_clip.duration
        
        # Create a simple TextClip without ImageMagick
        text_clip = TextClip(text, fontsize=24, color='white', size=(600, None))
        text_clip = text_clip.set_position(('center', 'center')).set_duration(duration)
        
        return CompositeVideoClip([text_clip.set_audio(audio_clip)]).set_duration(duration)
    except Exception as e:
        st.error(f"Error creating video clip: {e}")
        raise

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

                # Step 2: Process the story as a single dialogue or split into chunks
                video_clips = []
                chunk_size = 500  # Maximum length of text chunk for TTS
                for i in range(0, len(story), chunk_size):
                    text_chunk = story[i:i + chunk_size]
                    audio_data = text_to_speech(text_chunk, selected_voice, openai_api_key)
                    video_clip = create_video_clip(text_chunk, audio_data)
                    video_clips.append(video_clip)
                    st.write(f"Processed text chunk: {text_chunk[:50]}...")

                # Step 3: Concatenate video clips
                if video_clips:
                    try:
                        final_video = concatenate_videoclips(video_clips)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                            final_video.write_videofile(temp_file.name, fps=24)
                            st.video(temp_file.name)
                    except Exception as e:
                        st.error(f"Error creating final video: {e}")
                else:
                    st.error("No valid video clips were created. Please check the story.")
            except Exception as e:
                st.error(f"Error generating video: {e}")
