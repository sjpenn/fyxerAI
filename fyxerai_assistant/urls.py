"""
URL configuration for fyxerai_assistant project.

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
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_url
from django.conf import settings
from django.conf.urls.static import static as serve_static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("emails/", include('core.urls_unified', namespace='emails')),
    path("", include('core.urls')),
    # Serve favicon to avoid 404s in dev
    path("favicon.ico", RedirectView.as_view(url=static_url('icons/icon32.png'), permanent=True)),
]

# Ensure static assets are served in dev and staging even if DEBUG is False
urlpatterns += serve_static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
