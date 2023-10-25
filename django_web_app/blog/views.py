import json
import re

import openai
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
import os
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from json import loads, dumps
from datetime import datetime

from pytesseract import pytesseract
from requests import get, post
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)

from .chatPages.server.config import special_instructions
from .detectImage.detectVoice.audio2text import gpt_audio_response, gpt_text_response
from .detectImage.gpt_generate import generate_image
from .detectImage.image2text import generate_text
from .detectImage.utils import get_apikey, fetch_search_results
from .models import Post, Category, PostAudio
import operator
from django.urls import reverse_lazy
from django.contrib.staticfiles.views import serve

from django.db.models import Q
from django.contrib import messages
from django import forms
from .models import Post


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


class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    paginate_by = 2

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'


class PostForm(forms.ModelForm):  # 定义的表单
    class Meta:
        model = Post
        fields = ['file', 'language', 'platform', 'photo_category', 'special_request']

    photo_category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={'size': '10'}))


class PostCreateView(LoginRequiredMixin, CreateView):  # 朋友圈文本生成
    template_name = 'blog/post_form.html'
    # fields = ['file', 'language', 'platform', 'photo_category', 'special_request']
    form_class = PostForm  # 使用我们定义的表单

    def form_valid(self, form):  # 后端处理
        form.instance.author = self.request.user

        # First save the form to ensure that the file is saved
        response = super().form_valid(form)

        # # Notify user that the processing is starting
        # messages.info(self.request, "Processing started. Please wait...  文本生成中")

        # Now, the file should be saved and we can get its path
        relative_path = self.object.file.name
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        other_data = {
            'language': form.cleaned_data['language'],
            'platform': form.cleaned_data['platform'],
            'photo_category': form.cleaned_data['photo_category'],
            'special_request': form.cleaned_data['special_request'],
        }
        # Check for empty values
        if not full_path or not other_data:
            messages.error(self.request, "The file path or other data is missing. Please try again.")
            return response

        generated_text = generate_text(full_path, other_data)
        self.object.generate_text = generated_text
        self.object.save()  # Save the updated data

        # Notify user that the processing is done
        messages.success(self.request, "Processing completed successfully! 生成成功！")

        return response


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    template_name = 'blog/post_form.html'
    fields = ['file', 'language', 'platform', 'photo_category', 'special_request']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'
    template_name = 'blog/post_confirm_delete.html'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})


class GPTAudioCreateView(LoginRequiredMixin, CreateView):
    model = PostAudio
    template_name = 'blog/gpt_audio.html'
    fields = ['request', 'generate_text', 'chat_id']

    @method_decorator(csrf_exempt)  # 确保这个view可以被上面的JS代码POST
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    # 处理提交的文件
    def post(self, request, *args, **kwargs):
        audio_file = request.FILES.get('audio')
        if audio_file:
            chat_id = request.POST.get('chat_id')
            # 获取上下文
            records = PostAudio.objects.filter(author=self.request.user, chat_id=chat_id).order_by('-date_posted')
            combined_request = ""
            if records:
                # 遍历查询集并从每个对象中获取request_data
                data_strings = [req_record.request for req_record in records]
                # 将所有的数据连接成一个字符串
                combined_request = ' '.join(data_strings)
            print(combined_request)

            response_data = gpt_audio_response(audio_file, self.request.user, combined_request)
            user_transcript = clean_text(response_data.get('user_transcript'))
            gpt_response = clean_text(response_data.get('gpt_response'))

            # 创建新的PostAudio对象并保存到数据库
            post_audio = PostAudio(author=self.request.user, request=user_transcript, generate_text=gpt_response,
                                   chat_id=chat_id)
            post_audio.save()

            # 如果想要在响应中返回更多数据，您可以在此处修改
            return JsonResponse(response_data, status=200)  # user_transcript, gpt_response

        return JsonResponse({'message': 'No audio received.'}, status=400)


class GPTAudioUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = PostAudio

    @method_decorator(csrf_exempt)  # 确保这个view可以被上面的JS代码POST
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        # template_name = 'blog/post_form.html'
        # fields = ['request', 'generate_text', 'chat_id']  # 需要更新的字段
        try:
            data = json.loads(request.body)
            edited_text = data.get('text')
            chat_id = data.get('chat_id')

            # 寻找相同chat_id并检索最新的date_posted数据
            record = PostAudio.objects.filter(chat_id=chat_id).order_by('-date_posted').first()

            if record:
                # 更新并保存记录
                # 查询上下文
                records = PostAudio.objects.filter(author=self.request.user, chat_id=chat_id).order_by('-date_posted')
                combined_request = ""
                if records:
                    # 遍历查询集并从每个对象中获取request_data
                    data_strings = [req_record.request for req_record in records]
                    # 将所有的数据连接成一个字符串
                    combined_request = ' '.join(data_strings)
                print(combined_request)

                record.request = clean_text(edited_text)
                record.generate_text = clean_text(gpt_text_response(edited_text, combined_request).get('gpt_response'))
                record.date_posted = timezone.now()
                record.save()
                # print(gpt_text_response(edited_text).get('gpt_response'))
                # 返回成功信息和更新后的文本
                return JsonResponse(gpt_text_response(edited_text, combined_request), status=200)

            else:
                # 如果没有找到匹配的记录
                return JsonResponse({"success": False, "error": "Record not found"})

        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "error": "Record not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def test_func(self):
        return True


# 不登陆也能访问
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
            body_data = loads(body_unicode)

            jailbreak = body_data['jailbreak']
            internet_access = body_data['meta']['content']['internet_access']
            _conversation = body_data['meta']['content']['conversation']
            prompt = body_data['meta']['content']['parts'][0]
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_message = f'You are ChatGPT also known as ChatGPT, a large language model trained by OpenAI. ' \
                             f'Strictly follow the users instructions.' \
                             f' Knowledge cutoff: 2021-09-01 Current date: {current_date}'

            extra = []
            query_content = prompt["content"]  # 假设 prompt 已经定义
            internet_access = True  # 或根据需要设置
            result_count = 3
            extra = fetch_search_results(query_content, internet_access, result_count)

            conversation = [{'role': 'system', 'content': system_message}] + \
                           extra + special_instructions[jailbreak] + \
                           _conversation + [prompt]
            # print(conversation)
            url = f"{self.openai_api_base}/v1/chat/completions"

            # 给openai发送请求
            gpt_resp = post(
                url=url,
                headers={
                    'Authorization': f'Bearer {self.openai_key}'
                },
                json={
                    'model': body_data['model'],
                    'messages': conversation,
                    'stream': True
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


class ImageCreateView(LoginRequiredMixin, CreateView):
    template_name = 'blog/image_create.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
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
        # render是Django的一个核心函数，用于将数据渲染到模板并返回一个HTTP响应。它是Django
        # 模板系统的一个关键部分，允许您将Python字典中的数据传递到HTML模板，并在模板中显示这些数据。


# 入数据库
# class ImageUploadForm(forms.ModelForm):
#     class Meta:
#         model = UploadedImage
#         fields = ['image']


class GPTImageView(CreateView):

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        uploaded_image = request.FILES.get('croppedImage')
        if uploaded_image:
            # 创建一个文件名
            filename = '{}.png'.format(datetime.now().strftime('%Y%m%d%H%M%S%f'))

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
                extracted_text = re.sub(r'^[\s\n]+', '', extracted_text)

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


def clean_text(text):
    # 去除换行
    cleaned_text = text.replace('\n', ' ')
    # 去除制表符
    cleaned_text = cleaned_text.replace('\t', ' ')

    # 如果文本长度小于或等于500，直接返回
    if len(cleaned_text) <= 1500:
        return cleaned_text

    # 如果文本长度超过500，找到最后一个句号、问号或感叹号
    cutoff = 1500
    while cutoff > 0:
        if cleaned_text[cutoff] in ['.', '!', '?']:
            break
        cutoff -= 1

    # 如果在前500个字符中没有找到句子结束的标点符号，返回前500个字符
    if cutoff == 0:
        return cleaned_text[:1500]

    # 否则，返回到最后一个句子结束的位置
    return cleaned_text[:cutoff + 1]
