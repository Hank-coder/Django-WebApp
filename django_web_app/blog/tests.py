from django.test import TestCase

# Create your tests here.
from sympy import symbols, Eq, solve

from pathlib import Path
import openai

speech_file_path = Path(__file__).parent / "p7-2.mp3"
response = openai.audio.speech.create(
    model="tts-1",
    voice="shimmer",
    input="This graphical representation parallels concepts in Algebraic Geometry, where complex structures are projected onto simpler forms while preserving intrinsic relationships. Similarly, word embeddings compress the expansive, sparse lexical space into a denser, more manageable vector space. This process captures the nuanced semantic and syntactic relationships among words. It's akin to the preservation of fundamental properties in geometric transformations, demonstrating the elegant intersection of language processing and mathematical geometry."
)
response.stream_to_file(speech_file_path)
