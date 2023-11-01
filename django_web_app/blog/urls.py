from django.urls import path
from .views import (
    PostListView,
    PostDetailView,
    PostCreateView,
    PostUpdateView,
    PostDeleteView,
    UserPostListView,
    GPTAudioCreateView, GPTAudioUpdateView, ImageCreateView, GPTChatCreateView, GPTImageView,
)
from . import views

urlpatterns = [
    path('', PostListView.as_view(), name='blog-home'),  # 首页

    path('post/gptchat/', GPTChatCreateView.as_view(), name='gpt-chat'),  # gpt聊天界面
    path('post/gptchat/image', GPTImageView.as_view(), name='gpt-image'),

    path('user/<str:username>', UserPostListView.as_view(), name='user-posts'),
    path('post/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('post/gptnew/', GPTAudioCreateView.as_view(), name='gpt-audio'),
    path('update/gptnew/', GPTAudioUpdateView.as_view(), name='gpt-audio-update'),

    path('image/new/', ImageCreateView.as_view(), name='image-generate'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post-update'),

    path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post-delete'),
    path('media/Files/<int:pk>', PostDeleteView.as_view(), name='post-delete'),
    path('search/', views.search, name='search'),
    path('about/', views.about, name='blog-about'),
]
