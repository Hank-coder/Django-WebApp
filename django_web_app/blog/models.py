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


# Post图片保存路径
def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/Files/username/<filename>
    return 'Files/{0}/{1}'.format(instance.author.username, filename)


class Post(models.Model):
    file = models.FileField(upload_to=user_directory_path, null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, default=1)
    # platform是一个ForeignKey到Platform模型。这意味着您可以通过post.platform.name直接访问与某个帖子相关的平台的名称
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, default=1)
    # Post_Photo_Category（或之前提到的PostCategory）是一个"through"模型，
    # 用于在Django中表示两个模型之间的多对多关系。在这种情况下，Post和Category有一个多对多的关系，表示一个Post可以有多个Category，同时一个Category也可以与多个Post关联。

    photo_category = models.ManyToManyField(Category, through='Post_Photo_Category')  # 从数据库获取内容 数据对应表单为
    # Post_Photo_Category
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


# 定义Through模型
class Post_Photo_Category(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:  # migrate不要新建表
        managed = False


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
