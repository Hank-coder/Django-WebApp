from django.test import TestCase

# Create your tests here.
from sympy import symbols, Eq, solve

from pathlib import Path
import openai

speech_file_path = Path(__file__).parent / "speech.mp3"
response = openai.audio.speech.create(
  model="tts-1",
  voice="echo",
  input="The quick brown fox jumped over the lazy dog."
)
response.stream_to_file(speech_file_path)