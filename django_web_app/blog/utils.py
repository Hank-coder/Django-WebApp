import json


def convert_string_to_list(image_url_str):
    # 将单引号替换为双引号
    corrected_str = image_url_str.replace("'", '"')
    try:
        # 尝试将修正后的字符串转换为列表
        image_list = json.loads(corrected_str)
        # 确保结果是列表
        if isinstance(image_list, list):
            return image_list
    except json.JSONDecodeError:
        # 如果转换失败，记录错误或进行一些错误处理
        print("Error: imageUrl is not a valid list in JSON format after correction.")
        return None

# def clean_text(text):
#     # 去除换行
#     cleaned_text = text.replace('\n', ' ')
#     # 去除制表符
#     cleaned_text = cleaned_text.replace('\t', ' ')
#
#     # 如果文本长度小于或等于500，直接返回
#     if len(cleaned_text) <= 1500:
#         return cleaned_text
#
#     # 如果文本长度超过500，找到最后一个句号、问号或感叹号
#     cutoff = 1500
#     while cutoff > 0:
#         if cleaned_text[cutoff] in ['.', '!', '?']:
#             break
#         cutoff -= 1
#
#     # 如果在前500个字符中没有找到句子结束的标点符号，返回前500个字符
#     if cutoff == 0:
#         return cleaned_text[:1500]
#
#     # 否则，返回到最后一个句子结束的位置
#     return cleaned_text[:cutoff + 1]
