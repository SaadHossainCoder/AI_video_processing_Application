from utils.audio_processor import process_input
from core.transcriber import transcribe_all

source = "https://youtu.be/KnviRvdmFTc?si=SMl8immXRpOhLB8a"

chunks = process_input(source)

print(transcribe_all(chunks))