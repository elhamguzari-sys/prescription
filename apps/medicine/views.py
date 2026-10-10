# apps/medicine/views.py

from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from .models import Medication
from .forms import MedicationForm


# ═══════════════════════════════════════════════════════════════════
# 💊 Medication Bank — List + Create + Update + Delete
# ═══════════════════════════════════════════════════════════════════

def medication_list(request):
    """List + create + update + delete medications"""

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ═══════════════════════════════════════════════════
        # ➕ CREATE
        # ═══════════════════════════════════════════════════
        if action == 'create':
            form = MedicationForm(request.POST)
            if form.is_valid():
                med = form.save()
                messages.success(request, f'دوا «{med.full_name}» اضافه شد.')
                return redirect('medication_list')

            first_error = _get_first_form_error(form)
            return _render_medication_list(
                request,
                form=form,
                open_modal='create',
                modal_error=first_error,
            )

        # ═══════════════════════════════════════════════════
        # ✏️ UPDATE
        # ═══════════════════════════════════════════════════
        elif action == 'update':
            med = get_object_or_404(Medication, pk=request.POST.get('medication_id'))
            form = MedicationForm(request.POST, instance=med)
            if form.is_valid():
                updated = form.save()
                messages.success(request, f'دوا «{updated.full_name}» بروزرسانی شد.')
                return redirect('medication_list')

            first_error = _get_first_form_error(form)
            return _render_medication_list(
                request,
                form=form,
                edit_medication=med,
                open_modal='update',
                modal_error=first_error,
            )

        # ═══════════════════════════════════════════════════
        # 🗑️ DELETE — no dependency checks in this app
        # ═══════════════════════════════════════════════════
        elif action == 'delete':
            med = get_object_or_404(Medication, pk=request.POST.get('medication_id'))
            name = med.full_name
            med.delete()
            messages.success(request, f'دوا «{name}» حذف شد.')
            return redirect('medication_list')

    return _render_medication_list(request)


# ═══════════════════════════════════════════════════════════════════
# 🖨️ Helper — Render medication list page
# ═══════════════════════════════════════════════════════════════════

def _render_medication_list(
    request,
    form=None,
    edit_medication=None,
    open_modal=None,
    modal_error=None,
):
    qs = Medication.objects.all().order_by('-is_favorite', 'name')

    search_query = request.GET.get('search', '').strip()
    form_filter = request.GET.get('form', '').strip()

    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) |
            Q(generic_name__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )

    if form_filter:
        qs = qs.filter(form=form_filter)

    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 15)
    try:
        medications = paginator.page(page_number)
    except PageNotAnInteger:
        medications = paginator.page(1)
    except EmptyPage:
        medications = paginator.page(paginator.num_pages)

    stats = {
        'total_count': Medication.objects.count(),
        'active_count': Medication.objects.filter(is_active=True).count(),
        'favorite_count': Medication.objects.filter(is_favorite=True).count(),
        'forms_count': Medication.objects.values('form').distinct().count(),
    }

    return render(request, 'medicine/medication_list.html', {
        'medications': medications,
        'search_query': search_query,
        'form_filter': form_filter,
        'form_choices': Medication.Form.choices,
        'paginator': paginator,
        'stats': stats,
        'page_title': 'بانک دواها',
        'form': form or MedicationForm(),
        'edit_medication': edit_medication,
        'open_modal': open_modal,
        'modal_error': modal_error,
        'active_nav': 'medications',
    })


def _get_first_form_error(form):
    """Get the first error message from the form as a simple string."""
    for field_name, errors in form.errors.items():
        for err in errors:
            return str(err)
    return 'لطفاً خطاهای فرم را اصلاح کنید.'


# ═══════════════════════════════════════════════════════════════════
# 🔌 API — Medication detail (for Edit / View modals via JS)
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_medication_detail(request, pk):
    med = get_object_or_404(Medication, pk=pk)
    return JsonResponse({
        'success': True,
        'medication': {
            'id': med.id,
            'name': med.name,
            'generic_name': med.generic_name,
            'form': med.form,
            'form_display': med.get_form_display(),
            'strength': med.strength,
            'unit': med.unit,
            'manufacturer': med.manufacturer,
            'default_dose': med.default_dose,
            'default_frequency': med.default_frequency,
            'default_timing': med.default_timing,
            'default_route': med.default_route,
            'default_duration': med.default_duration,
            'is_active': med.is_active,
            'is_favorite': med.is_favorite,
            'full_name': med.full_name,
        }
    })


# ═══════════════════════════════════════════════════════════════════
# 🔌 API — Medication search (for prescription form medicine dropdown)
# ═══════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_search_medications(request):
    query = request.GET.get('q', '').strip()
    qs = Medication.objects.filter(is_active=True)

    if query and len(query) >= 2:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(generic_name__icontains=query) |
            Q(manufacturer__icontains=query)
        )
    qs = qs.order_by('-is_favorite', 'name')[:20]

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