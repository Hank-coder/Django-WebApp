import json

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
import os
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)

from .detectImage.detectVoice.audio2text import gpt_audio_response, gpt_text_response
from .detectImage.generate_text import generate_text
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


class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 2


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


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['file', 'language', 'platform', 'photo_category', 'special_request']

    photo_category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={'size': '10'}))


class PostCreateView(LoginRequiredMixin, CreateView):
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
            response_data = gpt_audio_response(audio_file, self.request.user)
            user_transcript = response_data.get('user_transcript')
            gpt_response = response_data.get('gpt_response')
            chat_id = request.POST.get('chat_id')
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
                print(edited_text)
                record.request = edited_text
                record.generate_text = gpt_text_response(edited_text)
                record.date_posted = timezone.now()
                record.save()
                # print(gpt_text_response(edited_text))
                # 返回成功信息和更新后的文本
                return JsonResponse(gpt_text_response(edited_text), status=200)

            else:
                # 如果没有找到匹配的记录
                return JsonResponse({"success": False, "error": "Record not found"})

        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "error": "Record not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def test_func(self):
        return True
