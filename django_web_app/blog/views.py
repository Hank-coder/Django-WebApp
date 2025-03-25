"""
处理前端所有传过来的请求 根据template名称
"""

import base64
import json
import shutil
from urllib.parse import unquote

import openai
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseBadRequest, \
    FileResponse, HttpResponseNotFound
from django.contrib.auth.mixins import LoginRequiredMixin
import os
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from json import loads
from datetime import datetime, timedelta

from openai import OpenAI
from pytesseract import pytesseract
from requests import post
from django.views.generic import (
    ListView,
    CreateView,
    DeleteView
)

from .chatPages.server.config import special_instructions
from .functions.image_audio_generate.gpt_generate import generate_image
from .functions.ppt2script.ppt_script_gen import summarize_layout, auto_summary_ppt_page, load_json
from .functions.utils import get_apikey, fetch_search_results, get_apikey_dp
from .functions.email_reply.email_test import get_relate_emails,summary_infor
from .models import Category, PostAudio, ChatMessage, Conversation, DailyUsage, EmailAccount
from django.contrib.staticfiles.views import serve

from django.db.models import Q, F
from django.contrib import messages
from django import forms
from .models import Post
from PIL import Image
import io

from .utils import convert_string_to_list


def home(request):
    context = {
        'posts': Post.objects.all()
    }
    return render(request, 'blog/home.html', context)


def search(request):
    template = 'blog/home.html'

    query = request.GET.get('q')

    result = Post.objects.filter(
        Q(title__icontains=query) | Q(author__username__icontains=query) | Q(content__icontains=query))
    paginate_by = 2
    context = {'posts': result}
    return render(request, template, context)


def getfile(request):
    return serve(request, 'File')


# class PostListView(ListView):
#     model = Post
#     template_name = 'blog/home.html'  # <app>/<model>_<viewtype>.html
#     context_object_name = 'posts'
#     ordering = ['-date_posted']
#     paginate_by = 2

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'

# 发布记录
# class UserPostListView(ListView):
#     model = Post
#     template_name = 'blog/user_posts.html'  # <app>/<model>_<viewtype>.html
#     context_object_name = 'posts'
#     paginate_by = 4  # 一页显示4条
#
#     def get_queryset(self):
#         user = get_object_or_404(User, username=self.kwargs.get('username'))
#         #  prefetch_related('photo_category')  =》 through='Post_Photo_Category'
#         #  使用prefetch_related方法是为了优化数据库查询。当你在之后访问与Post对象关联的photo_category多对多关系时，
#         #  它将减少数据库查询的数量。在这里，与每个Post对象相关的photo_category将被预先加载，
#         #  这样当您循环遍历每个Post对象并访问其photo_category时，不需要为每个Post对象进行额外的数据库查询。
#         return Post.objects.filter(author=user).order_by('-date_posted').prefetch_related('photo_category')
#
#
# class PostDetailView(DetailView):
#     model = Post
#     template_name = 'blog/post_detail.html'

"""PPT 自动演讲"""
class ppt2speech(CreateView):
    model = Post
    fields = []
    template_name = 'blog/ppt_speech.html'


class UploadFileForm(forms.Form):
    file = forms.FileField()


class pptSave(LoginRequiredMixin, CreateView):
    model = Post

    @csrf_exempt  # csrf_exempt is only for demonstration purposes
    def post(self, request, *args, **kwargs):
        try:
            if 'file' in request.FILES:  # Case 1: File upload and initial processing
                form = UploadFileForm(request.POST, request.FILES)
                if form.is_valid():
                    file = request.FILES['file']
                    relative_path = os.path.join('uploaded_ppt', request.user.username)
                    save_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    if os.path.exists(save_path):
                        shutil.rmtree(save_path)

                    os.makedirs(save_path, exist_ok=True)
                    fs = FileSystemStorage(location=save_path)
                    filename = fs.save(file.name, file)
                    pptx_path = os.path.join(save_path, filename)

                    # Assume summarize_layout generates a 'layouts.json' file in save_path
                    summarize_layout(pptx_path, save_path)

                    # Generate speech text for the first page (index 1)  Start from page 1
                    current_page_index = 0
                    userRequest = '演讲的首页 默认语言中文'
                    speech_text_for_current_page = self.generate_speech_text(save_path, current_page_index, userRequest)

                    return JsonResponse({
                        'message': 'File uploaded and processed successfully!',
                        'pages': {f"page_{current_page_index}": speech_text_for_current_page}
                    }, status=200)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Form is not valid'}, status=400)
            else:  # Case 2: Subsequent slide content request
                data = json.loads(request.body)
                slide_index = data.get('slideIndex', 0)  # Default to first slide if not specified
                # print(slide_index)
                userRequest = data.get('userRequest')
                # print(userRequest)
                save_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_ppt', request.user.username)
                speech_text = self.generate_speech_text(save_path, slide_index, userRequest)
                # print(speech_text)
                return JsonResponse({'message': 'Slide content retrieved successfully!', 'content': speech_text},
                                    status=200)

        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON format")
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def generate_speech_text(self, save_path, page_index, user_request):
        # Load the content for all pages
        content_str_lst = load_json(os.path.join(save_path, 'layouts.json'))

        # Call a hypothetical function to generate speech text for the given page index
        speech_text_for_page = auto_summary_ppt_page(
            background=user_request,
            content_str_lst=content_str_lst,
            page=page_index,
            save_path=save_path,
            sentence_cnt=6,
            use_paid_API=True
        )
        return speech_text_for_page


class pptPlay(LoginRequiredMixin, CreateView):
    @csrf_exempt  # csrf_exempt is only for demonstration purposes
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            slide_index = data.get('slideIndex', '1')  # Default to first slide if not specified
            save_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_ppt', request.user.username)
            speech_file_path = os.path.join(save_path, f"speech_{slide_index}.mp3")

            # Check if the file already exists
            if not os.path.isfile(speech_file_path):
                text_content = data.get('text', '')
                client = OpenAI()

                # If the file does not exist, generate the speech
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text_content
                )
                response.stream_to_file(speech_file_path)

            # At this point, the file exists, so return it in the response
            return FileResponse(open(speech_file_path, 'rb'), as_attachment=True, content_type='audio/mpeg')

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def download_speech(request, slide_index):
    file_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_ppt', request.user.username, f"speech_{slide_index}.mp3")

    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), content_type='audio/mpeg')
    else:
        return HttpResponseNotFound('The requested mp3 was not found on the server.')


class PostForm(forms.ModelForm):  # 定义的表单
    class Meta:
        model = Post
        fields = ['file', 'language', 'platform', 'photo_category', 'special_request']

    # 指定photo_category从Category获得数据
    photo_category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={'size': '10'}))
#
# # 朋友圈文本生成
# class PostCreateView(LoginRequiredMixin, CreateView):
#     template_name = 'blog/post_form.html'
#     # fields = ['file', 'language', 'platform', 'photo_category', 'special_request']
#     form_class = PostForm  # 使用我们定义的表单
#
#     def form_valid(self, form):  # 后端处理
#         form.instance.author = self.request.user
#
#         # First save the form to ensure that the file is saved
#         # ['file', 'language', 'platform', 'photo_category', 'special_request'] 已经到数据库中了！
#         response = super().form_valid(form)
#
#         # # Notify user that the processing is starting
#         # messages.info(self.request, "Processing started. Please wait...  文本生成中")
#
#         # Now, the file should be saved and we can get its path
#         relative_path = self.object.file.name
#         full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
#
#         other_data = {
#             'language': form.cleaned_data['language'],
#             'platform': form.cleaned_data['platform'],
#             'photo_category': form.cleaned_data['photo_category'],
#             'special_request': form.cleaned_data['special_request'],
#         }
#         # Check for empty values
#         if not full_path or not other_data:
#             messages.error(self.request, "The file path or other data is missing. Please try again.")
#             return response
#
#         generated_text = generate_text(full_path, other_data)
#         self.object.generate_text = generated_text
#         self.object.save()  # Save the updated data
#
#         # Notify user that the processing is done
#         messages.success(self.request, "Processing completed successfully! 生成成功！")
#
#         return response

# 朋友圈文案更正
# class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
#     model = Post
#     template_name = 'blog/post_form.html'
#
#     def post(self, request, *args, **kwargs):
#         post_id = self.kwargs['pk']
#         post = get_object_or_404(Post, id=post_id)  # 数据库获取信息
#         new_content = request.POST.get("content")
#
#         if new_content:
#             post.generate_text = new_content
#             post.save()
#
#         return HttpResponseRedirect(self.get_success_url())
#
#     def test_func(self):
#         post = self.get_object()
#         if self.request.user == post.author:
#             return True
#         return False
#
#     def get_success_url(self):
#         return reverse('user-posts', kwargs={'username': self.request.user.username})

# 朋友圈文案删除
# class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
#     model = Post
#     success_url = '/'
#     template_name = 'blog/post_confirm_delete.html'
#
#     def test_func(self):
#         post = self.get_object()
#         if self.request.user == post.author:
#             return True
#         return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})

# GPT语音版
# class GPTAudioCreateView(LoginRequiredMixin, CreateView):
#     model = PostAudio
#     template_name = 'blog/gpt_audio.html'
#     fields = ['request', 'generate_text', 'chat_id']
#
#     @method_decorator(csrf_exempt)  # 确保这个view可以被上面的JS代码POST
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)
#
#     # 处理提交的文件
#     def post(self, request, *args, **kwargs):
#         audio_file = request.FILES.get('audio')
#         if audio_file:
#             chat_id = request.POST.get('chat_id')
#             # 获取上下文
#             records = PostAudio.objects.filter(author=self.request.user, chat_id=chat_id).order_by('-date_posted')
#             combined_request = ""
#             if records:
#                 # 遍历查询集并从每个对象中获取request_data
#                 data_strings = [req_record.request for req_record in records]
#                 # 将所有的数据连接成一个字符串
#                 combined_request = ' '.join(data_strings)
#             # print(combined_request)
#
#             response_data = gpt_audio_response(audio_file, self.request.user, combined_request)
#             user_transcript = clean_text(response_data.get('user_transcript'))
#             gpt_response = clean_text(response_data.get('gpt_response'))
#
#             # 创建新的PostAudio对象并保存到数据库
#             post_audio = PostAudio(author=self.request.user, request=user_transcript, generate_text=gpt_response,
#                                    chat_id=chat_id)
#             post_audio.save()
#
#             # 如果想要在响应中返回更多数据，您可以在此处修改
#             return JsonResponse(response_data, status=200)  # user_transcript, gpt_response
#
#         return JsonResponse({'message': 'No audio received.'}, status=400)
#
#
# class GPTAudioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
#     model = PostAudio
#
#     @method_decorator(csrf_exempt)  # 确保这个view可以被上面的JS代码POST
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)
#
#     def post(self, request, *args, **kwargs):
#         # template_name = 'blog/post_form.html'
#         # fields = ['request', 'generate_text', 'chat_id']  # 需要更新的字段
#         try:
#             data = json.loads(request.body)
#             edited_text = data.get('text')
#             chat_id = data.get('chat_id')
#
#             # 寻找相同chat_id并检索最新的date_posted数据
#             record = PostAudio.objects.filter(chat_id=chat_id).order_by('-date_posted').first()
#
#             if record:
#                 # 更新并保存记录
#                 # 查询上下文
#                 records = PostAudio.objects.filter(author=self.request.user, chat_id=chat_id).order_by('-date_posted')
#                 combined_request = ""
#                 if records:
#                     # 遍历查询集并从每个对象中获取request_data
#                     data_strings = [req_record.request for req_record in records]
#                     # 将所有的数据连接成一个字符串
#                     combined_request = ' '.join(data_strings)
#                 print(combined_request)
#
#                 record.request = clean_text(edited_text)
#                 record.generate_text = clean_text(gpt_text_response(edited_text, combined_request).get('gpt_response'))
#                 record.date_posted = timezone.now()
#                 record.save()
#                 # print(gpt_text_response(edited_text).get('gpt_response'))
#                 # 返回成功信息和更新后的文本
#                 return JsonResponse(gpt_text_response(edited_text, combined_request), status=200)
#
#             else:
#                 # 如果没有找到匹配的记录
#                 return JsonResponse({"success": False, "error": "Record not found"})
#
#         except ObjectDoesNotExist:
#             return JsonResponse({"success": False, "error": "Record not found"})
#         except Exception as e:
#             return JsonResponse({"success": False, "error": str(e)})
#
#     def test_func(self):
#         return True

"""GPT 问答功能"""
class GPTChatCreateView(CreateView):
    model = PostAudio
    template_name = 'blog/index.html'
    fields = ['request', 'generate_text', 'chat_id']
    openai_key = get_apikey(openai)
    openai_api_base = 'https://api.openai.com'

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:

            body_unicode = request.body.decode('utf-8')
            body_data = loads(body_unicode)  # 获取所有Body信息

            # 检查权限
            if body_data['model'] == 'gpt-4o' and (not request.user.is_authenticated):
                body_data['model'] = 'gpt-4o-mini'
            if body_data['model'] == 'gpt-4-turbo' and (not request.user.is_authenticated):
                body_data['model'] = 'gpt-4o-mini'
            if body_data['model'] in ['gpt-4-turbo', 'gpt-4o']:
                # 如果用户是 staff，则直接跳过使用限制检查
                if request.user.is_staff:
                    pass
                elif self.can_use_gpt4(request.user):  # 假设这个函数会更新使用次数并返回是否超过限制
                    # 如果用户未超过使用限制，可以继续使用 GPT-4
                    pass
                else:
                    # 如果用户超过了使用限制，更改模型为 GPT-3.5
                    body_data['model'] = 'gpt-4o-mini'

            jailbreak = body_data['jailbreak']
            internet_access = body_data['meta']['content']['internet_access']
            _conversation = body_data['meta']['content']['conversation']
            if not request.user.is_staff:
                _conversation = _conversation[-10:]
            # print(_conversation)
            # 定义公式
            # formula = '对话中存在的所有学科公式（数学物理化学经济等）,请使用LaTeX输出,并使用"$...$"格式包围(我将使用katex处理),不需要换行'

            # 删除掉imageUrl再上传api 因为imageUrl是我自定义的数组 并修改成openai格式
            # _conversation = [{key: value for key, value in message.items() if key != 'imageUrl'} for message in
            #                  _conversation]
            # 检查模型是否为 gpt-4-vision 来决定是否处理 imageUrl
            if body_data['model'] in ['gpt-4o', 'gpt-4-turbo']:

                uploaded_images = body_data['meta']['content']['uploaded_images']
                # print(uploaded_images)
                image_content_list = [{"type": "text", "text": "Here are the images for you."}]

                for image_path in uploaded_images:
                    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                    image_data = self.encode_image(full_path)
                    image_dict = {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                    image_content_list.append(image_dict)  # Append to the list

                # 遍历以前的信息
                for message in _conversation:
                    if 'imageUrl' in message:
                        if isinstance(message['imageUrl'], str):
                            # 尝试转换字符串表示的列表
                            image_list = convert_string_to_list(message['imageUrl'])
                            if image_list is not None:
                                message['imageUrl'] = image_list

                        # 继续处理，如果它现在是一个列表
                        if isinstance(message['imageUrl'], list) and message['imageUrl']:
                            content_list = [{"type": "text", "text": message['content']}]

                            for image_path in message['imageUrl']:
                                # 确保路径格式正确
                                image_path = os.path.join(settings.MEDIA_ROOT, image_path.strip())
                                base64_image = self.encode_image(image_path)
                                image_dict = {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                                content_list.append(image_dict)

                            message['content'] = content_list
                            del message['imageUrl']

            else:
                # 移除所有 imageUrl 键
                for message in _conversation:
                    if 'imageUrl' in message:
                        del message['imageUrl']

            prompt = body_data['meta']['content']['parts'][0]
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_message = f'You are ChatGPT also known as ChatGPT, a large language model trained by OpenAI. ' \
                             f'Strictly follow the instruction below:'

            extra = []
            query_content = prompt["content"]  # 假设 prompt 已经定义

            result_count = 3
            extra = fetch_search_results(query_content, internet_access, result_count)  # 联网搜索

            if body_data['model'] in ['gpt-4-turbo', 'gpt-4o']:
                conversation = [{'role': 'system', 'content': system_message}] + \
                               [{'role': 'user', 'content': image_content_list}] + \
                               extra + special_instructions[jailbreak] + \
                               _conversation + [prompt]
            else:
                conversation = [{'role': 'system', 'content': system_message}] + \
                               extra + special_instructions[jailbreak] + \
                               _conversation + [prompt]

            # 已经淘汰
            # # Check if the model is for vision and images have been uploaded
            # if body_data['model'] == 'gpt-4-vision-preview':
            #     uploaded_images = body_data['meta']['content']['uploaded_images']
            #     if uploaded_images:
            #         # Create vision messages for the uploaded images
            #         # print(prompt)
            #         vision_messages = self.create_vision_messages(uploaded_images=uploaded_images,
            #                                                       prompt=prompt['content'])
            #         # Append the vision messages to the conversation
            #         conversation = extra + special_instructions[jailbreak] + \
            #                        _conversation + [vision_messages]
            # print(conversation)

            # # 定义最新版本 turbo
            # if body_data['model'] == 'gpt-4':
            #     body_data['model'] = 'gpt-4o'
            #
            # if body_data['model'] == 'gpt-3.5':
            #     body_data['model'] = 'gpt-3.5-turbo-0125'

            # print(body_data['model'])
            # 给openai发送请求
            # gpt_resp = post(
            #     url=url,
            #     headers={
            #         'Authorization': f'Bearer {self.openai_key}'
            #     },
            #     json={
            #         'model': body_data['model'],
            #         'messages': conversation,
            #         'stream': True,
            #         "max_tokens": 2048
            #     },
            #     stream=True
            # )

            url = f"{self.openai_api_base}/v1/chat/completions"
            # 给Deepseek处理请求
            deep_seek_api = get_apikey_dp()
            url2 = "https://api.siliconflow.cn/v1"

            # Deepseek处理
            if body_data['model'] == 'deepseek-r1':
                client = OpenAI(api_key=deep_seek_api, base_url=url2)
                gpt_resp = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-R1",
                    messages=conversation,
                    stream=True
                )

                # 流式响应处理
                def event_stream():
                    reasoning_buffer = []  # 存储思考过程
                    result_buffer = []  # 存储最终结果
                    ans = False

                    for chunk in gpt_resp:
                        delta = chunk.choices[0].delta

                        # 处理思考过程
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            reasoning_buffer.append(delta.reasoning_content)
                            # 实时发送思考过程
                            yield f"{delta.reasoning_content}"

                        # 处理最终结果
                        if hasattr(delta, 'content') and delta.content:
                            result_buffer.append(delta.content)
                            # 如果有缓存的思考过程，先发送
                            if reasoning_buffer:
                                full_reasoning = "".join(reasoning_buffer)
                                yield f"{full_reasoning}"
                                reasoning_buffer = []  # 清空缓存
                            # 在发送最终结果时，在 content 前加入 "ANSWER:" 换行
                            if not ans:
                                yield "\n\n\n\n\n***Answer***:\n\n\n\n" + f"{delta.content}"
                                ans = True
                            else:
                                yield f"{delta.content}"

                return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
            # OpenAI处理
            else:
                gpt_resp = post(
                    url=url,
                    headers={
                        'Authorization': f'Bearer {self.openai_key}'
                    },
                    json={
                        'model': body_data['model'],
                        'messages': conversation,
                        'stream': True,
                        "max_tokens": 2048
                    },
                    stream=True
                )

                if gpt_resp.status_code >= 400:
                    error_data = gpt_resp.json().get('error', {})
                    error_code = error_data.get('code', None)
                    error_message = error_data.get('message', "An error occurred")
                    return JsonResponse({
                        'success': False,
                        'error_code': error_code,
                        'message': error_message,
                        'status_code': gpt_resp.status_code
                    }, status=gpt_resp.status_code)

                def stream():  # 流传输
                    for chunk in gpt_resp.iter_lines():
                        try:
                            decoded_line = loads(chunk.decode("utf-8").split("data: ")[1])
                            token = decoded_line["choices"][0]['delta'].get('content')

                            if token is not None:
                                yield token

                        except GeneratorExit:
                            break

                        except Exception as e:
                            # print(e)
                            continue

                return StreamingHttpResponse(stream(), content_type='text/event-stream')


        except Exception as e:
            print(e)
            return JsonResponse({
                '_action': '_ask',
                'success': False,
                'error': f'an error occurred {str(e)}'
            }, status=400)

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def create_vision_messages(self, uploaded_images, prompt):
        # Start with the text prompt
        message_content = [
            {"type": "text", "text": 'Strictly follow the users instructions: ' + prompt}]

        # Add each image to the message content
        for image_path in uploaded_images:
            full_path = os.path.join(settings.MEDIA_ROOT, image_path)
            image_data = self.encode_image(full_path)
            image_content = {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{image_data}"
            }
            message_content.append(image_content)

        # Create a single message with all contents
        vision_message = {
            "role": "user",
            "content": message_content,
        }

        return vision_message

    # GPT限额
    def can_use_gpt4(self, user):
        current_time = timezone.now()
        usage_record, created = DailyUsage.objects.get_or_create(user=user, defaults={'last_used_at': current_time})

        if not created and current_time - usage_record.last_used_at < timedelta(hours=12):
            if usage_record.usage_count >= 15:
                return False  # 在12小时内达到限额

        # 重置计数或增加使用次数
        if created or current_time - usage_record.last_used_at >= timedelta(hours=12):
            usage_count = 1
        else:
            usage_count = usage_record.usage_count + 1

        # 增加总使用次数
        DailyUsage.objects.filter(id=usage_record.id).update(
            last_used_at=current_time,
            usage_count=usage_count,
            total_count=F('total_count') + 1  # 使用 F 表达式确保原子性更新
        )
        return True


# 入库
class SaveChat(LoginRequiredMixin, CreateView):
    model = ChatMessage
    fields = ['content', 'sender', 'conversation_id']

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            user = request.user
            conversation_id = data.get('conversation_id')
            role = data.get('role')
            content = data.get('content')
            imageUrl = data.get('imageUrl')
            # 确保对话存在
            conversation, created = Conversation.objects.get_or_create(
                user=user,
                conversation_id=conversation_id,
            )

            # 如果对话是新创建的，可以添加标题
            conversation.title = content[:10]
            conversation.save()  # auto_now=True会自动为您处理时间更新

            # 添加消息到对话
            ChatMessage.objects.create(
                conversation=conversation,
                role=role,
                content=content,
                timestamp=timezone.now(),
                imageUrl=imageUrl,
            )

            return JsonResponse({'status': 'success', 'message': 'Message saved successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class LoadChat(LoginRequiredMixin, CreateView):

    def get(self, request, *args, **kwargs):
        user = request.user
        conversations_query = Conversation.objects.filter(user=user).order_by('-id')
        conversations = []
        last_updated = None

        for conversation in conversations_query:
            chat_messages = conversation.chatmessage_set.all().values('role', 'content', 'imageUrl')
            # 初始化对话列表
            conversation_items = []

            for message in chat_messages:
                # 如果imageUrl存在且不是'[]'，则将其添加到信息中
                if message['imageUrl'] and message['imageUrl'] != '[]':
                    # 可以进一步转换或处理imageUrl字段
                    # 例如：转换字符串格式的列表为Python列表
                    conversation_items.append({
                        'role': message['role'],
                        'content': message['content'],
                        'imageUrl': message['imageUrl']  # 假设这是一个有效的列表或非空字符串
                    })
                else:
                    # 不包含imageUrl的信息
                    conversation_items.append({
                        'role': message['role'],
                        'content': message['content']
                        # 不添加imageUrl字段
                    })

            # 添加对话到对话列表中
            conversations.append({
                'id': conversation.conversation_id,
                'title': conversation.title,
                'items': conversation_items,
            })

            if last_updated is None or conversation.last_updated > last_updated:
                last_updated = conversation.last_updated

        return JsonResponse({'conversations': conversations, 'last_updated': last_updated})


class DeleteChat(LoginRequiredMixin, CreateView):

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')

            # Check if the conversation exists and user owns it
            conversation = Conversation.objects.filter(conversation_id=conversation_id, user=request.user).first()
            if conversation:
                conversation.delete()

            # 删除本地图片文件夹
            relative_path = os.path.join('uploaded_gpt4_images', request.user.username, conversation_id)
            save_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            if os.path.isdir(save_path):  # 检查是否是一个目录
                shutil.rmtree(save_path)  # 删除文件夹及其所有内容

            return JsonResponse({'status': 'success', 'message': 'Conversation deleted successfully.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
# 入数据库
# class ImageUploadForm(forms.ModelForm):
#     class Meta:
#         model = UploadedImage
#         fields = ['image']

"""GPT 3.5只能文字输入 要图片转文字"""
class GPTImageView(CreateView):

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        uploaded_image = request.FILES.get('croppedImage')
        if uploaded_image:
            # 创建一个文件名
            filename = '{}.jpeg'.format(datetime.now().strftime('%Y%m%d%H%M%S%f'))

            # 定义保存路径
            save_path = os.path.join(settings.MEDIA_ROOT, 'uploaded_chat_images', filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 保存文件
            with open(save_path, 'wb+') as destination:
                for chunk in uploaded_image.chunks():
                    destination.write(chunk)

            try:
                extracted_text = pytesseract.image_to_string(save_path, lang='chi_sim+eng', timeout=30)
                extracted_text = extracted_text.strip()

                # 删除已经读取的图像文件
                os.remove(save_path)
            except RuntimeError as timeout_error:
                # Tesseract processing is terminated
                return JsonResponse({'status': 'error', 'message': 'Image processing failed!'}, status=400)

            return JsonResponse({
                'status': 'success',
                'message': 'Image saved successfully!',
                'extracted_text': extracted_text
            })

        else:
            return JsonResponse({'status': 'error', 'message': 'Image upload failed!'}, status=400)

# GPT4 图片处理
class GPT4ImageView(LoginRequiredMixin, CreateView):

    def post(self, request, *args, **kwargs):
        uploaded_image = request.FILES.get('croppedImage')
        conversation_id = request.POST.get('conversation_id')
        user = request.user
        # 确保对话存在
        conversation, created = Conversation.objects.get_or_create(
            user=user,
            conversation_id=conversation_id,
        )
        # 如果对话是新创建的，可以添加标题
        conversation.title = '输入图片'
        conversation.save()
        if uploaded_image:
            # Read the uploaded image file
            img = Image.open(uploaded_image)

            # Define the maximum size in KB
            max_size = 512

            # Convert to RGB (in case it's a different mode and if the image format allows it)
            if img.mode in ("RGBA", "P"):  # Adjust based on your requirements
                img = img.convert('RGB')

            # Adjust the quality until the file is below the maximum size
            quality = 70  # Start with a quality value
            img_io = io.BytesIO()
            while quality > 3:  # min quality
                img_io.seek(0)  # Reset file pointer to the beginning.
                img.save(img_io, format='JPEG', quality=quality)
                # Check the size without closing BytesIO
                if img_io.tell() <= max_size * 1024:
                    break
                quality -= 1  # Decrease quality

            # Reset the file pointer before saving to disk
            img_io.seek(0)

            # Save the processed image to the file system
            filename = '{}.jpeg'.format(datetime.now().strftime('%Y%m%d%H%M%S%f'))
            relative_path = os.path.join('uploaded_gpt4_images', user.username, conversation_id, filename)
            save_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, 'wb') as destination:
                destination.write(img_io.getvalue())

            file_url = request.build_absolute_uri(settings.MEDIA_URL + relative_path)

            return JsonResponse({
                'status': 'success',
                'message': 'Image saved successfully!',
                'file_path': file_url,
                'relative_path': relative_path
            })

        else:
            return JsonResponse({'status': 'error', 'message': 'Image upload failed!'}, status=400)


class DeleteGPT4Image(LoginRequiredMixin, DeleteView):

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            file_url = data.get('file_path')

            if not file_url:
                return JsonResponse({'status': 'error', 'message': 'No file path provided'}, status=400)

            # URL解码
            file_path = unquote(file_url)
            # 移除MEDIA_URL和之前的所有内容
            relative_path = file_path.split(settings.MEDIA_URL)[-1]
            save_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            if os.path.isfile(save_path):
                os.remove(save_path)
                return JsonResponse({'status': 'success'}, status=204)  # 204 No Content
            else:
                return JsonResponse({'status': 'file_not_found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class ImageCreateView(LoginRequiredMixin, CreateView):
    template_name = 'blog/image_create.html'

    # Django 通过 get 方法渲染并返回 image_create.html
    # 网页只是显示表单，用户还未提交数据
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
    # 处理表单提交
    def post(self, request, *args, **kwargs): # 表单提交的获取
        prompt = request.POST.get('prompt')

        if not prompt:
            messages.error(request, "Prompt cannot be empty.")
            return render(request, self.template_name)

        # 使用generate_image函数生成图像并获取保存路径
        image_path = generate_image(prompt, request.user.username)

        # 为简单起见，只是将图像的路径返回给用户。
        context = {
            'image_url': image_path  # 这里假设image_path是一个可以直接访问的URL
        }
        return render(request, self.template_name, context)
        # render是Django的一个核心函数，用于将数据渲染到模板并返回一个HTTP响应
        # 前端这样使用:
        # < img
        # src = "{{ image_url }}"
        # alt = "Generated Image"
        # style = "max-width: 100%;" >

"""自动生成邮件"""
@method_decorator(csrf_exempt, name='dispatch')
class EmailGeneralView(LoginRequiredMixin, CreateView):
    template_name = 'blog/email_reply.html'
    # 网页只是显示表单
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'is_reply': False})

"""自动回复邮件"""
@method_decorator(csrf_exempt, name='dispatch')
class EmailReplyView(LoginRequiredMixin, CreateView):
    template_name = 'blog/email_reply.html'

    # 网页只是显示表单，用户还未提交数据
    def get(self, request, *args, **kwargs):
        # 从数据库获取当前user的email信息
        user_id = request.session.get('_auth_user_id')
        email_data = EmailAccount.objects.get(user_id=user_id)
        user_email = email_data.email
        user_password = email_data.password

        # Check if user_email or user_password is empty
        if not user_email or not user_password:
            return render(request, self.template_name, {'is_reply': False})

        return render(request, self.template_name, {'is_reply': True})

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的JSON数据'}, status=400)
        # 获取表单提交信息
        contact_email = data.get('email')
        subject_keyword = data.get('keyword')
        user_id = request.session.get('_auth_user_id')

        # 从数据库获取当前user的email信息
        email_data = EmailAccount.objects.get(user_id=user_id)
        user_email = email_data.email
        user_password = email_data.password

        relate_email_infor = get_relate_emails(user_email, user_password, contact_email, subject_keyword)
        print(relate_email_infor)
       # 如果找到了匹配邮件
        if relate_email_infor:
            exists = True
        else:
            exists = False

        if exists:
            # 传输数据
            subject = relate_email_infor[0]['Subject']
            date = relate_email_infor[0]['Date']
            body = relate_email_infor[0]['Body']
            # 渲染模板 email_reply.html，可以传递需要在模板中显示的上下文数据
            # rendered_html = render(request, self.template_name, context).content.decode('utf-8')
            return JsonResponse({
                'exists': True,
                'email_infor': relate_email_infor,
                'subject': subject,
                'timestamp': date,
                'body': body
            })
        else:
            return JsonResponse({'exists': False})

# 传输生成的Email
@method_decorator(csrf_exempt, name='dispatch')
class EmailGenerate(LoginRequiredMixin, CreateView):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的JSON数据'}, status=400)

        user_id = request.session.get('_auth_user_id')
        content = summary_infor(data, user_id= user_id)

        # 在这里根据传入参数生成邮件主题和正文，可以调用相关算法或调用AI服务

        return JsonResponse({
            'content': content
        })

def check_user_logged_in(request):
    if request.user.is_authenticated:
        return JsonResponse({'status': 'logged_in'})
    else:
        return JsonResponse({'status': 'not_logged_in'})
