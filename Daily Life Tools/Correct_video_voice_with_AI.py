import streamlit as st
import ffmpeg
import os
import whisper
import pyttsx3
import requests
import time
import subprocess
from pydub import AudioSegment

def main():
    st.title(":green[VoiceWeaver]")

    azure_openai_key = "22ec84421ec24230a3638d1b51e3a7dc"
    azure_openai_endpoint = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"  # Replace with your actual endpoint URL

    video_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"])

    if video_file is not None and azure_openai_key and azure_openai_endpoint:        
        video_path = "temp_video.mp4"
        with open(video_path, "wb") as f:
            f.write(video_file.read())

        if st.button("Done"):
            try:
                temp_audio_path = extract_audio(video_path)

                temp_video_path = remove_audio(video_path)

                transcription_map = transcribe_audio_with_whisper(temp_audio_path)

                corrected_transcription_map = correct_transcriptions(azure_openai_key, azure_openai_endpoint, transcription_map)
                synthesized_audio_path = synthesize_audio_with_pyttsx3(corrected_transcription_map)

                output_video_path = replace_audio_in_video(temp_video_path, synthesized_audio_path)

                if os.path.exists(output_video_path):
                    st.video(output_video_path)
                else:
                    st.error("Final output video not found.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def extract_audio(video_path):
    audio_path = "temp_audio.wav"
    ffmpeg.input(video_path).output(audio_path, ac=1, ar='32k').run(overwrite_output=True, quiet=True)
    return audio_path

def remove_audio(input_video_path):
    output_video_path = 'temp_vid.mp4'
    try:
        command = [
            'ffmpeg', '-i', input_video_path, '-an', '-c:v', 'copy', output_video_path
        ]
        subprocess.run(command, check=True)
        return output_video_path
    except subprocess.CalledProcessError as e:
        print(f"Error removing audio: {e}")
        return None

def transcribe_audio_with_whisper(audio_path):
    """Transcribe audio using the Whisper model."""
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="en", verbose=True)
    transcription_map = {}

    for segment in result['segments']:
        start_time = segment['start']
        end_time = segment['end']
        time_key = f"{start_time:.2f}-{end_time:.2f}"
        text = segment['text'].strip()
        transcription_map[time_key] = text

    return transcription_map

def correct_transcriptions(azure_openai_key, azure_openai_endpoint, transcription_map):
    """Correct transcriptions using Azure OpenAI API."""
    headers = {
        "Content-Type": "application/json",
        "api-key": azure_openai_key
    }

    corrected_map = {}
    for time_key, text in transcription_map.items():
        data = {
            "messages": [{"role": "user", "content": f"Correct this transcription even if it's correct, give me only the correct sentence and nothing else: '{text}'"}],
            "max_tokens": 100
        }
        try:
            response = requests.post(azure_openai_endpoint, headers=headers, json=data)
            if response.status_code == 429:
                st.warning(f"Rate limit exceeded. Retrying after 1 second for [{time_key}]...")
                time.sleep(1)
                response = requests.post(azure_openai_endpoint, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                corrected_text = result["choices"][0]["message"]["content"].strip()
                corrected_map[time_key] = corrected_text
            else:
                st.error(f"Error correcting transcription for [{time_key}]: {response.status_code} - {response.text}")
                corrected_map[time_key] = text

        except requests.exceptions.RequestException as e:
            st.error(f"Request failed for [{time_key}]: {str(e)}")
            corrected_map[time_key] = text

    return corrected_map

def synthesize_audio_with_pyttsx3(transcription_map):
    """Synthesize audio from corrected transcription using pyttsx3."""
    engine = pyttsx3.init()
    engine.setProperty('volume', 1.0)

    combined_audio = AudioSegment.silent(duration=0)

    for time_key, text in transcription_map.items():
        start, end = map(float, time_key.split('-'))
        start_ms = int(start * 1000)
        end_ms = int(end * 1000)
        target_duration = end_ms - start_ms
        
        words = text.split()
        word_count = len(words)
        desired_duration = target_duration / 1000  

        if desired_duration > 0:
            speech_rate = (word_count / desired_duration) * 60 
        else:
            speech_rate = 100

        engine.setProperty('rate', int(speech_rate))

        temp_audio_path = f"audio_{time_key}.wav"
        engine.save_to_file(text, temp_audio_path)
        engine.runAndWait()
        segment_audio = AudioSegment.from_wav(temp_audio_path)

        if start_ms > len(combined_audio):
            silence_gap = start_ms - len(combined_audio)
            combined_audio += AudioSegment.silent(duration=silence_gap)

        combined_audio += segment_audio
        os.remove(temp_audio_path)

    combined_audio.export("final_audio.wav", format="wav")
    return "final_audio.wav"

def replace_audio_in_video(video_path, audio_path):
    """Replace audio in video using ffmpeg."""
    output_path = 'final_video.mp4'
    try:
        os.system(f'ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac {output_path}')
        os.remove(video_path)
        os.remove(audio_path)
        return output_path  
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        os.remove(video_path)
        os.remove(audio_path)
        return None

if __name__ == "__main__":
    main()
