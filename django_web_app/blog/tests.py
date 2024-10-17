from django.test import TestCase
from openai import OpenAI

# Create your tests here.
from sympy import symbols, Eq, solve
#
# from pathlib import Path
# import openai
#
# speech_texts = [
#     "Good afternoon, boys and girls. Let's talk about computers.",
#     "First, computers are great for chatting. You can send emails, talk with friends over the internet, and even see each other using video calls. It's like magic mail that sends your message in seconds!",
#     "Second, they're our own entertainment center. You can play games, watch cartoons, and enjoy your favorite songs.",
#     "Third, computers are like a giant book that never ends. They're perfect for schoolwork and learning on websites, watching educational videos, and even taking fun quizzes to test your knowledge!",
#     "Fourth, you can use computers to draw, write essays, and make cool presentations for class.",
#     "Fifth, computers help people in all kinds of jobs—from building skyscrapers to flying planes. Even doctors use them to figure out how to make us feel better!",
#     "Last, just think—computers have become a big part of our lives. They're tools for talking, having fun, learning new stuff, and even helping us with our future jobs. Isn't that awesome? Keep exploring and who knows? Maybe you'll invent a new way to use computers!"
# ]
#
#
# for i, text in enumerate(speech_texts):
#     speech_file_path = Path(__file__).parent / f"part{i}.mp3"
#     response = openai.audio.speech.create(
#         model="tts-1",
#         voice="alloy",
#         input=text
#     )
#     response.stream_to_file(speech_file_path)
# response.stream_to_file(speech_file_path)


from pydub import AudioSegment
from pydub.utils import make_chunks
from openai import OpenAI
import os

# 初始化 OpenAI 客户端
client = OpenAI()

# 打开音频文件
audio_file = AudioSegment.from_file("C://Users//12084\OneDrive\文档\WeChat Files\wxid_g7ehsy3yd8or22\FileStorage\File//2024-01//23泉州一检听力.mp3", format="mp3")

# 将音频文件拆分成20秒的片段
chunks = make_chunks(audio_file, 60 * 1000)  # 20秒转换为毫秒

# 创建一个文件来保存结果
output_file = open("transcription_result.txt", "w")

# 逐个处理每个20秒的音频片段
for i, chunk in enumerate(chunks):
    chunk.export("temp_chunk_{}.wav".format(i), format="wav")  # 将片段导出为临时的wav文件
    with open("temp_chunk_{}.wav".format(i), "rb") as temp_audio_file:
        # 传递音频片段给 API 进行处理
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=temp_audio_file,
            response_format="text"
        )
        # 将处理结果写入输出文件
        output_file.write("{}\n".format(transcript))
    os.remove("temp_chunk_{}.wav".format(i))  # 删除临时的wav文件

output_file.close()  # 关闭输出文件
