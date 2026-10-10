# apps/prescription/forms.py

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import (
    Prescription,
    PrescriptionItem,
    ReadyPrescription,
    PrescriptionTemplate,
    TemplateField,
)

from .constants import (
    FONT_CHOICES,
    DATE_FORMAT_CHOICES,
    DATE_SEPARATOR_CHOICES,
)


# ══════════════════════════════════════════════════════════════════
# ⚠️ IMPORTANT — Medication now lives in the `medicine` app.
#    If you need a MedicationForm here, import it like this:
#
#       from medicine.models import Medication
#
#    It is intentionally NOT defined in this file anymore.
# ══════════════════════════════════════════════════════════════════


# ==================================================================
# 📝 فرم نسخه (Prescription)
# ==================================================================

class PrescriptionForm(forms.ModelForm):
    """فرم ثبت و ویرایش نسخه."""

    class Meta:
        model = Prescription
        fields = [
            "patient",
            "template",
            "prescription_date",

            # Clinical
            "signs_symptoms",
            "diagnosis",
            "impression",
            "doctor_note",

            # Vitals
            "blood_pressure",
            "pulse",
            "temperature",
            "respiratory_rate",
            "spo2",
            "weight",
            "height",
        ]
        widgets = {
            "patient": forms.Select(attrs={
                "class": "rx-form-control",
                "id": "id_patient",
            }),
            "template": forms.Select(attrs={
                "class": "rx-form-control",
                "id": "id_template",
            }),
            "prescription_date": forms.DateInput(attrs={
                "class": "rx-form-control",
                "type": "date",
                "id": "id_prescription_date",
            }),

            # Clinical
            "signs_symptoms": forms.Textarea(attrs={
                "class": "rx-form-textarea",
                "rows": 3,
                "placeholder": "تب، سرفه، گلودرد...",
                "id": "id_signs_symptoms",
            }),
            "diagnosis": forms.TextInput(attrs={
                "class": "rx-form-control",
                "placeholder": "تشخیص قطعی...",
                "id": "id_diagnosis",
            }),
            "impression": forms.Textarea(attrs={
                "class": "rx-form-textarea",
                "rows": 3,
                "placeholder": "برداشت بالینی داکتر...",
                "id": "id_impression",
            }),
            "doctor_note": forms.Textarea(attrs={
                "class": "rx-form-textarea",
                "rows": 2,
                "placeholder": "یادداشت داکتر...",
                "id": "id_doctor_note",
            }),

            # Vitals
            "blood_pressure": forms.TextInput(attrs={
                "class": "rx-form-control",
                "placeholder": "120/80",
                "id": "id_blood_pressure",
            }),
            "pulse": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "72",
                "id": "id_pulse",
            }),
            "temperature": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "37.0",
                "step": "0.1",
                "id": "id_temperature",
            }),
            "respiratory_rate": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "16",
                "id": "id_respiratory_rate",
            }),
            "spo2": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "98",
                "id": "id_spo2",
            }),
            "weight": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "75",
                "step": "1",
                "id": "id_weight",
            }),
            "height": forms.NumberInput(attrs={
                "class": "rx-form-control",
                "placeholder": "175",
                "step": "1",
                "id": "id_height",
            }),
        }
        labels = {
            "patient": "مریض *",
            "template": "دیزاین نسخه *",
            "prescription_date": "تاریخ نسخه *",
            "signs_symptoms": "علائم و نشانه‌ها",
            "diagnosis": "تشخیص",
            "impression": "برداشت بالینی",
            "doctor_note": "یادداشت داکتر",
            "blood_pressure": "BP — فشار خون",
            "pulse": "Pulse — نبض",
            "temperature": "Temp — دما",
            "respiratory_rate": "RR — تنفس",
            "spo2": "SpO₂ — اکسیژن",
            "weight": "Weight — وزن",
            "height": "Height — قد",
        }
        error_messages = {
            "patient": {"required": "انتخاب مریض الزامی است."},
            "template": {"required": "انتخاب دیزاین الزامی است."},
            "prescription_date": {"required": "تاریخ نسخه الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # queryset دیزاین‌ها
        self.fields["template"].queryset = (
            PrescriptionTemplate.objects
            .filter(is_active=True)
            .order_by("-is_default", "name")
        )

        # مقادیر پیش‌فرض
        if not self.instance.pk:
            self.fields["prescription_date"].initial = timezone.localdate()

            default_tpl = PrescriptionTemplate.objects.filter(
                is_default=True, is_active=True
            ).first()
            if default_tpl:
                self.fields["template"].initial = default_tpl

        # همه فیلدهای بالینی اختیاری
        for f in [
            "signs_symptoms", "diagnosis", "impression", "doctor_note",
            "blood_pressure", "pulse", "temperature",
            "respiratory_rate", "spo2", "weight", "height",
        ]:
            if f in self.fields:
                self.fields[f].required = False


# ==================================================================
# 💊 فرم دواهای نسخه (PrescriptionItem)
# ==================================================================

class PrescriptionItemForm(forms.ModelForm):
    """فرم یک دوا در نسخه."""

    class Meta:
        model = PrescriptionItem
        fields = [
            "medication",
            "dose", "frequency", "timing", "route",
            "duration",
            "quantity",           # ⭐ NEW
            "order",
        ]
        widgets = {
            "medication": forms.Select(attrs={
                "class": "form-select item-medication",
            }),
            "dose": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "1 tab",
            }),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "timing": forms.Select(attrs={"class": "form-select"}),
            "route": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "5 days",
            }),
            # ⭐ NEW — quantity input
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "مثلاً 2، 3، 21",
                "min": 1,
            }),
            "order": forms.HiddenInput(),
        }
        labels = {
            "medication": "دوا",
            "dose": "دوز",
            "frequency": "دفعات",
            "timing": "زمان مصرف",
            "route": "طریقه",
            "duration": "مدت",
            "quantity": "تعداد (n)",        # ⭐ NEW
        }
        error_messages = {
            "quantity": {
                "invalid": "تعداد باید یک عدد صحیح مثبت باشد.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # lazy import: Medication is in the `medicine` app
        from medicine.models import Medication

        self.fields["medication"].queryset = (
            Medication.objects.filter(is_active=True)
            .order_by("-is_favorite", "name")
        )

        for f in [
            "medication", "dose", "frequency",
            "timing", "route", "duration",
            "quantity",                       # ⭐ optional
        ]:
            if f in self.fields:
                self.fields[f].required = False

    def clean(self):
        cleaned_data = super().clean()
        medication = cleaned_data.get("medication")

        # Skip validation for empty (deleted / extra) rows
        if not medication and not any(
            cleaned_data.get(f) for f in
            ("dose", "frequency", "timing", "route", "duration", "quantity")
        ):
            return cleaned_data

        if not medication:
            raise forms.ValidationError(
                "انتخاب دوا از بانک الزامی است."
            )

        # ⭐ Validate quantity is a positive integer if provided
        quantity = cleaned_data.get("quantity")
        if quantity is not None and quantity < 1:
            raise forms.ValidationError(
                "تعداد باید حداقل ۱ باشد."
            )

        return cleaned_data


# ==================================================================
# 🎯 FormSet دواهای نسخه
# ==================================================================

class BasePrescriptionItemFormSet(forms.BaseInlineFormSet):
    """اعتبارسنجی: حداقل یک دوا لازم است."""

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        valid = 0
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("medication"):
                valid += 1

        if valid == 0:
            raise forms.ValidationError("حداقل یک دوا در نسخه لازم است.")


PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    formset=BasePrescriptionItemFormSet,
    extra=3,
    min_num=1,
    validate_min=False,
    can_delete=True,
    can_delete_extra=True,
    max_num=20,
    validate_max=True,
)


# ==================================================================
# 📋 فرم نسخه آماده (ReadyPrescription)
# ==================================================================

class ReadyPrescriptionForm(forms.ModelForm):
    """فرم ثبت و ویرایش نسخه آماده."""

    class Meta:
        model = ReadyPrescription
        fields = [
            "title",
            "signs_symptoms",
            "diagnosis",
            "impression",
            "doctor_note",
            "advice",
            "is_active",
            "is_favorite",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "rp-form-control",
                "placeholder": "مثلاً: سرماخوردگی بزرگسال",
                "autocomplete": "off",
            }),
            "signs_symptoms": forms.Textarea(attrs={
                "class": "rp-form-control",
                "rows": 3,
                "placeholder": "تب، سرفه، گلودرد، آبریزش بینی...",
            }),
            "diagnosis": forms.TextInput(attrs={
                "class": "rp-form-control",
                "placeholder": "مثلاً: عفونت تنفسی فوقانی",
            }),
            "impression": forms.Textarea(attrs={
                "class": "rp-form-control",
                "rows": 2,
                "placeholder": "جمع‌بندی بالینی کوتاه...",
            }),
            "doctor_note": forms.Textarea(attrs={
                "class": "rp-form-control",
                "rows": 2,
                "placeholder": "یادداشت داکتر...",
            }),
            "advice": forms.Textarea(attrs={
                "class": "rp-form-control",
                "rows": 3,
                "placeholder": "استراحت، مصرف مایعات، گرم نگه‌داشتن گلو...",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_favorite": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "title": "عنوان *",
            "signs_symptoms": "علائم و نشانه‌ها",
            "diagnosis": "تشخیص",
            "impression": "برداشت بالینی",
            "doctor_note": "یادداشت داکتر",
            "advice": "توصیه‌ها",
            "is_active": "فعال است",
            "is_favorite": "پرکاربرد",
        }
        error_messages = {
            "title": {"required": "عنوان الزامی است."},
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("عنوان الزامی است.")
        return title


# ==================================================================
# 🎨 فرم دیزاین نسخه (PrescriptionTemplate)
# ==================================================================

class PrescriptionTemplateForm(forms.ModelForm):
    """فرم ساخت و ویرایش دیزاین نسخه."""

    class Meta:
        model = PrescriptionTemplate
        fields = [
            "name", "description",
            "background_image",
            "is_default", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: نسخه A5 کلینیک",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "توضیحات اختیاری",
            }),
            "background_image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*",
                "id": "id_background_image",
            }),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "نام دیزاین *",
            "description": "توضیحات",
            "background_image": "عکس پس‌زمینه *",
            "is_default": "دیزاین پیش‌فرض",
            "is_active": "فعال است",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # اگر در حال ویرایش هستیم و عکس وجود دارد → عکس اختیاری
        if self.instance.pk and self.instance.background_image:
            self.fields["background_image"].required = False


# ==================================================================
# 🧩 فرم فیلد دیزاین (TemplateField)
# ==================================================================

class TemplateFieldForm(forms.ModelForm):
    """فرم یک فیلد مقداری روی دیزاین."""

    class Meta:
        model = TemplateField
        fields = [
            "field_type", "label",
            "x", "y", "width", "height",
            "padding", "line_height",
            "font_family", "font_size", "font_weight",
            "color", "text_align",
            "has_shadow", "shadow_color",
            "has_stroke", "stroke_color", "stroke_width",
            "date_format", "date_separator",
            "order",
        ]
        widgets = {
            "field_type": forms.Select(attrs={"class": "form-select"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "x": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "y": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "width": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "height": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "padding": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "line_height": forms.NumberInput(attrs={
                "class": "form-control", "min": 0.8, "max": 3, "step": 0.1,
            }),
            "font_family": forms.Select(attrs={"class": "form-select"}),
            "font_size": forms.NumberInput(attrs={
                "class": "form-control", "min": 8, "max": 300,
            }),
            "font_weight": forms.Select(attrs={"class": "form-select"}),
            "color": forms.TextInput(attrs={
                "class": "form-control form-control-color", "type": "color",
            }),
            "text_align": forms.Select(attrs={"class": "form-select"}),
            "has_shadow": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "shadow_color": forms.TextInput(attrs={
                "class": "form-control form-control-color", "type": "color",
            }),
            "has_stroke": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "stroke_color": forms.TextInput(attrs={
                "class": "form-control form-control-color", "type": "color",
            }),
            "stroke_width": forms.NumberInput(attrs={
                "class": "form-control", "min": 1, "max": 10,
            }),
            "date_format": forms.Select(attrs={"class": "form-select"}),
            "date_separator": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }
        labels = {
            "field_type": "نوع فیلد *",
            "label": "برچسب",
            "x": "موقعیت X",
            "y": "موقعیت Y",
            "width": "عرض",
            "height": "ارتفاع",
            "padding": "فاصله داخلی",
            "line_height": "فاصله خطوط",
            "font_family": "فونت",
            "font_size": "اندازه فونت",
            "font_weight": "ضخامت",
            "color": "رنگ",
            "text_align": "چینش",
            "has_shadow": "سایه متن",
            "shadow_color": "رنگ سایه",
            "has_stroke": "خط دور متن",
            "stroke_color": "رنگ خط دور",
            "stroke_width": "ضخامت خط دور",
            "date_format": "فرمت تاریخ",
            "date_separator": "جداکننده تاریخ",
            "order": "ترتیب",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # فونت‌ها از constants
        self.fields["font_family"] = forms.ChoiceField(
            choices=FONT_CHOICES,
            widget=forms.Select(attrs={"class": "form-select"}),
            label="فونت",
            initial="Vazirmatn",
        )

        # فیلدهای اختیاری
        optional_fields = [
            "label", "width", "height", "padding", "line_height",
            "font_weight",
            "has_shadow", "shadow_color",
            "has_stroke", "stroke_color", "stroke_width",
            "date_format", "date_separator",
            "order",
        ]
        for f in optional_fields:
            if f in self.fields:
                self.fields[f].required = False


# ==================================================================
# 🎯 FormSet فیلدهای دیزاین
# ==================================================================

TemplateFieldFormSet = inlineformset_factory(
    PrescriptionTemplate,
    TemplateField,
    form=TemplateFieldForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
    max_num=100,
    validate_max=True,
)