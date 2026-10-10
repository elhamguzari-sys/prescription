# apps/prescription/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ═══ List + Create + Update (SAME page) ═══
    path('', views.prescription_list, name='prescription_list'),

    # ═══ Print ═══
    path('<int:pk>/print/', views.prescription_print_page, name='prescription_print_page'),
    path('<int:pk>/regenerate/', views.prescription_regenerate, name='prescription_regenerate'),
    path('<int:pk>/delete/', views.prescription_delete, name='prescription_delete'),

    # ═══ Ready prescriptions ═══
    path('ready/', views.ready_prescription_list, name='ready_prescription_list'),
    path('api/ready/<int:pk>/', views.api_ready_prescription_detail, name='api_ready_prescription_detail'),

    # ═══ Templates ═══
    path('templates/', views.template_list, name='template_list'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/set-default/', views.template_set_default, name='template_set_default'),

    # ═══ Template APIs ═══
    path('api/templates/<int:pk>/fields/', views.api_get_fields, name='api_get_fields'),
    path('api/templates/<int:pk>/fields/save/', views.api_save_fields, name='api_save_fields'),
    path('api/templates/<int:pk>/upload/', views.api_upload_background, name='api_upload_background'),
    path('api/fonts/', views.api_get_fonts, name='api_get_fonts'),

    # ═══ Prescription API (View / Edit modals) ═══
    path('api/prescriptions/<int:pk>/', views.api_prescription_detail, name='api_prescription_detail'),

    # ═══ Search APIs ═══
    path('api/search/medications/', views.api_search_medications, name='api_search_medications'),
    path('api/search/patients/', views.api_search_patients, name='api_search_patients'),
]