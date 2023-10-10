import openai

# Set the API base URL and key (ensure these values are stored securely)
openai.api_key = "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"


def generate_system_message(user_inputs, results_dict_cls, exif_dict):
    system_message = ""
    categories = user_inputs['photo_category']
    category_names = [str(category) for category in categories]
    category_str = ', '.join(category_names)
    if user_inputs['platform'].name == 'WeChat' or user_inputs['platform'].name == 'Xiaohongshu':
        system_message = f"""
        
        You will be act to share a {user_inputs['platform']} Moments and only use {user_inputs['language']} language 
        as output. \
        
        
        You should put more focus on {category_str} and here is the special requirement from client: 
        {user_inputs['special_request']}. \
        
        I will provide the result from yolov8 and exif_data and you can use for detect time and objects to assist you 
        generating the Moments.\
        
        yolov8n result are {str(results_dict_cls)}, select the most possible object to expand description, do not
        mentioned probability in output.  
        {str(results_dict_cls)} \
        
        exif_information are following {str(exif_dict)}, ONLY attention to DateTimeOriginal (Time) and ignore others \
        
        
        Refer to the format that most people send {user_inputs['platform']} moments and avoid jargon to output text
        """
        print(system_message)
    else:
        system_message = f"""
              
              You will be act as Professional photography reviewer for 1x.com and only use {user_inputs['language']} language as output.\ 
              You should put more focus on {category_str} and here is the special requirement from client
              {user_inputs['special_request']}. \

              I will provide the result from yolov8n-cls and exif_data to assist you generate the description for time and objects,
              these result are in dictionary format.\

              yolov8n-cls result as 'OBJECT':probability format, select the most possible to expand description,do not
              mentioned probability in output.  
              {str(results_dict_cls)} \

              exif_information are following, attention to Time which is described in terms of DateTimeOriginal and 
              describe in photographic terms based on other information. 
              {str(exif_dict)}\

              Refer to the format that most people send {user_inputs['platform']} and output text
              """

    message = get_completion_messages(system_message)
    return get_completion_from_messages(message)


# 用chatgpt每个查询的类别生成5个选择题

def get_completion_messages(system_message):
    return [
        {
            'role': 'system',
            'content': system_message
        }
    ]


def get_completion_from_messages(
        messages,
        model="gpt-4",
        temperature=0.8,
        max_tokens=3000
):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message["content"]
