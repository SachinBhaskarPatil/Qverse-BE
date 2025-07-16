from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserProfileViewSet,AuthView,RecommendationView,ProfileView

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('verify_user/', AuthView.as_view(), name='verify_user'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('recommendations/', RecommendationView.as_view(), name='recommendations'),
]