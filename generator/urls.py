from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'universes', UniverseViewSet)
router.register(r'quests', QuestViewSet, basename='Quest')
router.register(r'questions', QuestionViewSet)
router.register(r'options', OptionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('homepages/', HomePageView.as_view(), name='homepage-list-create'), 
    path('banners/', BannerView.as_view(), name='banner-list'),

    # Trivia
    path('trivia/', TriviaView.as_view(), name='trivia-list'), 
    path('trivia/<slug:slug>/', TriviaView.as_view(), name='trivia-detail'),  
    path('trivia/<slug:slug>/<int:question_number>/', TriviaView.as_view(), name='trivia-question-detail'),  

    # Audio Story
    path('audiostories/', AudioStoryView.as_view(), name='audiostory-list'),  
    path('audiostories/<slug:slug>/', AudioStoryView.as_view(), name='audiostory-detail'),  
    path('audiostories/<slug:slug>/<int:episode_number>/', AudioStoryView.as_view(), name='audiostory-episode-detail'),  

    # Comic
    path('comics/', ComicView.as_view(), name='comic-list'),  
    path('comics/<slug:slug>/', ComicView.as_view(), name='comic-detail'),  
    path('comics/<slug:slug>/<int:page_number>/', ComicView.as_view(), name='comic-page-detail'),  

    path('make-live/<str:type>/', MakeLiveView.as_view(), name='make-live'),

    # Short Videos
    path('shortvideos/', ShortVideosView.as_view(), name='shortvideo-list'),
    path('shortvideos/<slug:slug>/', ShortVideosView.as_view(), name='shortvideo-detail'),

    path('mixed-content/', MixedContentView.as_view(), name='mixed-content'),
    path('quest/<slug:slug>/', QuestView.as_view(), name='quest-detail'),
]