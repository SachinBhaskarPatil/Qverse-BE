from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('user.urls')),
    path('api/generator/', include('generator.urls')),
    path('api/gameplay/', include('game_interface.urls')),
    path('api/gametester/', include('gametester.urls')),
]
