# prescript/views.py

import io
import os
import zipfile
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.utils import timezone

# Import models from your apps
from apps.patient.models import Patient
from apps.medicine.models import Medication
from apps.prescripts.models import (
    Prescription,
    PrescriptionItem,
    PrescriptionTemplate,
)


# ═══════════════════════════════════════════════════════════════════
# 📊 DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def dashboard(request):
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # ─── Core counts ───
    total_prescriptions = Prescription.objects.count()
    total_patients = Patient.objects.filter(prescriptions__isnull=False).distinct().count()
    today_count = Prescription.objects.filter(prescription_date=today).count()
    week_count = Prescription.objects.filter(prescription_date__gte=week_ago).count()
    month_count = Prescription.objects.filter(prescription_date__gte=month_ago).count()
    total_medicines = Medication.objects.filter(is_active=True).count()
    total_templates = PrescriptionTemplate.objects.filter(is_active=True).count()

    # ─── Recent prescriptions ───
    recent_prescriptions = (
        Prescription.objects
        .select_related('patient')
        .order_by('-created_at')[:6]
    )

    # ─── Top medicines (most prescribed) ───
    top_medicines = (
        PrescriptionItem.objects
        .values('medication__name', 'medication__generic_name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:8]
    )

    # ─── Recent patients (with prescriptions) ───
    recent_patients = (
        Patient.objects
        .annotate(rx_count=Count('prescriptions'))
        .filter(rx_count__gt=0)
        .order_by('-id')[:6]
    )

    # ─── 7-day activity chart ───
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = Prescription.objects.filter(prescription_date=d).count()
        chart_data.append({
            'date': d,
            'label': d.strftime('%a'),
            'label_full': d.strftime('%Y-%m-%d'),
            'count': cnt,
        })

    max_chart = max([c['count'] for c in chart_data]) or 1

    # ─── Gender breakdown ───
    genders = (
        Patient.objects
        .filter(prescriptions__isnull=False)
        .values('gender')
        .annotate(cnt=Count('id', distinct=True))
        .order_by('-cnt')
    )
    gender_map = {'M': 'مرد', 'F': 'زن'}

    return render(request, 'dashboard.html', {
        'today': today,

        'stats': {
            'total_prescriptions': total_prescriptions,
            'total_patients': total_patients,
            'today_count': today_count,
            'week_count': week_count,
            'month_count': month_count,
            'total_medicines': total_medicines,
            'total_templates': total_templates,
        },

        'recent_prescriptions': recent_prescriptions,
        'top_medicines': top_medicines,
        'recent_patients': recent_patients,

        'chart_data': chart_data,
        'max_chart': max_chart,

        'genders': [
            {
                'label': gender_map.get(g['gender'], g['gender'] or 'نامشخص'),
                'count': g['cnt'],
                'code': g['gender'],
            }
            for g in genders
        ],

        'page_title': 'داشبورد',
        'active_nav': 'dashboard',
    })


# ═══════════════════════════════════════════════════════════════════
# 💾 BACKUP — helpers
# ═══════════════════════════════════════════════════════════════════

def _fmt_size(num_bytes):
    """Convert bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return f'{num_bytes:.1f} {unit}'
        num_bytes /= 1024
    return f'{num_bytes:.1f} TB'

def _get_backup_items():
    """
    Return a list of (display_name, absolute_path, kind) for everything to back up.
    Only includes:
      • db.sqlite3  (the database)
      • media/      (uploaded images and templates)
    No source code — kept small and fast.
    """
    base = str(settings.BASE_DIR)
    items = []

    # ── 1. Database ──
    db_path = os.path.join(base, 'db.sqlite3')
    if os.path.exists(db_path):
        items.append(('db.sqlite3', db_path, 'file'))

    # ── 2. Media folder ──
    media_root = str(settings.MEDIA_ROOT)
    if os.path.exists(media_root):
        items.append(('media', media_root, 'dir'))

    return items

# ═══════════════════════════════════════════════════════════════════
# 💾 BACKUP — page
# ═══════════════════════════════════════════════════════════════════

def backup_page(request):
    """Show the backup page with size info."""
    base = str(settings.BASE_DIR)

    # ── Size of DB ──
    db_path = os.path.join(base, 'db.sqlite3')
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    # ── Size of media ──
    media_root = str(settings.MEDIA_ROOT)
    media_size = 0
    media_files = 0
    if os.path.exists(media_root):
        for root, dirs, files in os.walk(media_root):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    media_size += os.path.getsize(fp)
                    media_files += 1
                except OSError:
                    pass

    # ── Counts ──
    total_patients = Patient.objects.count()
    total_prescriptions = Prescription.objects.count()

    return render(request, 'backup.html', {
        'db_size': _fmt_size(db_size),
        'media_size': _fmt_size(media_size),
        'media_files': media_files,
        'total_patients': total_patients,
        'total_prescriptions': total_prescriptions,
        'page_title': 'پشتیبان‌گیری',
        'active_nav': 'backup',
    })


# ═══════════════════════════════════════════════════════════════════
# 💾 BACKUP — download
# ═══════════════════════════════════════════════════════════════════

def backup_download(request):
    """
    Build a ZIP of DB + media + code in memory and return it as a download.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    zip_name = f'backup_{timestamp}.zip'

    items = _get_backup_items()

    # ── Write to in-memory buffer ──
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for display_name, full_path, kind in items:
            try:
                if kind == 'file':
                    zf.write(full_path, arcname=display_name)
                elif kind == 'dir':
                    for root, dirs, files in os.walk(full_path):
                        # Skip __pycache__ inside media
                        dirs[:] = [d for d in dirs if d != '__pycache__']
                        for f in files:
                            fp = os.path.join(root, f)
                            rel = os.path.relpath(fp, full_path)
                            arc = os.path.join(display_name, rel).replace('\\', '/')
                            try:
                                zf.write(fp, arcname=arc)
                            except OSError:
                                pass
            except OSError:
                continue

    buffer.seek(0)

    response = StreamingHttpResponse(
        buffer,
        content_type='application/zip',
    )
    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
    response['Content-Length'] = buffer.getbuffer().nbytes
    return response