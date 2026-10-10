# apps/patient_history/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.patient_history_list, name='patient_history_list'),
    path('api/patient/<int:pk>/prescriptions/', views.api_patient_prescriptions, name='api_patient_prescriptions'),
    path('api/prescription/<int:pk>/', views.api_prescription_detail, name='api_history_prescription_detail'),
]