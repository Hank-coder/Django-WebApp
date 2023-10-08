from PIL.ExifTags import TAGS
from django.forms import model_to_dict

from ultralytics import YOLO
import re
import shutil

import os
import utils

from .utils import extract_exif_info
# Generate the message
from .gpt_connect import generate_system_message


def generate_text(file_path, other_data):
    # 删除指定的文件夹及其所有内容
    if os.path.exists('image_detect'):
        # 如果存在，则删除文件夹及其所有内容
        shutil.rmtree('image_detect')

    if file_path:  # 检查用户是否选择了一个文件
        # Load a model
        model = YOLO('yolov8n-cls.pt')  # load an official model
        # model = YOLO('path/to/best.pt')  # load a custom model

        # Predict with the model
        results = model.predict(source=file_path, project="image_detect", save_txt=True)  # predict
        # on an image

        # 创建一个空字典来保存结果
        results_dict_cls = {}


        # 从文件名中获取图像的基本名（不带扩展名）
        base_name = os.path.basename(os.path.splitext(file_path)[0])

        # 构建结果文件的路径
        result_file_path = f'image_detect/predict/labels/{base_name}.txt'

        # 打开并读取文件
        with open(result_file_path, 'r') as file:
            # 循环遍历文件的每一行
            for line in file:
                # 分割每一行的内容
                confidence, label = line.strip().split(' ')
                # 将置信度转换为浮点数，并将结果保存到字典中
                results_dict_cls[label] = float(confidence)

        # 打印结果字典
        print(results_dict_cls)

    else:
        print('No file selected.')
    exif_data, gps_info = extract_exif_info(file_path)
    # 创建一个字典来保存EXIF数据
    exif_dict = {}

    if exif_data is not None:
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            exif_dict[tag_name] = value  # 将数据添加到字典中，而不是打印它

    # 这是您想要保留的键的列表
    keys_to_keep = [
        'DateTimeOriginal', 'Model', 'OffsetTimeOriginal',
        'ExposureTime', 'ISOSpeedRatings', 'FNumber',
        'LensSpecification', 'LensModel'
    ]

    # 创建一个新字典来保存过滤后的数据
    filtered_dict = {key: exif_dict[key] for key in keys_to_keep if key in exif_dict}

    # 现在，filtered_dict 包含了所有您想要保留的键和它们的值
    print(filtered_dict)
    # 现在，exif_dict 包含了所有的EXIF数据，您可以随时访问或处理它
    if gps_info is not None:
        exif_dict['GPS'] = gps_info
    chatgpt_response = generate_system_message(other_data, results_dict_cls, exif_dict)

    return chatgpt_response
