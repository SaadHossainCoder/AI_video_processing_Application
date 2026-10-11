import yt_dlp
import os
from pydub import AudioSegment

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    yt_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(yt_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        filename = os.path.splitext(filename)[0] + ".wav"

    return filename


# download_audio_file = download_youtube_audio(
#     "https://youtu.be/s9w3gtgvNSU?si=DqJUOoQemt_vL3x5"
# )
# print(download_audio_file)

# convert the audio in wav & change the frame rate 16000
def convert_to_wav(input_path: str) -> str :
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0]+"_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format = "wav")
    return output_path

# convert_audio_file = convert_to_wav(download_audio_file)
# print(convert_audio_file)

# audio split int chunk
def chunk_audio(wav_path : str , chunk_minutes: int = 10 ) -> list :
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes*60*1000

    chunk_list = []

    for i, start in enumerate(range (0, len(audio), chunk_ms)) : 
        chunk = audio[start: start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path,format = "wav")
        chunk_list.append(chunk_path)

    return chunk_list

def process_input(source: str) -> list: 
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio ... ")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV ... ")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready - {len(chunks)} chunk(s) created.")
    return chunks