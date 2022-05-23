from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = "plbscf"
urlpatterns = [
        path('', views.index, name='index'),
        path('csv_to_PLBSCF/', views.csv_to_PLBSCF, name='csv_to_PLBSCF'),
]

