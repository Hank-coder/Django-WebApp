from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
import os
from django.conf import settings
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)

from .detectImage.generate_text import generate_text
from .models import Post, Category
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

    def form_valid(self, form): # 后端处理
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
