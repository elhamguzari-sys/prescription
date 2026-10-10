# apps/patient/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('patient_list/', views.patient_list, name='patient_list'),
]