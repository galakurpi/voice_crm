"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from voice_agent import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Authentication endpoints - support both with and without trailing slashes
    path('auth/register', views.register_view, name='register'),
    path('auth/register/', views.register_view, name='register_slash'),
    path('auth/login', views.login_view, name='login'),
    path('auth/login/', views.login_view, name='login_slash'),
    path('auth/logout', views.logout_view, name='logout'),
    path('auth/logout/', views.logout_view, name='logout_slash'),
    path('auth/check', views.check_auth_view, name='check_auth'),
    path('auth/check/', views.check_auth_view, name='check_auth_slash'),
]
