
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from . import views as prescripts_views  
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', prescripts_views.dashboard, name='dashboard'),
     path('backup/', prescripts_views.backup_page, name='backup_page'),
    path('backup/download/', prescripts_views.backup_download, name='backup_download'),    
    path('admin/', admin.site.urls),
    path('patient/', include('apps.patient.urls')),
    path('medicine/', include('apps.medicine.urls')),
    path('prescripts/', include('apps.prescripts.urls')),
    path('patient_history/', include('apps.patient_history.urls')),
]






if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


