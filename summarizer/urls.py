from django.urls import path
from . import views

urlpatterns = [
    path('', views.summarizer, name='summarizer')
]