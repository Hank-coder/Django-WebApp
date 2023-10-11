import os

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

        # Print the file path for debugging purposes
        print(file_path)

        # 返回一个响应
        return file_path

    # Handle the case where no audio file was provided
    return JsonResponse({'message': 'No audio file provided.'}, status=400)
