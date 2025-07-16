from django.contrib import admin
from .models import UserGameplay, UserScoreByCategoryForGameplay, UserCollectible, UserUniverseSuggestion

# Register your models here.
admin.site.register(UserUniverseSuggestion)