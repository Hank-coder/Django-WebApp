import os
import subprocess

from django.conf import settings
from django.http import JsonResponse


def save_audio_file(audio_file, user_info):
    if audio_file:
        # Extract the original file's extension
        file_extension = os.path.splitext(audio_file.name)[1]

        # Create a new file name with user info and original extension
        new_file_name = f"{user_info}_{audio_file.name}"

        # Build the full file path
        file_path = os.path.join(settings.BASE_DIR, "blog", "detectImage", "detectVoice", "record", new_file_name)

        # Ensure the directory exists
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)

        # switch webm to wav to access chatgpt

        # 调用上述函数
        convert_webm_to_wav(file_path,
                            file_path.replace('.webm', '.wav'))

        # 转换文件
        # Print the file path for debugging purposes
        print(file_path.replace('.webm', '.wav'))

        # 返回一个响应
        return file_path.replace('.webm', '.wav')

    # Handle the case where no audio file was provided
    return JsonResponse({'message': 'No audio file provided.'}, status=400)


# switch webm to wav to access chatgpt
def convert_webm_to_wav(input_path, output_path):
    command = ['ffmpeg', '-y', '-i', input_path, output_path]
    subprocess.run(command)
