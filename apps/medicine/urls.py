from django.urls import path
from . import  views

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # 💊 بانک دواها
    # ═══════════════════════════════════════════════════════════════
    path('medications/', views.medication_list, name='medication_list'),
    path('medications/<int:pk>/json/', views.api_medication_detail, name='api_medication_detail'),
    path('api/search-medications/', views.api_search_medications, name='api_search_medications'),
]