from django.db import models
from django import forms
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
import os

from django.utils.crypto import get_random_string

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Language(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Platform(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Post(models.Model):
    file = models.FileField(null=True, blank=True, upload_to='Files')
    language = models.ForeignKey(Language, on_delete=models.CASCADE, default=1)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, default=1)
    photo_category = models.ManyToManyField(Category)  # 从数据库获取内容
    special_request = models.TextField(default="")
    generate_text = models.TextField(default="no text")
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.generate_text

    def extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension

    # 你在 Post 模型中定义的 get_absolute_url 方法告诉 Django 创建或更新成功后应该重定向到哪里。
    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})


class PostAudio(models.Model):
    request = models.TextField(default="no record")
    generate_text = models.TextField(default="no text")
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=20, default="0")  # 新增的字段

    def __str__(self):
        return self.generate_text

    # 你在 Post 模型中定义的 get_absolute_url 方法告诉 Django 创建或更新成功后应该重定向到哪里。
    # def get_absolute_url(self):
    #     return reverse('post-detail', kwargs={'pk': self.pk})


# Chat图片数据库
# class UploadedImage(models.Model):
#     image = models.ImageField(upload_to='uploaded_images/')



