# apps/prescription/views.py

import json
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import (
    Prescription,
    PrescriptionItem,
    ReadyPrescription,
    PrescriptionTemplate,
    TemplateField,
)
from .forms import (
    PrescriptionForm,
    PrescriptionItemFormSet,
    ReadyPrescriptionForm,
    PrescriptionTemplateForm,
    TemplateFieldFormSet,
)
from .constants import (
    FONT_CHOICES,
    DATE_FORMAT_CHOICES,
    DATE_SEPARATOR_CHOICES,
    DEFAULT_MEDICINE_OPTIONS,
)

from apps.medicine.models import Medication
from apps.patient.models import Patient


# ═══════════════════════════════════════════════════════════════════
# 🎨 Helpers
# ═══════════════════════════════════════════════════════════════════

def _get_first_form_error(form):
    for field_name, errors in form.errors.items():
        for err in errors:
            return str(err)
    return 'لطفاً خطاهای فرم را اصلاح کنید.'


def _safe_json_dumps(data):
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        print(f"⚠️ JSON dumps error: {e}")
        return 'null'


def _pick_default_template():
    return (
        PrescriptionTemplate.objects.filter(is_default=True, is_active=True).first()
        or PrescriptionTemplate.objects.filter(is_active=True).first()
    )


def _get_preview_data():
    """Sample data for the template editor preview."""
    return {
        'patient_name':    'احمد نوید وازر احمدی',
        'patient_father':  'عبدالله',
        'patient_age':     '35',
        'patient_gender':  'مرد',
        'patient_phone':   '0700-123456',
        'patient_address': 'کابل، افغانستان',
        'patient_file':    'F-12345',

        'vital_bp':     '120/80',
        'vital_pr':     '72',
        'vital_rr':     '16',
        'vital_temp':   '37.2',
        'vital_spo2':   '98%',
        'vital_weight': '75',
        'vital_height': '175',
        'vital_bmi':    '24.5',

        'signs_symptoms': 'درد قفسه سینه از ۳ روز پیش، تشدید با فعالیت',
        'diagnosis':      'آنژین صدری',
        'impression':     'آنژین ناپایدار — نیاز به ارزیابی قلبی',
        'doctor_note':    'پیگیری هفتگی — کاهش نمک',
        'advice':         'استراحت + کاهش نمک',

        'medications_list':
            '۱. Metformin 500mg | ۱ تابلت | روزی ۲ بار | بعد از غذا\n'
            '۲. Atorvastatin 20mg | ۱ تابلت | شب | قبل خواب\n'
            '۳. Aspirin 80mg | ۱ تابلت | روزی ۱ بار | بعد از صبحانه',

        'prescription_number': 'P-1403-00123',
        'prescription_date':   '1403/07/15',
    }


def _get_preview_medicines():
    """Preview medicines for the editor — includes quantity example."""
    return [
        {
            'number': 1, 'generic': 'Metformin', 'strength': '500mg',
            'brand': 'Glucophage', 'manufacturer': 'Merck',
            'dosage': '۱ تابلت', 'frequency': 'روزی ۲ بار',
            'timing': 'بعد از غذا', 'route': 'oral', 'duration': '۳۰ روز',
            'quantity': 60,
        },
        {
            'number': 2, 'generic': 'Atorvastatin', 'strength': '20mg',
            'brand': 'Lipitor', 'manufacturer': 'Pfizer',
            'dosage': '۱ تابلت', 'frequency': 'شب',
            'timing': 'قبل خواب', 'route': 'oral', 'duration': '۳۰ روز',
            'quantity': 30,
        },
        {
            'number': 3, 'generic': 'Aspirin', 'strength': '80mg',
            'brand': 'Bayer', 'manufacturer': 'Bayer',
            'dosage': '۱ تابلت', 'frequency': 'روزی ۱ بار',
            'timing': 'بعد از صبحانه', 'route': 'oral', 'duration': '۳۰ روز',
            'quantity': 30,
        },
    ]


# ═══════════════════════════════════════════════════════════════════
# CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════

def _build_list_context(request):
    """Everything the GET path passes to the template."""
    today = timezone.localdate()

    qs = Prescription.objects.select_related(
        'patient', 'template'
    ).prefetch_related('items').order_by('-created_at')

    search_query = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if search_query:
        qs = qs.filter(
            Q(prescription_number__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(patient__father_name__icontains=search_query) |
            Q(diagnosis__icontains=search_query)
        )

    if date_filter == 'today':
        qs = qs.filter(prescription_date=today)
    elif date_filter == 'week':
        qs = qs.filter(prescription_date__gte=today - timezone.timedelta(days=7))
    elif date_filter == 'month':
        qs = qs.filter(prescription_date__gte=today - timezone.timedelta(days=30))

    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 20)
    try:
        prescriptions = paginator.page(page_number)
    except PageNotAnInteger:
        prescriptions = paginator.page(1)
    except EmptyPage:
        prescriptions = paginator.page(paginator.num_pages)

    templates = PrescriptionTemplate.objects.filter(is_active=True).order_by(
        '-is_default', 'name'
    )
    ready_prescriptions = ReadyPrescription.objects.filter(
        is_active=True
    ).order_by('-is_favorite', 'title')
    medications = Medication.objects.filter(is_active=True).order_by(
        '-is_favorite', 'name'
    )
    recent_patients = Patient.objects.all().order_by('-id')[:15]
    default_tpl = _pick_default_template()

    return {
        'prescriptions': prescriptions,
        'paginator': paginator,
        'stats': {
            'today_count': Prescription.objects.filter(prescription_date=today).count(),
            'week_count': Prescription.objects.filter(
                prescription_date__gte=today - timezone.timedelta(days=7)
            ).count(),
            'total_count': Prescription.objects.count(),
        },
        'search_query': search_query,
        'date_filter': date_filter,
        'today': today,
        'templates': templates,
        'default_template_id': default_tpl.id if default_tpl else '',
        'ready_prescriptions': ready_prescriptions,
        'medications': medications,
        'recent_patients': recent_patients,
        'page_title': 'لیست نسخه‌ها',
        'active_nav': 'prescriptions',
    }


# ═══════════════════════════════════════════════════════════════════
# ERROR RENDERER
# ═══════════════════════════════════════════════════════════════════

def _render_with_modal_error(request, error_text, form_data=None, auto_patient_id=None):
    """Re-render with modal_error + form_data preserved."""
    context = _build_list_context(request)

    ctx_form = {}
    if form_data is not None:
        def _getlist(key):
            if hasattr(form_data, 'getlist'):
                return form_data.getlist(key)
            val = form_data.get(key)
            if val is None:
                return []
            return val if isinstance(val, list) else [val]

        for key in (
            'patient_id', 'template_id', 'prescription_date',
            'signs_symptoms', 'diagnosis', 'impression', 'doctor_note',
            'blood_pressure', 'pulse', 'respiratory_rate', 'temperature',
            'spo2', 'weight', 'height', 'advice_text',
            'new_first_name', 'new_last_name', 'new_father_name',
            'new_gender', 'new_age', 'new_phone', 'new_address',
        ):
            ctx_form[key] = form_data.get(key, '') or ''

        ctx_form['medication'] = _getlist('medication[]')
        ctx_form['dose']       = _getlist('dose[]')
        ctx_form['frequency']  = _getlist('frequency[]')
        ctx_form['timing']     = _getlist('timing[]')
        ctx_form['route']      = _getlist('route[]')
        ctx_form['duration']   = _getlist('duration[]')
        ctx_form['quantity']   = _getlist('quantity[]')

    if auto_patient_id:
        try:
            p = Patient.objects.get(id=auto_patient_id)
            ctx_form['patient_id'] = str(p.id)
            ctx_form['auto_patient'] = {
                'id': p.id,
                'name': p.full_name,
                'age': str(p.age or ''),
                'gender': p.get_gender_display() if hasattr(p, 'get_gender_display') else '',
                'phone': p.phone or '',
                'genderCode': p.gender or '',
                'initial': (p.first_name or '?')[:1].upper(),
            }
        except Patient.DoesNotExist:
            pass

    context['modal_error'] = error_text
    context['form_data'] = ctx_form
    context['open_modal'] = True
    return render(request, 'prescription/prescription_list.html', context)


# ═══════════════════════════════════════════════════════════════════
# 📋 PRESCRIPTION LIST  —  LIST + CREATE + UPDATE + DELETE
# ═══════════════════════════════════════════════════════════════════

def prescription_list(request):
    """
    One page for everything:
      • List of prescriptions
      • CREATE / UPDATE via modal
      • DELETE via modal
    """

    # ────────────────────────────────────────────────────────────
    # POST: CREATE
    # ────────────────────────────────────────────────────────────
    if request.method == 'POST' and request.POST.get('action') == 'create':

        patient_id = request.POST.get('patient_id', '').strip()
        new_first  = request.POST.get('new_first_name', '').strip()
        new_last   = request.POST.get('new_last_name', '').strip()
        new_father = request.POST.get('new_father_name', '').strip()
        new_age    = request.POST.get('new_age', '').strip()

        patient = None

        if patient_id:
            patient = Patient.objects.filter(pk=patient_id).first()

        if not patient:
            if not (new_first and new_last and new_father and new_age):
                return _render_with_modal_error(
                    request,
                    'Please select an existing patient OR fill in all required '
                    'fields (First Name, Last Name, Father Name, Age) to create '
                    'a new patient. — '
                    'لطفاً یک مریض موجود انتخاب کنید یا فیلدهای اجباری مریض '
                    'جدید را پر کنید.',
                    form_data=request.POST,
                )

            existing = Patient.objects.filter(
                first_name__iexact=new_first,
                last_name__iexact=new_last,
                father_name__iexact=new_father,
            ).first()

            if existing:
                return _render_with_modal_error(
                    request,
                    f'Patient "{existing.full_name}" already exists in the '
                    f'system. We have automatically selected this patient — '
                    f'please review and click Save again. — '
                    f'مریض «{existing.full_name}» قبلاً ثبت شده است. '
                    f'به صورت خودکار انتخاب شد — لطفاً دوباره ذخیره کنید.',
                    form_data=request.POST,
                    auto_patient_id=existing.id,
                )

            from apps.patient.forms import PatientForm
            pf = PatientForm({
                'first_name':  new_first,
                'last_name':   new_last,
                'father_name': new_father,
                'gender':      request.POST.get('new_gender', 'M'),
                'age':         new_age or 0,
                'phone':       request.POST.get('new_phone', ''),
                'address':     request.POST.get('new_address', ''),
            })
            if pf.is_valid():
                patient = pf.save()
            else:
                return _render_with_modal_error(
                    request,
                    _get_first_form_error(pf),
                    form_data=request.POST,
                )

        if not patient:
            return _render_with_modal_error(
                request,
                'Please select an existing patient or fill in all required '
                'fields to create a new patient.',
                form_data=request.POST,
            )

        prescription = Prescription.objects.create(
            patient=patient,
            template_id=request.POST.get('template_id') or None,
            created_by=request.user if request.user.is_authenticated else None,
        )

        prescription.signs_symptoms = request.POST.get('signs_symptoms', '')
        prescription.diagnosis      = request.POST.get('diagnosis', '')
        prescription.impression     = request.POST.get('impression', '')
        prescription.doctor_note    = request.POST.get('doctor_note', '')

        prescription.blood_pressure   = request.POST.get('blood_pressure', '')
        prescription.pulse            = request.POST.get('pulse') or None
        prescription.temperature      = request.POST.get('temperature') or None
        prescription.respiratory_rate = request.POST.get('respiratory_rate') or None
        prescription.spo2             = request.POST.get('spo2') or None
        prescription.weight           = request.POST.get('weight') or None
        prescription.height           = request.POST.get('height') or None

        advice_text = request.POST.get('advice_text', '').strip()
        prescription.advice_items = [
            a.strip() for a in advice_text.split('\n') if a.strip()
        ]

        date_val = request.POST.get('prescription_date')
        if date_val:
            prescription.prescription_date = date_val

        prescription.save()
        _save_prescription_items_from_post(request, prescription)

        messages.success(request, 'نسخه ذخیره شد. آماده چاپ است.')
        return redirect('prescription_print_page', pk=prescription.pk)

    # ────────────────────────────────────────────────────────────
    # POST: UPDATE (edit)
    # ────────────────────────────────────────────────────────────
    if request.method == 'POST' and request.POST.get('action') == 'update':
        pk = request.POST.get('prescription_id')
        prescription = get_object_or_404(Prescription, pk=pk)

        template_id = request.POST.get('template_id')
        if template_id:
            try:
                prescription.template = PrescriptionTemplate.objects.get(pk=template_id)
            except PrescriptionTemplate.DoesNotExist:
                pass

        prescription.signs_symptoms = request.POST.get('signs_symptoms', '')
        prescription.diagnosis      = request.POST.get('diagnosis', '')
        prescription.impression     = request.POST.get('impression', '')
        prescription.doctor_note    = request.POST.get('doctor_note', '')

        prescription.blood_pressure   = request.POST.get('blood_pressure', '')
        prescription.pulse            = request.POST.get('pulse') or None
        prescription.temperature      = request.POST.get('temperature') or None
        prescription.respiratory_rate = request.POST.get('respiratory_rate') or None
        prescription.spo2             = request.POST.get('spo2') or None
        prescription.weight           = request.POST.get('weight') or None
        prescription.height           = request.POST.get('height') or None

        advice_text = request.POST.get('advice_text', '').strip()
        prescription.advice_items = [
            a.strip() for a in advice_text.split('\n') if a.strip()
        ]

        date_val = request.POST.get('prescription_date')
        if date_val:
            prescription.prescription_date = date_val

        prescription.save()

        prescription.items.all().delete()
        _save_prescription_items_from_post(request, prescription)

        messages.success(
            request,
            f'نسخه «{prescription.prescription_number}» بروزرسانی شد.'
        )
        return redirect('prescription_print_page', pk=prescription.pk)

    # ⭐ ──────────────────────────────────────────────────────────
    # ⭐ POST: DELETE  ⬅️ NEW HANDLER
    # ⭐ ──────────────────────────────────────────────────────────
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        pk = request.POST.get('prescription_id')
        prescription = get_object_or_404(Prescription, pk=pk)
        number = prescription.prescription_number

        # Delete the generated image file first (avoid orphans)
        if prescription.edited_image:
            try:
                prescription.edited_image.delete(save=False)
            except Exception:
                pass

        prescription.delete()
        messages.success(request, f'نسخه «{number}» حذف شد.')
        return redirect('prescription_list')

    # ────────────────────────────────────────────────────────────
    # GET: render the page
    # ────────────────────────────────────────────────────────────
    return render(
        request,
        'prescription/prescription_list.html',
        _build_list_context(request),
    )


# ═══════════════════════════════════════════════════════════════════
# 🔌 API — Prescription Detail
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_prescription_detail(request, pk):
    """JSON detail for the View / Edit modals."""
    rx = get_object_or_404(
        Prescription.objects.select_related(
            'patient', 'template'
        ).prefetch_related('items__medication'),
        pk=pk
    )

    def _s(v):
        return '' if v is None else str(v)

    patient = rx.patient
    patient_gender_display = ''
    if patient and hasattr(patient, 'get_gender_display'):
        try:
            patient_gender_display = patient.get_gender_display()
        except Exception:
            patient_gender_display = getattr(patient, 'gender', '')

    items = []
    for item in rx.items.all().order_by('order', 'id'):
        items.append({
            'id': item.id,
            'medication_id': item.medication_id,
            'drug_name': item.drug_name or '',
            'drug_strength': item.drug_strength or '',
            'drug_form': item.drug_form or '',
            'drug_generic_name': item.drug_generic_name or '',
            'dose': item.dose or '',
            'frequency': item.frequency or '',
            'frequency_display': item.get_frequency_display() if item.frequency else '',
            'timing': item.timing or '',
            'timing_display': item.get_timing_display() if item.timing else '',
            'route': item.route or 'oral',
            'route_display': item.get_route_display() if item.route else '',
            'duration': item.duration or '',
            # ⭐ quantity
            'quantity': item.quantity if item.quantity else None,
            'quantity_display': item.quantity_display or '',
        })

    return JsonResponse({
        'success': True,
        'prescription': {
            'id': rx.id,
            'prescription_number': rx.prescription_number or '',
            'prescription_date': rx.prescription_date.strftime('%Y-%m-%d') if rx.prescription_date else '',
            'template_id': rx.template_id,
            'template_name': rx.template.name if rx.template else '',

            'patient_id': patient.id if patient else None,
            'patient_name': patient.full_name if patient else '',
            'patient_age': str(getattr(patient, 'age', '') or ''),
            'patient_gender': patient_gender_display,
            'patient_gender_code': getattr(patient, 'gender', '') if patient else '',
            'patient_phone': getattr(patient, 'phone', '') or '' if patient else '',

            'signs_symptoms': rx.signs_symptoms or '',
            'diagnosis': rx.diagnosis or '',
            'impression': rx.impression or '',
            'doctor_note': rx.doctor_note or '',

            'blood_pressure': rx.blood_pressure or '',
            'pulse': _s(rx.pulse),
            'respiratory_rate': _s(rx.respiratory_rate),
            'temperature': _s(rx.temperature),
            'spo2': _s(rx.spo2),
            'weight': _s(rx.weight),
            'height': _s(rx.height),

            'advice_items': rx.advice_items or [],
            'items': items,
            'items_count': len(items),

            'has_image': bool(rx.edited_image),
            'image_url': rx.edited_image.url if rx.edited_image else '',
        }
    })


def prescription_print_page(request, pk):
    """Generate the image and show the print preview."""
    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'template'),
        pk=pk
    )

    if not prescription.template:
        tpl = _pick_default_template()
        if tpl:
            prescription.template = tpl
            prescription.save(update_fields=['template'])
        else:
            messages.error(request, 'هیچ دیزاین نسخه‌ای وجود ندارد. اول یک دیزاین بسازید.')
            return render(request, 'prescription/prescription_print.html', {
                'prescription': prescription,
                'page_title': f'چاپ نسخه — {prescription.patient.full_name}',
                'active_nav': 'prescriptions',
            })

    try:
        prescription.generate_image(
            user=request.user if request.user.is_authenticated else None
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'خطا در تولید تصویر نسخه: {e}')

    return render(request, 'prescription/prescription_print.html', {
        'prescription': prescription,
        'page_title': f'چاپ نسخه — {prescription.patient.full_name}',
        'active_nav': 'prescriptions',
    })


def prescription_regenerate(request, pk):
    """Regenerate the image from the list page."""
    prescription = get_object_or_404(Prescription, pk=pk)

    if not prescription.template:
        tpl = _pick_default_template()
        if tpl:
            prescription.template = tpl
            prescription.save(update_fields=['template'])
        else:
            messages.error(request, 'هیچ دیزاین نسخه‌ای وجود ندارد.')
            return redirect('prescription_list')

    try:
        prescription.generate_image(
            user=request.user if request.user.is_authenticated else None
        )
        messages.success(
            request,
            f'تصویر نسخه «{prescription.prescription_number}» تولید شد.'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'خطا در تولید تصویر: {e}')

    return redirect('prescription_list')


def prescription_delete(request, pk):
    """Delete a prescription (dedicated endpoint)."""
    if request.method != 'POST':
        return redirect('prescription_list')

    prescription = get_object_or_404(Prescription, pk=pk)
    number = prescription.prescription_number

    if prescription.edited_image:
        try:
            prescription.edited_image.delete(save=False)
        except Exception:
            pass

    prescription.delete()
    messages.success(request, f'نسخه «{number}» حذف شد.')
    return redirect('prescription_list')


# ═══════════════════════════════════════════════════════════════════
# 🔧 Shared helper — save medicines from POST
# ═══════════════════════════════════════════════════════════════════

def _save_prescription_items_from_post(request, prescription):
    """Save all prescription items from POST. Includes quantity."""
    med_ids     = request.POST.getlist('medication[]')
    doses       = request.POST.getlist('dose[]')
    frequencies = request.POST.getlist('frequency[]')
    timings     = request.POST.getlist('timing[]')
    routes      = request.POST.getlist('route[]')
    durations   = request.POST.getlist('duration[]')
    quantities  = request.POST.getlist('quantity[]')

    for i in range(len(med_ids)):
        med_id = med_ids[i] if i < len(med_ids) else ''
        if not med_id:
            continue

        raw_qty = quantities[i] if i < len(quantities) else ''
        try:
            qty = int(raw_qty) if raw_qty not in ('', None) else None
            if qty is not None and qty < 1:
                qty = None
        except (ValueError, TypeError):
            qty = None

        PrescriptionItem.objects.create(
            prescription=prescription,
            medication_id=med_id,
            dose=doses[i] if i < len(doses) else '',
            frequency=frequencies[i] if i < len(frequencies) else '',
            timing=timings[i] if i < len(timings) else '',
            route=routes[i] if i < len(routes) else 'oral',
            duration=durations[i] if i < len(durations) else '',
            quantity=qty,
            order=i,
        )


# ═══════════════════════════════════════════════════════════════════
# 📋 READY PRESCRIPTIONS  —  full CRUD
# ═══════════════════════════════════════════════════════════════════

def ready_prescription_list(request):
    """List + create + edit + delete ready prescriptions."""

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ➕ CREATE
        if action == 'create':
            form = ReadyPrescriptionForm(request.POST)
            if form.is_valid():
                rp = form.save(commit=False)
                rp.medications = _parse_medications_from_post(request)
                rp.save()
                messages.success(request, f'نسخه آماده «{rp.title}» ساخته شد.')
                return redirect('ready_prescription_list')

            first_error = _get_first_form_error(form)
            return _render_ready_list(
                request, form=form, open_modal='create', modal_error=first_error,
            )

        # ✏️ UPDATE
        elif action == 'update':
            rp = get_object_or_404(ReadyPrescription, pk=request.POST.get('ready_id'))
            form = ReadyPrescriptionForm(request.POST, instance=rp)
            if form.is_valid():
                rp = form.save(commit=False)
                rp.medications = _parse_medications_from_post(request)
                rp.save()
                messages.success(request, f'نسخه آماده «{rp.title}» بروزرسانی شد.')
                return redirect('ready_prescription_list')

            first_error = _get_first_form_error(form)
            return _render_ready_list(
                request, form=form, edit_ready=rp,
                open_modal='update', modal_error=first_error,
            )

        # 🗑️ DELETE
        elif action == 'delete':
            rp = get_object_or_404(ReadyPrescription, pk=request.POST.get('ready_id'))
            title = rp.title
            rp.delete()
            messages.success(request, f'نسخه آماده «{title}» حذف شد.')
            return redirect('ready_prescription_list')

        # ⭐ TOGGLE FAVORITE
        elif action == 'toggle_favorite':
            rp = get_object_or_404(ReadyPrescription, pk=request.POST.get('ready_id'))
            rp.is_favorite = not rp.is_favorite
            rp.save(update_fields=['is_favorite', 'updated_at'])
            messages.success(
                request,
                f'«{rp.title}» {"پرکاربرد" if rp.is_favorite else "عادی"} شد.'
            )
            return redirect('ready_prescription_list')

        # ⚡ TOGGLE ACTIVE
        elif action == 'toggle_active':
            rp = get_object_or_404(ReadyPrescription, pk=request.POST.get('ready_id'))
            rp.is_active = not rp.is_active
            rp.save(update_fields=['is_active', 'updated_at'])
            messages.success(
                request,
                f'«{rp.title}» {"فعال" if rp.is_active else "غیرفعال"} شد.'
            )
            return redirect('ready_prescription_list')

    # GET
    qs = ReadyPrescription.objects.all()

    search_query    = request.GET.get('search', '').strip()
    favorite_filter = request.GET.get('favorite', '').strip()
    active_filter   = request.GET.get('active', '').strip()

    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query) |
            Q(signs_symptoms__icontains=search_query) |
            Q(diagnosis__icontains=search_query) |
            Q(impression__icontains=search_query)
        )

    if favorite_filter == '1':
        qs = qs.filter(is_favorite=True)

    if active_filter == '1':
        qs = qs.filter(is_active=True)
    elif active_filter == '0':
        qs = qs.filter(is_active=False)

    qs = qs.order_by('-is_favorite', 'title')

    stats = {
        'total':      ReadyPrescription.objects.count(),
        'active':     ReadyPrescription.objects.filter(is_active=True).count(),
        'favorites':  ReadyPrescription.objects.filter(is_favorite=True).count(),
        'meds_total': sum(rp.medications_count for rp in ReadyPrescription.objects.all()),
    }

    return _render_ready_list(
        request, qs=qs,
        search_query=search_query,
        favorite_filter=favorite_filter,
        active_filter=active_filter,
        stats=stats,
    )


def _render_ready_list(
    request, qs=None,
    search_query='', favorite_filter='', active_filter='',
    stats=None, form=None, edit_ready=None,
    open_modal=None, modal_error=None,
):
    if qs is None:
        qs = ReadyPrescription.objects.all().order_by('-is_favorite', 'title')

    if stats is None:
        stats = {
            'total':      ReadyPrescription.objects.count(),
            'active':     ReadyPrescription.objects.filter(is_active=True).count(),
            'favorites':  ReadyPrescription.objects.filter(is_favorite=True).count(),
            'meds_total': sum(rp.medications_count for rp in ReadyPrescription.objects.all()),
        }

    return render(request, 'prescription/ready_prescription_list.html', {
        'ready_prescriptions': qs,
        'search_query': search_query,
        'favorite_filter': favorite_filter,
        'active_filter': active_filter,
        'stats': stats,
        'form': form or ReadyPrescriptionForm(),
        'edit_ready': edit_ready,
        'open_modal': open_modal,
        'modal_error': modal_error,
        'page_title': 'نسخه‌های آماده',
        'active_nav': 'ready_prescriptions',
    })


def _parse_medications_from_post(request):
    """Parse medicines from POST — includes quantity."""
    medications = []
    med_ids     = request.POST.getlist('medication[]')
    doses       = request.POST.getlist('dose[]')
    frequencies = request.POST.getlist('frequency[]')
    timings     = request.POST.getlist('timing[]')
    routes      = request.POST.getlist('route[]')
    durations   = request.POST.getlist('duration[]')
    quantities  = request.POST.getlist('quantity[]')

    for i in range(len(med_ids)):
        med_id = med_ids[i] if i < len(med_ids) else ''
        if not med_id:
            continue

        raw_qty = quantities[i] if i < len(quantities) else ''
        try:
            qty = int(raw_qty) if raw_qty not in ('', None) else None
            if qty is not None and qty < 1:
                qty = None
        except (ValueError, TypeError):
            qty = None

        medications.append({
            'medication_id': int(med_id),
            'dose': doses[i] if i < len(doses) else '',
            'frequency': frequencies[i] if i < len(frequencies) else '',
            'timing': timings[i] if i < len(timings) else '',
            'route': routes[i] if i < len(routes) else 'oral',
            'duration': durations[i] if i < len(durations) else '',
            'quantity': qty,
        })

    return medications


@require_http_methods(["GET"])
def api_ready_prescription_detail(request, pk):
    """Full detail for the View / Edit modals."""
    rp = get_object_or_404(ReadyPrescription, pk=pk)

    med_ids = [
        item.get('medication_id')
        for item in (rp.medications or [])
        if item.get('medication_id')
    ]

    med_map = {
        m.id: m for m in Medication.objects.filter(pk__in=med_ids)
    }

    FREQ_LABELS = {
        '1x':   'Once Daily — روزی ۱ بار',
        '2x':   'Twice Daily — روزی ۲ بار',
        '3x':   'Three Times Daily — روزی ۳ بار',
        '4x':   'Four Times Daily — روزی ۴ بار',
        'q6h':  'Every 6 Hours — هر ۶ ساعت',
        'q8h':  'Every 8 Hours — هر ۸ ساعت',
        'q12h': 'Every 12 Hours — هر ۱۲ ساعت',
        'prn':  'As Needed — در صورت نیاز',
        'stat': 'STAT — فوری',
    }
    TIMING_LABELS = {
        'before_meal':   'Before Meal — قبل از غذا',
        'after_meal':    'After Meal — بعد از غذا',
        'with_meal':     'With Meal — همراه با غذا',
        'empty_stomach': 'Empty Stomach — با معده خالی',
        'at_bedtime':    'At Bedtime — قبل از خواب',
        'morning':       'Morning — صبح',
        'evening':       'Evening — شب',
        'any_time':      'Any Time — هر زمان',
    }
    ROUTE_LABELS = {
        'oral':       'Oral — خوراکی',
        'topical':    'Topical — موضعی',
        'injection':  'Injection — تزریقی',
        'inhalation': 'Inhalation — استنشاقی',
        'rectal':     'Rectal — مقعدی',
        'eye':        'Eye — چشمی',
        'ear':        'Ear — گوشی',
        'nasal':      'Nasal — بینی',
    }

    def _label(val, mapping):
        if not val:
            return ''
        return mapping.get(val, val)

    meds = []
    for item in (rp.medications or []):
        med_id = item.get('medication_id')
        med_obj = med_map.get(med_id) if med_id else None

        drug_name = ''
        if med_obj:
            drug_name = med_obj.full_name or med_obj.name or ''

        qty = item.get('quantity')
        try:
            qty = int(qty) if qty not in ('', None) else None
        except (ValueError, TypeError):
            qty = None

        meds.append({
            'medication_id': med_id,
            'drug_name': drug_name,
            'drug_generic_name': med_obj.generic_name if med_obj else '',
            'drug_form': med_obj.get_form_display() if med_obj else '',
            'drug_manufacturer': med_obj.manufacturer if med_obj else '',

            'dose': item.get('dose', '') or '',
            'frequency': item.get('frequency', '') or '',
            'frequency_display': _label(item.get('frequency'), FREQ_LABELS),
            'timing': item.get('timing', '') or '',
            'timing_display': _label(item.get('timing'), TIMING_LABELS),
            'route': item.get('route', 'oral') or 'oral',
            'route_display': _label(item.get('route', 'oral'), ROUTE_LABELS),
            'duration': item.get('duration', '') or '',
            'quantity': qty,
            'quantity_display': f"n={qty}" if qty else '',
        })

    return JsonResponse({
        'success': True,
        'ready': {
            'id': rp.id,
            'title': rp.title,
            'signs_symptoms': rp.signs_symptoms or '',
            'diagnosis': rp.diagnosis or '',
            'impression': rp.impression or '',
            'doctor_note': rp.doctor_note or '',
            'advice': rp.advice or '',
            'is_active': rp.is_active,
            'is_favorite': rp.is_favorite,
            'medications': meds,
            'medications_count': len(meds),
        }
    })


# ═══════════════════════════════════════════════════════════════════
# 🎨 TEMPLATES  —  full CRUD + editor
# ═══════════════════════════════════════════════════════════════════

def template_list(request):
    templates = PrescriptionTemplate.objects.prefetch_related('fields')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = PrescriptionTemplateForm(request.POST, request.FILES)
            if form.is_valid():
                template = form.save()
                messages.success(request, f'دیزاین «{template.name}» ساخته شد.')
                return redirect('template_edit', pk=template.pk)
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f'{field}: {e}')

        elif action == 'delete':
            tpl = get_object_or_404(PrescriptionTemplate, pk=request.POST.get('template_id'))
            name = tpl.name
            if tpl.prescriptions.count() > 0:
                tpl.is_active = False
                tpl.is_default = False
                tpl.save()
                messages.warning(request, f'دیزاین «{name}» غیرفعال شد.')
            else:
                if tpl.background_image:
                    try:
                        tpl.background_image.delete(save=False)
                    except Exception:
                        pass
                tpl.delete()
                messages.success(request, f'دیزاین «{name}» حذف شد.')
            return redirect('template_list')

        elif action == 'set_default':
            tpl = get_object_or_404(PrescriptionTemplate, pk=request.POST.get('template_id'))
            tpl.is_default = True
            tpl.save()
            messages.success(request, f'دیزاین «{tpl.name}» پیش‌فرض شد.')
            return redirect('template_list')

    stats = {
        'total': templates.count(),
        'active': templates.filter(is_active=True).count(),
        'default': templates.filter(is_default=True).count(),
    }

    return render(request, 'prescription/template_list.html', {
        'templates': templates,
        'stats': stats,
        'form': PrescriptionTemplateForm(),
        'page_title': 'دیزاین‌های نسخه',
        'active_nav': 'templates',
    })


def template_edit(request, pk):
    template = get_object_or_404(
        PrescriptionTemplate.objects.prefetch_related('fields'),
        pk=pk
    )

    if request.method == 'POST':
        form = PrescriptionTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'اطلاعات دیزاین ذخیره شد.')
            return redirect('template_edit', pk=template.pk)
    else:
        form = PrescriptionTemplateForm(instance=template)

    existing_fields = template.fields.all().order_by('order', 'id')

    fields_data = [{
        'id': f.id, 'field_type': f.field_type, 'label': f.display_label,
        'x': f.x, 'y': f.y, 'width': f.width, 'height': f.height,
        'padding': f.padding, 'line_height': f.line_height,
        'font_family': f.font_family, 'font_size': f.font_size,
        'font_weight': f.font_weight, 'color': f.color,
        'text_align': f.text_align,
        'has_shadow': f.has_shadow, 'shadow_color': f.shadow_color,
        'has_stroke': f.has_stroke, 'stroke_color': f.stroke_color,
        'stroke_width': f.stroke_width,
        'date_format': f.date_format, 'date_separator': f.date_separator,
        'medicine_options': f.medicine_options or {},
        'order': f.order,
    } for f in existing_fields]

    return render(request, 'prescription/editor.html', {
        'template': template,
        'form': form,
        'existing_fields': existing_fields,
        'fields_json': _safe_json_dumps(fields_data),
        'font_choices_json': _safe_json_dumps([[v, l] for v, l in FONT_CHOICES]),
        'date_format_choices_json': _safe_json_dumps([[v, l] for v, l in DATE_FORMAT_CHOICES]),
        'date_separator_choices_json': _safe_json_dumps([[v, l] for v, l in DATE_SEPARATOR_CHOICES]),
        'medicine_options_json': _safe_json_dumps(DEFAULT_MEDICINE_OPTIONS),
        'preview_data_json': _safe_json_dumps(_get_preview_data()),
        'preview_medicines_json': _safe_json_dumps(_get_preview_medicines()),
        'page_title': f'ویرایش دیزاین: {template.name}',
        'active_nav': 'templates',
    })


def template_delete(request, pk):
    if request.method != 'POST':
        return redirect('template_list')

    tpl = get_object_or_404(PrescriptionTemplate, pk=pk)
    name = tpl.name
    if tpl.prescriptions.count() > 0:
        tpl.is_active = False
        tpl.is_default = False
        tpl.save()
        messages.warning(request, f'دیزاین «{name}» غیرفعال شد.')
    else:
        if tpl.background_image:
            try:
                tpl.background_image.delete(save=False)
            except Exception:
                pass
        tpl.delete()
        messages.success(request, f'دیزاین «{name}» حذف شد.')
    return redirect('template_list')


def template_set_default(request, pk):
    if request.method != 'POST':
        return redirect('template_list')

    tpl = get_object_or_404(PrescriptionTemplate, pk=pk)
    tpl.is_default = True
    tpl.save()
    messages.success(request, f'دیزاین «{tpl.name}» پیش‌فرض شد.')
    return redirect('template_list')


# ═══════════════════════════════════════════════════════════════════
# 🔌 API — Templates
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_get_fields(request, pk):
    template = get_object_or_404(PrescriptionTemplate, pk=pk)
    fields = [{
        'id': f.id, 'field_type': f.field_type, 'label': f.display_label,
        'x': f.x, 'y': f.y, 'width': f.width, 'height': f.height,
        'padding': f.padding, 'line_height': f.line_height,
        'font_family': f.font_family, 'font_size': f.font_size,
        'font_weight': f.font_weight, 'color': f.color,
        'text_align': f.text_align,
        'has_shadow': f.has_shadow, 'shadow_color': f.shadow_color,
        'has_stroke': f.has_stroke, 'stroke_color': f.stroke_color,
        'stroke_width': f.stroke_width,
        'date_format': f.date_format, 'date_separator': f.date_separator,
        'medicine_options': f.medicine_options or {},
        'order': f.order,
    } for f in template.fields.all().order_by('order', 'id')]

    return JsonResponse({'success': True, 'fields': fields})


@require_http_methods(["POST"])
def api_save_fields(request, pk):
    template = get_object_or_404(PrescriptionTemplate, pk=pk)
    try:
        data = json.loads(request.body)
        fields_data = data.get('fields', [])

        new_ids = [f.get('id') for f in fields_data if f.get('id')]
        template.fields.exclude(id__in=new_ids).delete()

        def safe_int(val, default):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default

        def safe_float(val, default):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        for fd in fields_data:
            field_id = fd.get('id')
            values = {
                'field_type': fd.get('field_type'),
                'label': fd.get('label', ''),
                'x': max(0, safe_int(fd.get('x'), 100)),
                'y': max(0, safe_int(fd.get('y'), 100)),
                'width': max(0, safe_int(fd.get('width'), 300)),
                'height': max(0, safe_int(fd.get('height'), 0)),
                'padding': max(0, safe_int(fd.get('padding'), 0)),
                'line_height': safe_float(fd.get('line_height'), 1.4),
                'font_family': fd.get('font_family', 'Vazirmatn'),
                'font_size': max(8, safe_int(fd.get('font_size'), 14)),
                'font_weight': fd.get('font_weight', 'normal'),
                'color': fd.get('color', '#0f172a'),
                'text_align': fd.get('text_align', 'right'),
                'has_shadow': bool(fd.get('has_shadow', False)),
                'shadow_color': fd.get('shadow_color', '#000000'),
                'has_stroke': bool(fd.get('has_stroke', False)),
                'stroke_color': fd.get('stroke_color', '#ffffff'),
                'stroke_width': safe_int(fd.get('stroke_width'), 1),
                'date_format': fd.get('date_format', 'YYYY/MM/DD'),
                'date_separator': fd.get('date_separator', '/'),
                'medicine_options': fd.get('medicine_options', {}) or {},
                'order': safe_int(fd.get('order'), 0),
            }
            if field_id:
                TemplateField.objects.filter(id=field_id, template=template).update(**values)
            else:
                TemplateField.objects.create(template=template, **values)

        return JsonResponse({'success': True, 'count': len(fields_data)})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON نامعتبر'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def api_upload_background(request, pk):
    template = get_object_or_404(PrescriptionTemplate, pk=pk)
    try:
        if 'background_image' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'فایل یافت نشد.'}, status=400)
        image = request.FILES['background_image']
        if not image.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'فقط تصویر.'}, status=400)
        if image.size > 20 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'حجم زیاد.'}, status=400)
        if template.background_image:
            try:
                template.background_image.delete(save=False)
            except Exception:
                pass
        template.background_image = image
        template.save(update_fields=['background_image', 'updated_at'])
        return JsonResponse({'success': True, 'image_url': template.background_image.url})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_get_fonts(request):
    return JsonResponse({
        'success': True,
        'fonts': [{'value': v, 'label': l} for v, l in FONT_CHOICES],
        'date_formats': [{'value': v, 'label': l} for v, l in DATE_FORMAT_CHOICES],
        'date_separators': [{'value': v, 'label': l} for v, l in DATE_SEPARATOR_CHOICES],
    })


# ═══════════════════════════════════════════════════════════════════
# 🔌 API — Search
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_search_medications(request):
    query = request.GET.get('q', '').strip()
    qs = Medication.objects.filter(is_active=True)

    if query and len(query) >= 1:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(manufacturer__icontains=query)
        )
    qs = qs.order_by('-is_favorite', 'name')[:100]

    results = [{
        'id': m.id,
        'name': m.name,
        'full_name': m.full_name,
        'generic_name': m.generic_name,
        'strength': m.strength,
        'unit': m.unit,
        'form': m.form,
        'form_display': m.get_form_display(),
        'manufacturer': m.manufacturer,
        'default_dose': m.default_dose,
        'default_frequency': m.default_frequency,
        'default_timing': m.default_timing,
        'default_route': m.default_route,
        'default_duration': m.default_duration,
        'is_favorite': m.is_favorite,
    } for m in qs]

    return JsonResponse({'results': results})


@require_http_methods(["GET"])
def api_search_patients(request):
    """Live search for patients."""
    query = request.GET.get('q', '').strip()

    if not query:
        qs = Patient.objects.all().order_by('-id')[:15]
    else:
        qs = Patient.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(father_name__icontains=query) |
            Q(phone__icontains=query)
        ).order_by('-id')[:20]

    results = []
    for p in qs:
        full_name = ''
        try:
            full_name = p.full_name or f"{p.first_name} {p.last_name}"
        except Exception:
            full_name = f"{p.first_name} {p.last_name}"

        initials = ''
        if p.first_name:
            initials += p.first_name[0].upper()
        if p.last_name:
            initials += p.last_name[0].upper()

        age = getattr(p, 'age', None)
        if callable(age):
            try:
                age = age()
            except Exception:
                age = None

        gender_display = ''
        if hasattr(p, 'get_gender_display'):
            try:
                gender_display = p.get_gender_display()
            except Exception:
                gender_display = getattr(p, 'gender', '')

        results.append({
            'id': p.id,
            'first_name': p.first_name or '',
            'last_name': p.last_name or '',
            'father_name': p.father_name or '',
            'full_name': full_name,
            'initials': initials or '؟',
            'age': str(age) if age else '',
            'gender': gender_display or '',
            'phone': getattr(p, 'phone', '') or '',
            'file_number': getattr(p, 'file_number', '') or '',
        })

    return JsonResponse({'results': results})