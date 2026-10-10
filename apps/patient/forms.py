from django import forms
from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "father_name",
            "gender",
            "age",
            "phone",
            "address",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "نام مریض",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "تخلص مریض",
            }),
            "father_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "نام پدر",
            }),
            "gender": forms.Select(attrs={
                "class": "form-control",
            }),
            "age": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "سن",
                "min": 0,
                "max": 150,
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "07XXXXXXXX (اختیاری)",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "آدرس (اختیاری)",
                "rows": 3,
            }),
        }
        labels = {
            "first_name": "نام",
            "last_name": "تخلص",
            "father_name": "نام پدر",
            "gender": "جنسیت",
            "age": "سن",
            "phone": "شماره تماس",
            "address": "آدرس",
        }
        error_messages = {
            "first_name": {"required": "نام الزامی است."},
            "last_name": {"required": "تخلص الزامی است."},
            "father_name": {"required": "نام پدر الزامی است."},
            "gender": {"required": "جنسیت را انتخاب کنید."},
            "age": {"required": "سن الزامی است."},
        }

    # --- اعتبارسنجی نام ---
    def clean_first_name(self):
        name = (self.cleaned_data.get("first_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("نام باید حداقل ۲ حرف باشد.")
        return name

    # --- اعتبارسنجی تخلص ---
    def clean_last_name(self):
        name = (self.cleaned_data.get("last_name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("تخلص باید حداقل ۲ حرف باشد.")
        return name

    # --- اعتبارسنجی شماره تماس (اختیاری) ---
    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return None
        if not phone.isdigit():
            raise forms.ValidationError("شماره تماس باید فقط عدد باشد.")
        if len(phone) < 9:
            raise forms.ValidationError("شماره تماس باید حداقل ۹ رقم باشد.")
        return phone

    # --- اعتبارسنجی آدرس (اختیاری) ---
    def clean_address(self):
        address = (self.cleaned_data.get("address") or "").strip()
        if not address:
            return None
        return address