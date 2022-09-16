from django.urls import path

from . import views

app_name = 'about'

urlpatterns = [
    path('author/', views.AuthorViews.as_view(), name='author'),
    path('tech/', views.TechViews.as_view(), name='tech'),
]
