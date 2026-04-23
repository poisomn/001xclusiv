from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("info/<slug:slug>/", views.info_page, name="info_page"),
]
