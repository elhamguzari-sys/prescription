# apps/patient_history/views.py

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.patient.models import Patient
from apps.prescripts.models import Prescription, PrescriptionItem


# ═══════════════════════════════════════════════════════════════════
# MAIN PAGE — search + patient list
# ═══════════════════════════════════════════════════════════════════

def patient_history_list(request):
    first_name  = request.GET.get('first_name', '').strip()
    last_name   = request.GET.get('last_name', '').strip()
    father_name = request.GET.get('father_name', '').strip()
    age         = request.GET.get('age', '').strip()
    phone       = request.GET.get('phone', '').strip()

    has_filters = any([first_name, last_name, father_name, age, phone])

    patients = []
    total_found = 0

    if has_filters:
        qs = Patient.objects.annotate(
            rx_count=Count('prescriptions')
        ).filter(rx_count__gt=0)

        if first_name:
            qs = qs.filter(first_name__icontains=first_name)
        if last_name:
            qs = qs.filter(last_name__icontains=last_name)
        if father_name:
            qs = qs.filter(father_name__icontains=father_name)
        if phone:
            qs = qs.filter(phone__icontains=phone)
        if age:
            try:
                qs = qs.filter(age=int(age))
            except (ValueError, TypeError):
                pass

        qs = qs.order_by('first_name', 'last_name')
        total_found = qs.count()

        paginator = Paginator(qs, 20)
        page_number = request.GET.get('page', 1)
        try:
            patients = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            patients = paginator.page(1)

    return render(request, 'patient_history/patient_history_list.html', {
        'patients': patients,
        'total_found': total_found,
        'first_name': first_name,
        'last_name': last_name,
        'father_name': father_name,
        'age': age,
        'phone': phone,
        'has_filters': has_filters,
        'page_title': 'تاریخچه مریض‌ها',
        'active_nav': 'patient_history',
    })


# ═══════════════════════════════════════════════════════════════════
# AJAX — load one patient's prescriptions
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_patient_prescriptions(request, pk):
    """JSON: list of a patient's prescriptions (date + number + id)."""
    patient = get_object_or_404(Patient, pk=pk)

    prescriptions = (
        Prescription.objects
        .filter(patient=patient)
        .order_by('-prescription_date', '-created_at')
    )

    today = timezone.localdate()

    data = []
    for rx in prescriptions:
        data.append({
            'id': rx.id,
            'number': rx.prescription_number or '',
            'date': rx.prescription_date.strftime('%Y-%m-%d') if rx.prescription_date else '',
            'is_today': rx.prescription_date == today,
            'items_count': rx.items.count(),
        })

    return JsonResponse({
        'success': True,
        'patient': {
            'id': patient.id,
            'name': patient.full_name,
        },
        'prescriptions': data,
    })


# ═══════════════════════════════════════════════════════════════════
# AJAX — load one prescription's full details
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_prescription_detail(request, pk):
    """JSON: full details of one prescription."""
    rx = get_object_or_404(
        Prescription.objects
        .select_related('patient', 'template')
        .prefetch_related('items__medication'),
        pk=pk
    )

    items = []
    for it in rx.items.all().order_by('order', 'id'):
        med = it.medication
        items.append({
            'number': len(items) + 1,
            'medication_name': med.name if med else '',
            'generic_name': med.generic_name if med else '',
            'manufacturer': med.manufacturer if med else '',
            'strength': it.drug_strength or '',
            'form': it.drug_form or '',
            'dose': it.dose or '',
            'frequency_display': it.get_frequency_display() if it.frequency else '',
            'timing_display': it.get_timing_display() if it.timing else '',
            'route_display': it.get_route_display() if it.route else '',
            'duration': it.duration or '',
        })

    return JsonResponse({
        'success': True,
        'prescription': {
            'id': rx.id,
            'number': rx.prescription_number or '',
            'date': rx.prescription_date.strftime('%Y-%m-%d') if rx.prescription_date else '',

            'signs_symptoms': rx.signs_symptoms or '',
            'diagnosis': rx.diagnosis or '',
            'impression': rx.impression or '',
            'doctor_note': rx.doctor_note or '',

            'blood_pressure': rx.blood_pressure or '',
            'pulse': str(rx.pulse) if rx.pulse else '',
            'respiratory_rate': str(rx.respiratory_rate) if rx.respiratory_rate else '',
            'temperature': str(rx.temperature) if rx.temperature else '',
            'spo2': str(rx.spo2) if rx.spo2 else '',
            'weight': str(rx.weight) if rx.weight else '',
            'height': str(rx.height) if rx.height else '',

            'advice_items': rx.advice_items or [],

            'items': items,
            'items_count': len(items),
        }
    })