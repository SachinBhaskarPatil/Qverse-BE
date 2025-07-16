from django.urls import path
from .views import GameplayViewSet, MockLeaderboardView,UserUniverseSuggestionViewSet

urlpatterns = [
    path('start_quest/<str:slug>/', GameplayViewSet.as_view({'post': 'start_quest'}), name='start-quest'),
    path('universes/', GameplayViewSet.as_view({'get': 'get_universes'}), name='universes'),
    path('answer_question/<int:pk>/', GameplayViewSet.as_view({'post': 'answer_question'}), name='answer-question'),
    path('score_categories/<str:slug>/', GameplayViewSet.as_view({'get': 'get_score_categories'}), name='score-categories'),
    path('suggest_universe/', UserUniverseSuggestionViewSet.as_view({'post': 'suggest_universe'}), name='suggest-universe'),
    # path('leaderboard/', MockLeaderboardView.as_view(), name='leaderboard'),
    # path('current_gameplay_score/', GameplayViewSet.as_view({'get': 'current_gameplay_score'}), name='current-gameplay-score'),
    # path('user_stats/', GameplayViewSet.as_view({'get': 'user_stats'}), name='user-stats'),
]