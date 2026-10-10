# apps/prescription/forms.py

from django import forms
from .models import Medication


class MedicationForm(forms.ModelForm):
    """فرم ثبت و ویرایش دوا در بانک دواها."""

    class Meta:
        model = Medication
        fields = [
            "name", "generic_name",
            "form", "strength", "unit", "manufacturer",
            "default_dose", "default_frequency", "default_timing",
            "default_route", "default_duration",
            "is_active", "is_favorite",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: Paracetamol",
                "autocomplete": "off",
            }),
            "generic_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "نام علمی (اختیاری)",
            }),
            "form": forms.Select(attrs={"class": "form-select"}),
            "strength": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: 500",
            }),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "manufacturer": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "شرکت سازنده",
            }),
            "default_dose": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: 1 Tablet",
            }),
            "default_duration": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: 7 Days",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_favorite": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "نام دوا *",
            "generic_name": "نام جنریک",
            "form": "شکل دوا",
            "strength": "قدرت",
            "unit": "واحد",
            "manufacturer": "شرکت سازنده",
            "default_dose": "Default Dose (دوز پیش‌فرض)",
            "default_frequency": "Default Frequency (دفعات پیش‌فرض)",
            "default_timing": "Default Timing (زمان مصرف پیش‌فرض)",
            "default_route": "Default Route (طریقه مصرف پیش‌فرض)",
            "default_duration": "Default Duration (مدت پیش‌فرض)",
            "is_active": "فعال است",
            "is_favorite": "دوا پرکاربرد",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Convert ChoiceFields to CharFields so custom text is accepted
        for field_name in ("default_frequency", "default_timing", "default_route"):
            if field_name not in self.fields:
                continue

            old = self.fields[field_name]

            self.fields[field_name] = forms.CharField(
                required=False,
                max_length=getattr(old, "max_length", 50) or 50,
                label=old.label,
                initial=old.initial,
                widget=forms.TextInput(attrs={
                    "class": "form-control",
                    "placeholder": "جستجو یا تایپ کنید...",
                    "autocomplete": "off",
                }),
            )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("نام دوا الزامی است.")
        qs = Medication.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("دوایی با این نام قبلاً ثبت شده است.")
        return name