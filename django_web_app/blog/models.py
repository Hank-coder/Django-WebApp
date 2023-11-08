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
    # platform是一个ForeignKey到Platform表的模型。这意味着您可以通过post.platform.name直接访问与某个帖子相关的平台的名称
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


#  Post_Photo_Category:里面存的就是post和category的一对多关系   ： 定义Through模型
class Post_Photo_Category(models.Model):
    # 这个模型是一个"through"模型，用于在Django中表示两个模型之间的多对多关系。
    # 在这种情况下，Post和Category有一个多对多的关系，表示一个Post可以有多个Category，
    # 同时一个Category也可以与多个Post关联。

    # ForeignKey到Post模型。每个记录都链接到一个Post。
    post = models.ForeignKey(Post, on_delete=models.CASCADE, default="none")
    # ForeignKey到Category模型。每个记录都链接到一个Category。
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)

    class Meta:
        # 这里的Meta类定义了模型的一些元数据。

        # 设置为False表示Django的迁移系统不会管理这个模型的数据库表。
        # 这意味着Django不会为这个模型自动创建、修改或删除数据库表。
        # 如果您需要在数据库中有这个表，您必须手动创建它。
        managed = False


class PostAudio(models.Model):
    request = models.TextField(default="no record")
    generate_text = models.TextField(default="no text")
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=255, default="0")  # 新增的字段

    def __str__(self):
        return self.generate_text

    # 你在 Post 模型中定义的 get_absolute_url 方法告诉 Django 创建或更新成功后应该重定向到哪里。
    # def get_absolute_url(self):
    #     return reverse('post-detail', kwargs={'pk': self.pk})


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 关联到用户
    conversation_id = models.CharField(max_length=255, unique=True)  # 用字符串表示的对话ID
    title = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)  # 关联到对话
    role = models.CharField(max_length=20)  # 角色，例如'sender', 'receiver'等
    content = models.TextField()  # 消息内容
    timestamp = models.DateTimeField(auto_now_add=True)  # 记录消息的发送时间
    imageUrl = models.CharField(max_length=255, default="")

