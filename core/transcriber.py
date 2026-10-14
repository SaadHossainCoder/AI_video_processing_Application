import whisper
import os
import torch

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

_model = None

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def load_model():
    global _model

    if _model is None:
        device = get_device()
        print(f"Loading Whisper model '{WHISPER_MODEL}' on device: {device.upper()}...")
        _model = whisper.load_model(WHISPER_MODEL, device=device)
        print("Model loaded successfully")

    return _model


def transcribe_chunk(chunk_path: str, translate: bool = False) -> str:
    model = load_model()
    task = "translate" if translate else "transcribe"
    use_fp16 = torch.cuda.is_available()

    result = model.transcribe(chunk_path, task=task, fp16=use_fp16)
    return result["text"]


def transcribe_all (chunk: list, translate:bool = False ) -> str :

    full_transcribe = ""

    for i , chunk in enumerate(chunk) :
        print(f"Transcribing chunk {i+1} ")
        text = transcribe_chunk(chunk, translate= translate)
        full_transcribe+= text + " "
    print("Transcription completed")
    return full_transcribe