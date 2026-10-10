# apps/prescription/constants.py

"""
متمرکز کردن لیست فونت‌ها، فرمت‌های تاریخ، و تنظیمات نمایش دواها روی نسخه.
"""

# ==================================================================
# 📝 فونت‌های موجود
# ==================================================================

FONT_CHOICES = [
    ("Vazirmatn", "وزیرمتن"),
    ("Parastoo", "پرستو"),
    ("Tahoma", "Tahoma"),
    ("Arial", "Arial"),
]

FONT_FILE_MAP = {
    "Vazirmatn": "Vazirmatn",
    "Parastoo": "Parastoo",
    "Tahoma": "TAHOMA",
    "Arial": "ARIAL",
}

DEFAULT_PERSIAN_FONT = "Vazirmatn"
DEFAULT_ENGLISH_FONT = "Arial"
PERSIAN_FONTS = ["Vazirmatn", "Parastoo", "Tahoma"]


# ==================================================================
# 📅 فرمت‌های تاریخ
# ==================================================================

DATE_FORMAT_CHOICES = [
    ("YYYY/MM/DD", "سال/ماه/روز"),
    ("YYYY-MM-DD", "سال-ماه-روز"),
    ("DD/MM/YYYY", "روز/ماه/سال"),
    ("DD-MM-YYYY", "روز-ماه-سال"),
    ("MM/DD/YYYY", "ماه/روز/سال"),
    ("MM-DD-YYYY", "ماه-روز-سال"),
]

DATE_SEPARATOR_CHOICES = [
    ("/", "اسلش (/)"),
    ("-", "خط تیره (-)"),
    (".", "نقطه (.)"),
    (" ", "فاصله"),
]


# ==================================================================
# 💊 تنظیمات پیش‌فرض نمایش دوا روی نسخه
# ==================================================================

DEFAULT_MEDICINE_OPTIONS = {
    # --- اینکه چه چیزی نمایش داده شود ---
    'show_number': True,           # شماره ردیف (۱. ۲. ۳.)
    'show_generic': True,          # نام جنریک
    'show_brand': False,           # نام تجارتی
    'show_manufacturer': False,    # شرکت سازنده
    'show_strength': True,         # قدرت (500mg)
    'show_dosage': True,           # دوز (۱ تابلت)
    'show_frequency': True,        # دفعات (روزی ۳ بار)
    'show_timing': True,           # زمان (بعد از غذا)
    'show_route': False,           # طریقه (خوراکی)
    'show_duration': True,         # مدت (۵ روز)

    # --- قالب‌بندی ---
    'show_border': True,           # خط دور هر دوا
    'border_color': '#cbd5e1',     # رنگ خط
    'border_width': 1,             # ضخامت خط
    'separator': ' - ',            # جداکننده بین مشخصات
    'layout': 'table',             # 'table' (کادر) یا 'list' (خطی)
    'row_padding': 8,              # فاصله داخلی
}


# ==================================================================
# ✅ توابع کمکی
# ==================================================================

def get_font_file_base(font_family):
    return FONT_FILE_MAP.get(font_family, font_family)


def is_persian_font(font_family):
    return font_family in PERSIAN_FONTS


def format_date_value(date_obj, date_format="YYYY/MM/DD", separator=None):
    if not date_obj:
        return ""
    try:
        from datetime import datetime, date
        if isinstance(date_obj, str):
            dt = datetime.strptime(date_obj, "%Y-%m-%d").date()
        elif isinstance(date_obj, datetime):
            dt = date_obj.date()
        elif isinstance(date_obj, date):
            dt = date_obj
        else:
            return str(date_obj)
    except Exception:
        return str(date_obj)

    y, m, d = dt.year, dt.month, dt.day
    fmt = date_format or "YYYY/MM/DD"
    result = (
        fmt.replace("YYYY", f"{y:04d}")
           .replace("MM", f"{m:02d}")
           .replace("DD", f"{d:02d}")
    )
    if separator:
        for sep in ["/", "-", "."]:
            result = result.replace(sep, separator)
    return result


def get_medicine_display_name(medication, display_mode="generic"):
    """
    Return the display name of a medication.
    `medication` should be a `medicine.Medication` instance.

    Note: `brand_name` was removed from the model — brand falls back
    to `name` (commercial name) when needed.
    """
    if not medication:
        return ""
    generic = (medication.generic_name or medication.name or "").strip()
    brand = (medication.name or "").strip()

    if display_mode == "brand":
        return brand or generic
    if display_mode == "both":
        if generic and brand and generic != brand:
            return f"{generic} ({brand})"
        return generic or brand
    return generic or brand


def get_default_medicine_options():
    """برگرداندن یک کپی از تنظیمات پیش‌فرض."""
    return dict(DEFAULT_MEDICINE_OPTIONS)