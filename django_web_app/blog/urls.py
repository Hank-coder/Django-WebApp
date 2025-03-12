from django.urls import path
from .views import (
    PostListView, ImageCreateView, GPTChatCreateView, GPTImageView, SaveChat, LoadChat,
    DeleteChat, GPT4ImageView, DeleteGPT4Image, ppt2speech, pptSave, pptPlay, a1_view,
)
from . import views


# URL 对应处理
urlpatterns = [
    path('', PostListView.as_view(), name='blog-home'),  # 首页

    # gpt基础聊天
    path('post/gptchat/', GPTChatCreateView.as_view(), name='gpt-chat'),
    path('post/savechat/', SaveChat.as_view(), name='save-chat'),
    path('post/loadchat/', LoadChat.as_view(), name='load-chat'),
    path('post/deletechat/', DeleteChat.as_view(), name='delete-chat'),
    # GPT图片处理
    path('post/gptchat/image', GPTImageView.as_view(), name='gpt-image'),
    path('post/gpt4/image', GPT4ImageView.as_view(), name='gpt4-image'),
    path('post/gpt4/image/delete', DeleteGPT4Image.as_view(), name='gpt4-image-delete'),
    # PPT演讲
    path('post/ppt2speech/', ppt2speech.as_view(), name='ppt-speech'),
    path('post/ppt2speech/save', pptSave.as_view(), name='ppt-speech-save'),
    path('post/ppt2speech/play', pptPlay.as_view(), name='ppt-speech-play'),
    path('download_speech/<int:slide_index>/', views.download_speech, name='download_speech'),
    # GPT语音版 已过时
    # path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    # path('post/gptnew/', GPTAudioCreateView.as_view(), name='gpt-audio'),
    # path('update/gptnew/', GPTAudioUpdateView.as_view(), name='gpt-audio-update'),
    # 生成图片
    path('image/new/', ImageCreateView.as_view(), name='image-generate'),
    # 朋友圈文案
    # path('post/new/', PostCreateView.as_view(), name='post-create'),
    # path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),
    #
    # path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    # path('media/Files/<int:pk>', PostDeleteView.as_view(), name='post-delete'),

    path('search/', views.search, name='search'),
    path('about/', views.about, name='blog-about'),

    # 检查用户登陆状态
    path('check-user-status/', views.check_user_logged_in, name='check_user_status'),

    path('a1/', a1_view, name='my_view_a1'),
]
