import whisper
import ffmpeg
import os
import threading
import time
import sys

def add_subtitles_to_video(input_video, output_video, sync_offset=-0.1):
    def extract_audio(video_path):
        audio_path = "temp_audio.wav"
        ffmpeg.input(video_path).output(audio_path, ac=1, ar='32k').run(overwrite_output=True, quiet=True)
        return audio_path

    def generate_srt(segments, srt_path, sync_offset):
        with open(srt_path, 'w', encoding='utf-8') as f:
            index = 1
            group_size = 6
            last_end_time = 0 
            for segment in segments:
                words = segment['words']
                for i in range(0, len(words), group_size):
                    group_words = words[i:i + group_size]
                    start = group_words[0]['start'] + sync_offset
                    end = group_words[-1]['end'] + sync_offset
                    if start < last_end_time:
                        start = last_end_time + 0.1
                    last_end_time = end
                    start_timestamp = format_timestamp(start)
                    end_timestamp = format_timestamp(end)
                    subtitle_text = ''.join([word_info['word'] for word_info in group_words])
                    f.write(f"{index}\n{start_timestamp} --> {end_timestamp}\n{subtitle_text}\n\n")
                    index += 1

    def format_timestamp(seconds):
        hrs, secs = divmod(seconds, 3600)
        mins, secs = divmod(secs, 60)
        millis = int((secs - int(secs)) * 1000)
        return f"{int(hrs):02}:{int(mins):02}:{int(secs):02},{millis:03}"

    def show_spinner(stop_event):
        spinner = ['|', '/', '-', '\\']
        colors = ['\033[92m', '\033[93m', '\033[94m', '\033[96m']
        i = 0
        while not stop_event.is_set():
            color = colors[i % len(colors)]
            sys.stdout.write(f"\r{color}Processing... {spinner[i % len(spinner)]}\033[0m")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def video_to_srt(video_path, srt_path):
        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=show_spinner, args=(stop_event,), daemon=True)
        spinner_thread.start()

        audio_path = extract_audio(video_path)
        model = whisper.load_model("medium")
        result = model.transcribe(audio_path, temperature=0.5, compression_ratio_threshold=2.4, word_timestamps=True)
        os.remove(audio_path)

        if 'segments' in result and result['segments']:
            generate_srt(result['segments'], srt_path, sync_offset)
        else:
            print("\033[91mNo segments found in transcription.\033[0m")
            stop_event.set()
            spinner_thread.join()
            return False
        
        stop_event.set()
        spinner_thread.join()
        return True
    
    def add_subtitles(video_path, srt_path, output_video_path):
        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=show_spinner, args=(stop_event,), daemon=True)
        spinner_thread.start()

        ffmpeg.input(video_path).output(
            output_video_path,
            vf=f"subtitles={srt_path}:force_style='FontName=Montserrat,FontSize=18,PrimaryColour=&HFFFFFF&'"
        ).run(overwrite_output=True, quiet=True)

        stop_event.set()
        spinner_thread.join()

    # SRT file path
    srt_file = "subtitles.srt"

    # Transcribe audio and generate subtitles
    transcription_success = video_to_srt(input_video, srt_file)

    if transcription_success and os.path.exists(srt_file):
        # Add subtitles to the video
        add_subtitles(input_video, srt_file, output_video)
        os.remove(srt_file)
    else:
        if os.path.exists(srt_file):
            os.remove(srt_file)
        return

# Usage
input_video = "sample.mp4"
output_video = "output_video.mp4"
add_subtitles_to_video(input_video, output_video, sync_offset=-0.1)
