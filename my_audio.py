

# https://github.com/idiap/coqui-ai-TTS

# Regeneration
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/your_tts")
tts.tts_to_file(
    text="corrected word",
    file_path="fixed_word.wav",
    speaker_wav="your_voice_sample.wav"
)



# Correction
from pydub import AudioSegment

audio = AudioSegment.from_file("audio.mp3")
replacement = AudioSegment.from_file("fixed_word.wav")

# Replace between 3.2s and 3.8s
corrected = audio[:3200] + replacement + audio[3800:]

corrected.export("corrected_audio.mp3", format="mp3")
