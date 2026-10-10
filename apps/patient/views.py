# apps/patient/views.py

from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, ProtectedError
from .models import Patient
from .forms import PatientForm


def patient_list(request):
    """لیست + ثبت + ویرایش + حذف — همه در یک صفحه"""

    # ---------- POST: create / update / delete ----------
    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ----- CREATE -----
        if action == 'create':
            form = PatientForm(request.POST)
            if form.is_valid():
                patient = form.save()
                messages.success(
                    request,
                    f'مریض "{patient.first_name} {patient.last_name}" موفقانه ثبت شد.'
                )
                return redirect('patient_list')
            messages.error(request, 'لطفاً معلومات را درست وارد کنید.')
            return _render(request, form=form, open_modal='create')

        # ----- UPDATE -----
        elif action == 'update':
            patient = get_object_or_404(Patient, pk=request.POST.get('patient_id'))
            form = PatientForm(request.POST, instance=patient)
            if form.is_valid():
                updated = form.save()
                messages.success(
                    request,
                    f'معلومات مریض "{updated.first_name} {updated.last_name}" موفقانه تصحیح شد.'
                )
                return redirect('patient_list')
            messages.error(request, 'لطفاً معلومات را درست وارد کنید.')
            return _render(
                request,
                form=form,
                edit_patient=patient,
                open_modal='update',
            )

        # ----- DELETE — no dependency checks -----
        elif action == 'delete':
            patient = get_object_or_404(Patient, pk=request.POST.get('patient_id'))
            name = f'{patient.first_name} {patient.last_name}'

            try:
                patient.delete()
                messages.success(request, f'مریض "{name}" موفقانه حذف شد.')
            except ProtectedError:
                # Django will still raise this if other models have PROTECT FKs
                messages.error(
                    request,
                    f'⚠️ نمی‌توان مریض «{name}» را حذف کرد — وابستگی در سیستم وجود دارد.'
                )

            return redirect('patient_list')

    # ---------- GET ----------
    return _render(request)


def _render(request, form=None, edit_patient=None, open_modal=None):
    """Helper: shared context for the list page"""
    patients_list = Patient.objects.all().order_by('-id')

    search_query = request.GET.get('search', '').strip()
    gender_filter = request.GET.get('gender', '').strip()

    # ---------- Search ----------
    if search_query:
        patients_list = patients_list.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(father_name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    # ---------- Gender filter ----------
    if gender_filter in ('M', 'F'):
        patients_list = patients_list.filter(gender=gender_filter)

    # ---------- Pagination ----------
    page_number = request.GET.get('page', 1)
    paginator = Paginator(patients_list, 10)

    try:
        patients = paginator.page(page_number)
    except PageNotAnInteger:
        patients = paginator.page(1)
    except EmptyPage:
        patients = paginator.page(paginator.num_pages)

    return render(request, 'patient/patient_list.html', {
        'patients': patients,
        'search_query': search_query,
        'gender_filter': gender_filter,
        'paginator': paginator,
        'page_title': 'لیست مریضان',
        'form': form or PatientForm(),
        'edit_patient': edit_patient,
        'open_modal': open_modal,
        'active_nav': 'patients',
    })