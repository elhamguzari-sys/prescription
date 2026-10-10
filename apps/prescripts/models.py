from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# ==================================================================
# 🎨 مدل ۱: PrescriptionTemplate (دیزاین نسخه)
# ==================================================================

class PrescriptionTemplate(models.Model):
    """دیزاین نسخه — عکس پس‌زمینه + فیلدها"""

    name = models.CharField(max_length=100, verbose_name="نام دیزاین")
    description = models.TextField(blank=True, verbose_name="توضیحات")

    background_image = models.ImageField(
        upload_to="templates/prescriptions/%Y/%m/",
        verbose_name="عکس پس‌زمینه",
    )

    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال است")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دیزاین نسخه"
        verbose_name_plural = "دیزاین‌های نسخه"
        ordering = ["-is_default", "-updated_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            PrescriptionTemplate.objects.filter(
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def image_width(self):
        if self.background_image:
            try:
                from PIL import Image
                with Image.open(self.background_image.path) as img:
                    return img.width
            except Exception:
                pass
        return 1748

    @property
    def image_height(self):
        if self.background_image:
            try:
                from PIL import Image
                with Image.open(self.background_image.path) as img:
                    return img.height
            except Exception:
                pass
        return 2480

    @property
    def canvas_width(self):
        return self.image_width

    @property
    def canvas_height(self):
        return self.image_height


# ==================================================================
# 🧩 مدل ۲: TemplateField (فیلدهای دیزاین)
# ==================================================================

class TemplateField(models.Model):
    """فیلد مقداری روی دیزاین نسخه — دقیقاً مطابق ساختار Prescription"""

    class FieldType(models.TextChoices):
        # ─── Patient ───
        PATIENT_NAME      = "patient_name",     "نام مریض"
        PATIENT_FATHER    = "patient_father",   "نام پدر"
        PATIENT_AGE       = "patient_age",      "سن"
        PATIENT_GENDER    = "patient_gender",   "جنسیت"
        PATIENT_PHONE     = "patient_phone",    "شماره تماس"
        PATIENT_ADDRESS   = "patient_address",  "آدرس"
        PATIENT_FILE      = "patient_file",     "شماره پرونده"

        # ─── Vitals ───
        VITAL_BP          = "vital_bp",         "فشار خون"
        VITAL_PR          = "vital_pr",         "نبض"
        VITAL_RR          = "vital_rr",         "تنفس"
        VITAL_TEMP        = "vital_temp",       "دما"
        VITAL_SPO2        = "vital_spo2",       "اکسیژن SpO₂"
        VITAL_WEIGHT      = "vital_weight",     "وزن"
        VITAL_HEIGHT      = "vital_height",     "قد"
        VITAL_BMI         = "vital_bmi",        "BMI"

        # ─── Clinical ───
        SIGNS_SYMPTOMS    = "signs_symptoms",   "علائم و نشانه‌ها"
        DIAGNOSIS         = "diagnosis",        "تشخیص"
        IMPRESSION        = "impression",       "برداشت بالینی"
        DOCTOR_NOTE       = "doctor_note",      "یادداشت داکتر"

        # ─── Advice ───
        ADVICE            = "advice",           "توصیه‌ها"

        # ─── Meds ───
        MEDICATIONS_LIST  = "medications_list", "لیست دواها"

        # ─── Meta ───
        PRESCRIPTION_NUM  = "prescription_number", "شماره نسخه"
        PRESCRIPTION_DATE = "prescription_date",   "تاریخ نسخه"

    template = models.ForeignKey(
        PrescriptionTemplate, on_delete=models.CASCADE,
        related_name="fields", verbose_name="دیزاین",
    )
    field_type = models.CharField(max_length=50, choices=FieldType.choices, verbose_name="نوع فیلد")
    label = models.CharField(max_length=100, blank=True, verbose_name="برچسب")

    x = models.IntegerField(default=100, verbose_name="X")
    y = models.IntegerField(default=100, verbose_name="Y")
    width = models.IntegerField(default=300, verbose_name="عرض")
    height = models.IntegerField(default=0, verbose_name="ارتفاع")

    padding = models.PositiveIntegerField(default=0, verbose_name="فاصله داخلی")
    line_height = models.FloatField(default=1.4, verbose_name="فاصله خطوط")

    font_family = models.CharField(max_length=50, default="Vazirmatn", verbose_name="فونت")
    font_size = models.PositiveIntegerField(default=14, verbose_name="اندازه فونت")
    font_weight = models.CharField(
        max_length=10,
        choices=[("normal", "معمولی"), ("bold", "ضخیم")],
        default="normal", verbose_name="ضخامت",
    )
    color = models.CharField(max_length=20, default="#0f172a", verbose_name="رنگ")
    text_align = models.CharField(
        max_length=10,
        choices=[("right", "راست"), ("center", "وسط"), ("left", "چپ")],
        default="right", verbose_name="چینش",
    )

    has_shadow = models.BooleanField(default=False, verbose_name="سایه متن")
    shadow_color = models.CharField(max_length=20, default="#000000", verbose_name="رنگ سایه")
    has_stroke = models.BooleanField(default=False, verbose_name="خط دور متن")
    stroke_color = models.CharField(max_length=20, default="#ffffff", verbose_name="رنگ خط")
    stroke_width = models.PositiveIntegerField(default=1, verbose_name="ضخامت خط")

    date_format = models.CharField(max_length=20, default="YYYY/MM/DD", verbose_name="فرمت تاریخ")
    date_separator = models.CharField(max_length=3, default="/", verbose_name="جداکننده")

    medicine_options = models.JSONField(default=dict, blank=True, verbose_name="تنظیمات دوا")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "فیلد دیزاین"
        verbose_name_plural = "فیلدهای دیزاین"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.template.name} — {self.get_field_type_display()}"

    @property
    def display_label(self):
        return self.label or self.get_field_type_display()

    @property
    def is_wrap_field(self):
        return self.field_type in [
            "signs_symptoms", "diagnosis", "impression", "doctor_note", "advice",
        ]

    @property
    def is_date_field(self):
        return self.field_type == "prescription_date"

    @property
    def is_medicine_field(self):
        return self.field_type == "medications_list"


# ==================================================================
# 📝 مدل ۳: Prescription (نسخه)
# ==================================================================

class Prescription(models.Model):
    """نسخه — شامل همه اطلاعات بالینی، دواها و دیزاین"""

    # ─── Relations ───
    patient = models.ForeignKey(
        "patient.Patient", on_delete=models.PROTECT,
        related_name="prescriptions", verbose_name="مریض",
    )
    template = models.ForeignKey(
        PrescriptionTemplate, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="prescriptions", verbose_name="دیزاین نسخه",
    )

    # ─── Identity ───
    prescription_number = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="شماره نسخه"
    )
    prescription_date = models.DateField(
        default=timezone.localdate, verbose_name="تاریخ نسخه"
    )

    # ─── Clinical ───
    signs_symptoms = models.TextField(blank=True, verbose_name="علائم و نشانه‌ها")
    diagnosis = models.CharField(max_length=500, blank=True, verbose_name="تشخیص")
    impression = models.TextField(blank=True, verbose_name="برداشت بالینی")
    doctor_note = models.TextField(blank=True, verbose_name="یادداشت داکتر")

    # ─── Vital Signs ───
    blood_pressure = models.CharField(max_length=20, blank=True, verbose_name="فشار خون (mmHg)")
    pulse = models.PositiveIntegerField(null=True, blank=True, verbose_name="نبض (bpm)")
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1,
        null=True, blank=True, verbose_name="دما (°C)",
    )
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True, verbose_name="تنفس (/min)")
    spo2 = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="SpO₂ (%)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    weight = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="وزن (kg)",
    )
    height = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="قد (cm)",
    )

    # ─── Advice ───
    advice_items = models.JSONField(default=list, blank=True, verbose_name="توصیه‌ها")

    # ─── Image ───
    edited_image = models.ImageField(
        upload_to="prescriptions/edited/%Y/%m/",
        blank=True, null=True, verbose_name="عکس نسخه",
    )
    is_image_edited = models.BooleanField(default=False, verbose_name="عکس تولید شده")

    # ─── Meta ───
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_prescriptions", verbose_name="ثبت‌کننده",
    )

    class Meta:
        verbose_name = "نسخه"
        verbose_name_plural = "نسخه‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["prescription_date"]),
            models.Index(fields=["patient", "prescription_date"]),
        ]

    def __str__(self):
        return f"{self.prescription_number} — {self.patient.full_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.prescription_number:
            year = timezone.now().year
            self.prescription_number = f"P-{year}-{self.pk:05d}"
            super().save(update_fields=["prescription_number"])

    # ─── Properties ───
    @property
    def patient_name(self):
        return self.patient.full_name

    @property
    def patient_father_name(self):
        return self.patient.father_name or ""

    @property
    def patient_age(self):
        return self.patient.age

    @property
    def patient_gender(self):
        if hasattr(self.patient, "get_gender_display"):
            return self.patient.get_gender_display()
        return self.patient.gender or ""

    @property
    def patient_phone(self):
        return self.patient.phone or ""

    @property
    def patient_address(self):
        return self.patient.address or ""

    @property
    def bmi(self):
        if self.weight and self.height:
            h = float(self.height) / 100
            return round(float(self.weight) / (h * h), 1)
        return None

    @property
    def bmi_category(self):
        bmi = self.bmi
        if not bmi:
            return ""
        if bmi < 18.5:
            return "کمبود وزن"
        elif bmi < 25:
            return "نرمال"
        elif bmi < 30:
            return "اضافه وزن"
        else:
            return "چاقی"

    @property
    def items_count(self):
        return self.items.count()

    # ==============================================================
    # 🎨 Generate image
    # ==============================================================
    def generate_image(self, user=None):
        """Generate the prescription image from the template."""
        if not self.template:
            raise ValueError("دیزاین نسخه انتخاب نشده است.")

        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        from django.core.files.base import ContentFile
        import os
        import re

        bg_img = Image.open(self.template.background_image.path)
        SCALE = 1.0

        def px(v):
            return int(v * SCALE)

        def reshape(text):
            if not text:
                return ""
            text = str(text)
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                return get_display(arabic_reshaper.reshape(text))
            except Exception:
                return text

        def has_persian(text):
            if not text:
                return False
            return bool(re.search(
                r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]',
                str(text)
            ))

        def get_font(font_name, size, weight="normal"):
            font_dirs = [
                os.path.join(settings.BASE_DIR, "static", "fonts"),
                os.path.join(settings.BASE_DIR, "fonts"),
            ]
            file_base = font_name.replace(" ", "")

            if weight == "bold":
                candidates = [
                    f"{file_base}-Bold.ttf",
                    f"{file_base}-bold.ttf",
                    f"{file_base}Bold.ttf",
                    f"{file_base}.ttf",
                ]
            else:
                candidates = [
                    f"{file_base}-Regular.ttf",
                    f"{file_base}.ttf",
                ]
            candidates.extend(["Vazirmatn-Regular.ttf", "Vazirmatn.ttf", "arial.ttf"])

            for d in font_dirs:
                for c in candidates:
                    path = os.path.join(d, c)
                    if os.path.exists(path):
                        try:
                            return ImageFont.truetype(path, size)
                        except Exception:
                            continue

            try:
                return ImageFont.load_default()
            except Exception:
                return None

        def draw_text(draw, text, x, y, font, fill):
            if has_persian(text):
                text = reshape(text)
            draw.text((x, y), text, font=font, fill=fill)

        def measure_text(draw, text, font):
            if has_persian(text):
                text = reshape(text)
            try:
                bb = draw.textbbox((0, 0), text, font=font)
                return bb[2] - bb[0], bb[3] - bb[1]
            except Exception:
                return len(text) * 8, 14

        def truncate_to_width(draw, text, font, max_w, ellipsis="…"):
            if not text:
                return ""
            original = str(text)
            w, _ = measure_text(draw, original, font)
            if w <= max_w:
                return original
            for cut in range(len(original) - 1, 0, -1):
                test_str = original[:cut] + ellipsis
                w, _ = measure_text(draw, test_str, font)
                if w <= max_w:
                    return test_str
            return ellipsis

        def wrap_text_to_width(draw, text, font, max_w):
            if not text:
                return []
            words = str(text).split()
            if not words:
                return []
            lines = []
            current = ""
            for w in words:
                test = (current + " " + w).strip() if current else w
                tw, _ = measure_text(draw, test, font)
                if tw <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = w
            if current:
                lines.append(current)
            return lines

        def wrap_specs_to_width(draw, specs, font, max_w, gap):
            lines = []
            current_line = []
            current_w = 0
            pill_pad_x_local = int(getattr(font, 'size', 12) * 0.55)
            for spec in specs:
                sw, _ = measure_text(draw, spec, font)
                pill_w = sw + pill_pad_x_local * 2
                needed = pill_w if not current_line else current_w + gap + pill_w
                if needed <= max_w:
                    current_line.append(spec)
                    current_w = needed
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [spec]
                    current_w = pill_w
            if current_line:
                lines.append(current_line)
            return lines

        def draw_justified_line(draw, text, font, color, x_left, x_right, y, is_rtl=True):
            if not text:
                return
            words = text.split()
            if len(words) <= 1:
                draw_text(draw, text, x_left, y, font, color)
                return

            word_widths = []
            for w in words:
                ww, _ = measure_text(draw, w, font)
                word_widths.append(ww)

            total_words_w = sum(word_widths)
            total_gap_space = (x_right - x_left) - total_words_w
            gap_per = total_gap_space / (len(words) - 1) if len(words) > 1 else 0

            if gap_per < 2:
                gap_per = 2

            if is_rtl:
                cursor_x = x_right
                for i, w in enumerate(words):
                    ww = word_widths[i]
                    draw_text(draw, w, cursor_x - ww, y, font, color)
                    cursor_x -= (ww + gap_per)
            else:
                cursor_x = x_left
                for i, w in enumerate(words):
                    ww = word_widths[i]
                    draw_text(draw, w, cursor_x, y, font, color)
                    cursor_x += (ww + gap_per)

        img = bg_img.convert("RGB")
        draw = ImageDraw.Draw(img)

        for field in self.template.fields.all().order_by("order", "id"):
            try:
                value = self._get_field_value(field.field_type)
            except Exception as e:
                print(f"⚠️ Field {field.field_type} value error: {e}")
                continue

            if not value:
                continue

            try:
                real_x = px(field.x) + field.padding
                real_y = px(field.y) + field.padding
                real_width = px(field.width) - (field.padding * 2)
                if real_width < 20:
                    real_width = px(field.width) if field.width else 600

                real_font_size = max(8, px(field.font_size))

                # ═══════════════════════════════════════════════════
                # MEDICINES
                # ═══════════════════════════════════════════════════
                if field.field_type == "medications_list":
                    rows = value
                    opts = field.medicine_options or {}

                    name_font = get_font(field.font_family, real_font_size, "bold")
                    str_font  = get_font(field.font_family, real_font_size, "normal")
                    meta_font = get_font(
                        field.font_family,
                        max(8, int(real_font_size * 0.85)),
                        "normal",
                    )
                    spec_font = get_font(
                        field.font_family,
                        max(7, int(real_font_size * 0.78)),
                        "bold",
                    )
                    # ⭐ Quantity badge font — bold + slightly bigger
                    qty_font = get_font(
                        field.font_family,
                        max(8, int(real_font_size * 0.9)),
                        "bold",
                    )

                    COLOR_ACCENT = "#dc2626"
                    COLOR_NAME   = field.color
                    COLOR_STR    = "#334155"
                    COLOR_META   = "#334155"
                    COLOR_QTY    = "#dc2626"       # ⭐ quantity color

                    QTY_BG  = "#fee2e2"
                    QTY_BD  = "#dc2626"
                    QTY_TXT = "#991b1b"

                    PILL_BG  = "#fef2f2"
                    PILL_BD  = "#dc2626"
                    PILL_TXT = "#991b1b"

                    CARD_BG = "#ffffff"
                    CARD_BD = "#e5e7eb"

                    card_pad_x    = int(real_font_size * 1)
                    card_pad_y    = int(real_font_size * 0.9)
                    gap_name_meta = int(real_font_size * 0.7)
                    gap_meta_spec = int(real_font_size * 0.8)
                    gap_cards     = 0
                    pill_pad_x    = int(real_font_size * 0.55)
                    pill_pad_y    = int(real_font_size * 0.28)
                    pill_gap      = int(real_font_size * 0.4)

                    row_y = real_y
                    card_w = real_width if real_width > 100 else 500
                    card_inner_w = card_w - (card_pad_x * 2)

                    for med in rows:
                        primary_name = ''
                        if opts.get('show_generic') and med.get('generic'):
                            primary_name = med['generic']
                        elif med.get('name'):
                            primary_name = med['name']
                        elif med.get('brand'):
                            primary_name = med['brand']

                        strength_str = med.get('strength', '') if opts.get('show_strength') else ''
                        brand_str = ''
                        if opts.get('show_brand') and med.get('brand') and med['brand'] != primary_name:
                            brand_str = f"({med['brand']})"
                        mfr_str = med.get('manufacturer', '') if opts.get('show_manufacturer') else ''

                        # ⭐ Quantity badge text: "n=2"
                        quantity_val = med.get('quantity') or ''
                        qty_text = f"n={quantity_val}" if (opts.get('show_quantity', True) and quantity_val) else ''
                        qty_w = 0
                        qty_h = 0
                        if qty_text:
                            qty_w, qty_h = measure_text(draw, qty_text, qty_font)

                        specs = []
                        if opts.get('show_dosage') and med.get('dosage'):
                            specs.append(med['dosage'])
                        if opts.get('show_frequency') and med.get('frequency'):
                            specs.append(med['frequency'])
                        if opts.get('show_timing') and med.get('timing'):
                            specs.append(med['timing'])
                        if opts.get('show_route') and med.get('route'):
                            specs.append(med['route'])
                        if opts.get('show_duration') and med.get('duration'):
                            specs.append(med['duration'])

                        num_text = f"{med['number']}.  "
                        num_w, _ = measure_text(draw, num_text, name_font)

                        # ⭐ Reserve space on the right side for the quantity badge
                        # (RTL layout: quantity sits at the right edge of the card)
                        qty_reserved = (qty_w + 24) if qty_text else 0

                        available_for_name = max(
                            60,
                            card_inner_w - num_w - qty_reserved - 20
                        )

                        first_line_text = primary_name
                        if strength_str:
                            first_line_text = (first_line_text + "  " + strength_str).strip()

                        name_lines = wrap_text_to_width(
                            draw, first_line_text, name_font, available_for_name
                        )
                        if not name_lines:
                            name_lines = [""]

                        _, name_h = measure_text(draw, "Ag", name_font)
                        name_h = max(name_h, real_font_size)

                        # ⭐ Badge height — at least as tall as the name line
                        qty_badge_h = max(name_h + 6, qty_h + 8) if qty_text else 0

                        meta_parts = []
                        if (opts.get('show_generic') and med.get('generic')
                                and med['generic'] != primary_name):
                            meta_parts.append(med['generic'])
                        if mfr_str:
                            meta_parts.append(mfr_str)
                        if brand_str:
                            meta_parts.append(brand_str)

                        meta_text = "  •  ".join(meta_parts)
                        meta_lines = []
                        if meta_text:
                            meta_lines = wrap_text_to_width(
                                draw, meta_text, meta_font, card_inner_w
                            )

                        _, meta_h = measure_text(draw, "Ag", meta_font)
                        meta_h = max(meta_h, int(real_font_size * 0.8))

                        pill_lines = []
                        if specs:
                            pill_lines = wrap_specs_to_width(
                                draw, specs, spec_font, card_inner_w, pill_gap
                            )

                        pill_line_h = int(real_font_size * 1.15) if pill_lines else 0

                        card_h = card_pad_y * 2
                        card_h += max(name_h * len(name_lines), qty_badge_h)
                        if meta_lines:
                            card_h += gap_name_meta + (meta_h * len(meta_lines))
                        if pill_lines:
                            card_h += gap_meta_spec
                            card_h += pill_line_h * len(pill_lines)
                            card_h += gap_meta_spec * (len(pill_lines) - 1)

                        card_l = real_x
                        card_r = real_x + card_w
                        card_t = row_y
                        card_b = card_t + card_h

                        try:
                            draw.rounded_rectangle(
                                [card_l, card_t, card_r, card_b],
                                radius=int(real_font_size * 0.55),
                                outline=CARD_BD, width=2, fill=CARD_BG,
                            )
                        except Exception:
                            draw.rectangle(
                                [card_l, card_t, card_r, card_b],
                                outline=CARD_BD, width=2, fill=CARD_BG,
                            )

                        inner_x = card_l + card_pad_x
                        cursor_y = card_t + card_pad_y

                        # ── Draw name line(s) — skip the right side if quantity present ──
                        for li, line_text in enumerate(name_lines):
                            x_cursor = inner_x
                            if li == 0:
                                draw_text(draw, num_text, x_cursor,
                                          cursor_y, name_font, COLOR_ACCENT)
                                x_cursor += num_w

                            if line_text:
                                if strength_str and li == len(name_lines) - 1 and strength_str in line_text:
                                    idx = line_text.rfind("  ")
                                    if idx > 0:
                                        name_part = line_text[:idx]
                                        str_part = line_text[idx:].strip()
                                        if name_part:
                                            draw_text(draw, name_part, x_cursor,
                                                      cursor_y, name_font, COLOR_NAME)
                                            nw, _ = measure_text(draw, name_part + "  ", name_font)
                                            x_cursor += nw
                                        if str_part:
                                            draw_text(draw, str_part, x_cursor,
                                                      cursor_y, str_font, COLOR_STR)
                                    else:
                                        draw_text(draw, line_text, x_cursor,
                                                  cursor_y, name_font, COLOR_NAME)
                                else:
                                    draw_text(draw, line_text, x_cursor,
                                              cursor_y, name_font, COLOR_NAME)

                            cursor_y += name_h

                        # ⭐ Draw quantity badge at the RIGHT edge of the first line
                                                # ⭐ Draw quantity badge at the RIGHT edge of the first line
                        if qty_text:
                            # ── Bigger font for the badge number ──
                            badge_font = get_font(
                                field.font_family,
                                max(10, int(real_font_size * 1.05)),
                                "bold",
                            )

                            # ── Measure with the badge font ──
                            qty_w, qty_h = measure_text(draw, qty_text, badge_font)

                            # ── Generous padding ──
                            badge_pad_x = int(real_font_size * 0.75)
                            badge_pad_y = int(real_font_size * 0.50)

                            badge_w = qty_w + badge_pad_x * 2
                            badge_h = max(qty_h + badge_pad_y * 2, int(real_font_size * 1.8))

                            # ── Position: top-right corner, aligned with first name line ──
                            badge_x_right = card_r - card_pad_x
                            badge_x_left = badge_x_right - badge_w

                            # Align the badge's vertical center with the name line's center
                            name_center_y = card_t + card_pad_y + (name_h // 2)
                            badge_y_top = name_center_y - (badge_h // 2)

                            # ── Draw the badge (rounded pill) ──
                            try:
                                draw.rounded_rectangle(
                                    [badge_x_left, badge_y_top,
                                     badge_x_right, badge_y_top + badge_h],
                                    radius=int(badge_h * 0.5),
                                    fill=QTY_BG, outline=QTY_BD, width=2,
                                )
                            except Exception:
                                draw.rectangle(
                                    [badge_x_left, badge_y_top,
                                     badge_x_right, badge_y_top + badge_h],
                                    fill=QTY_BG, outline=QTY_BD, width=2,
                                )

                            # ── Center the text inside the badge ──
                            # textbbox gives us (left, top, right, bottom)
                            try:
                                tb = draw.textbbox((0, 0), qty_text, font=badge_font)
                                text_w = tb[2] - tb[0]
                                text_h = tb[3] - tb[1]
                                text_offset_x = tb[0]
                                text_offset_y = tb[1]
                            except Exception:
                                text_w = qty_w
                                text_h = qty_h
                                text_offset_x = 0
                                text_offset_y = 0

                            text_x = badge_x_left + (badge_w - text_w) // 2 - text_offset_x
                            text_y = badge_y_top + (badge_h - text_h) // 2 - text_offset_y

                            draw_text(draw, qty_text, text_x, text_y, badge_font, QTY_TXT)

                        if meta_lines:
                            cursor_y += gap_name_meta
                            for mline in meta_lines:
                                draw_text(draw, mline, inner_x,
                                          cursor_y, meta_font, COLOR_META)
                                cursor_y += meta_h

                        if pill_lines:
                            cursor_y += gap_meta_spec
                            for line_specs in pill_lines:
                                pill_x = inner_x
                                for spec in line_specs:
                                    spec_w, spec_h = measure_text(draw, spec, spec_font)
                                    pill_w = spec_w + pill_pad_x * 2
                                    pill_h = spec_h + pill_pad_y * 2

                                    try:
                                        draw.rounded_rectangle(
                                            [pill_x, cursor_y, pill_x + pill_w, cursor_y + pill_h],
                                            radius=int(pill_h * 0.5),
                                            fill=PILL_BG, outline=PILL_BD, width=1,
                                        )
                                    except Exception:
                                        draw.rectangle(
                                            [pill_x, cursor_y, pill_x + pill_w, cursor_y + pill_h],
                                            fill=PILL_BG, outline=PILL_BD, width=1,
                                        )

                                    text_x = pill_x + pill_pad_x
                                    text_y = cursor_y + pill_pad_y - int(real_font_size * 0.02)
                                    draw_text(draw, spec, text_x, text_y, spec_font, PILL_TXT)

                                    pill_x += pill_w + pill_gap
                                cursor_y += pill_line_h + gap_meta_spec

                        row_y = card_b + gap_cards

                    continue

                # ═══════════════════════════════════════════════════
                # NORMAL FIELDS
                # ═══════════════════════════════════════════════════
                font = get_font(field.font_family, real_font_size, field.font_weight)
                line_height = int(real_font_size * (field.line_height or 1.4))

                if field.is_wrap_field or "\n" in str(value):
                    paragraphs = str(value).split("\n")
                    current_y = real_y
                    is_rtl = has_persian(str(value))

                    for para in paragraphs:
                        wrapped = wrap_text_to_width(draw, para, font, real_width)
                        if not wrapped:
                            current_y += line_height
                            continue
                        for li, line in enumerate(wrapped):
                            is_last_line = (li == len(wrapped) - 1)
                            if (not is_last_line) and (" " in line):
                                draw_justified_line(
                                    draw, line, font, field.color,
                                    real_x, real_x + real_width,
                                    current_y, is_rtl=is_rtl,
                                )
                            else:
                                if is_rtl:
                                    lw, _ = measure_text(draw, line, font)
                                    draw_text(draw, line,
                                              real_x + real_width - lw,
                                              current_y, font, field.color)
                                else:
                                    draw_text(draw, line, real_x,
                                              current_y, font, field.color)
                            current_y += line_height
                else:
                    text_to_draw = str(value)
                    w, _ = measure_text(draw, text_to_draw, font)
                    if w > real_width:
                        text_to_draw = truncate_to_width(draw, text_to_draw, font, real_width)
                    draw_text(draw, text_to_draw, real_x, real_y, font, field.color)

            except Exception as e:
                print(f"⚠️ Field {field.field_type} draw error: {e}")
                continue

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95, optimize=True)

        if self.edited_image:
            try:
                self.edited_image.delete(save=False)
            except Exception:
                pass

        filename = f"rx_{self.prescription_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        self.edited_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        self.is_image_edited = True
        self.save(update_fields=["edited_image", "is_image_edited", "updated_at"])

        return self.edited_image

    # ==============================================================
    # 🔍 Field value extractor
    # ==============================================================
    def _get_field_value(self, field_type):
        if field_type == "medications_list":
            rows = []
            for i, item in enumerate(self.items.all().order_by("order", "id"), 1):
                rows.append({
                    'number': i,
                    'generic': (item.medication.generic_name if item.medication else '') or '',
                    'strength': item.drug_strength or '',
                    'name': item.medication.name if item.medication else '',
                    'brand': item.medication.name if item.medication else '',
                    'manufacturer': (item.medication.manufacturer if item.medication else '') or '',
                    'dosage': item.dose or '',
                    'frequency': item.frequency or '',
                    'timing': item.timing or '',
                    'route': item.route or '',
                    'duration': item.duration or '',
                    # ⭐ NEW — quantity
                    'quantity': item.quantity if item.quantity else '',
                })
            return rows

        def g(obj, attr, default=""):
            v = getattr(obj, attr, None)
            return v if v not in (None, "") else default

        if field_type == "patient_name":
            return g(self.patient, "full_name") if self.patient else ""
        if field_type == "patient_father":
            return g(self.patient, "father_name") if self.patient else ""
        if field_type == "patient_age":
            return str(g(self.patient, "age")) if self.patient else ""
        if field_type == "patient_gender":
            if self.patient and hasattr(self.patient, "get_gender_display"):
                return self.patient.get_gender_display() or ""
            return g(self.patient, "gender") if self.patient else ""
        if field_type == "patient_phone":
            return g(self.patient, "phone") if self.patient else ""
        if field_type == "patient_address":
            return g(self.patient, "address") if self.patient else ""
        if field_type == "patient_file":
            return g(self.patient, "file_number") if self.patient else ""

        if field_type == "vital_bp":
            return g(self, "blood_pressure")
        if field_type == "vital_pr":
            p = g(self, "pulse")
            return str(p) if p else ""
        if field_type == "vital_rr":
            rr = g(self, "respiratory_rate")
            return str(rr) if rr else ""
        if field_type == "vital_temp":
            t = g(self, "temperature")
            return str(t) if t else ""
        if field_type == "vital_spo2":
            s = g(self, "spo2")
            return f"{s}%" if s else ""

        if field_type == "vital_weight":
            w = g(self, "weight")
            return str(w) if w else ""

        if field_type == "vital_height":
            h = g(self, "height")
            return str(h) if h else ""

        if field_type == "vital_bmi":
            bmi = self.bmi
            return str(bmi) if bmi else ""

        if field_type == "signs_symptoms":
            return g(self, "signs_symptoms")
        if field_type == "diagnosis":
            return g(self, "diagnosis")
        if field_type == "impression":
            return g(self, "impression")
        if field_type == "doctor_note":
            return g(self, "doctor_note")

        if field_type == "advice":
            return "\n".join(self.advice_items or [])

        if field_type == "prescription_number":
            return self.prescription_number or ""
        if field_type == "prescription_date":
            return str(self.prescription_date) if self.prescription_date else ""

        return ""


# ==================================================================
# 💊 مدل ۴: PrescriptionItem (دواهای نسخه)
# ==================================================================

class PrescriptionItem(models.Model):
    """داروهای نسخه — medication از اپ medicine"""

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE,
        related_name="items", verbose_name="نسخه",
    )
    medication = models.ForeignKey(
        "medicine.Medication", on_delete=models.PROTECT,
        related_name="prescription_items", verbose_name="دارو",
        null=True, blank=True,
    )

    class Frequency(models.TextChoices):
        ONCE_DAILY   = "1x",   "روزی ۱ بار"
        TWICE_DAILY  = "2x",   "روزی ۲ بار"
        THREE_TIMES  = "3x",   "روزی ۳ بار"
        FOUR_TIMES   = "4x",   "روزی ۴ بار"
        EVERY_6H     = "q6h",  "هر ۶ ساعت"
        EVERY_8H     = "q8h",  "هر ۸ ساعت"
        EVERY_12H    = "q12h", "هر ۱۲ ساعت"
        AS_NEEDED    = "prn",  "در صورت نیاز"
        STAT         = "stat", "فوری"
        OTHER        = "other","دیگر"

    class Timing(models.TextChoices):
        BEFORE_MEAL   = "before_meal",   "قبل از غذا"
        AFTER_MEAL    = "after_meal",    "بعد از غذا"
        WITH_MEAL     = "with_meal",     "همراه با غذا"
        EMPTY_STOMACH = "empty_stomach", "با معده خالی"
        AT_BEDTIME    = "at_bedtime",    "قبل از خواب"
        MORNING       = "morning",       "صبح"
        EVENING       = "evening",       "شب"
        ANY_TIME      = "any_time",      "هر زمان"
        OTHER         = "other",         "دیگر"

    class Route(models.TextChoices):
        ORAL       = "oral",       "خوراکی"
        TOPICAL    = "topical",    "موضعی"
        INJECTION  = "injection",  "تزریقی"
        INHALATION = "inhalation", "استنشاقی"
        RECTAL     = "rectal",     "مقعذی"
        EYE        = "eye",        "چشمی"
        EAR        = "ear",        "گوشی"
        NASAL      = "nasal",      "بینی"
        OTHER      = "other",      "دیگر"

    dose = models.CharField(max_length=50, blank=True, verbose_name="دوز")
    frequency = models.CharField(max_length=10, blank=True, choices=Frequency.choices, verbose_name="دفعات")
    timing = models.CharField(max_length=20, blank=True, choices=Timing.choices, verbose_name="زمان مصرف")
    route = models.CharField(max_length=15, blank=True, choices=Route.choices, default=Route.ORAL, verbose_name="طریقه مصرف")
    duration = models.CharField(max_length=50, blank=True, verbose_name="مدت")

    # ⭐ NEW — quantity (n=X)
    quantity = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="تعداد",
        help_text="تعداد کل از این دوا در این نسخه (مثلاً 2، 3، 21)"
    )

    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دارو در نسخه"
        verbose_name_plural = "داروهای نسخه"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.drug_name} — {self.prescription.prescription_number}"

    @property
    def drug_name(self):
        if self.medication:
            return self.medication.full_name
        return ""

    @property
    def drug_strength(self):
        if self.medication:
            return f"{self.medication.strength}{self.medication.unit}"
        return ""

    @property
    def drug_form(self):
        if self.medication:
            return self.medication.get_form_display()
        return ""

    @property
    def drug_generic_name(self):
        if self.medication:
            return self.medication.generic_name
        return ""

    # ⭐ NEW — display helpers
    @property
    def quantity_display(self):
        """Return 'n=X' string for display, or '' if no quantity."""
        if self.quantity:
            return f"n={self.quantity}"
        return ""


# ==================================================================
# 📋 مدل ۵: ReadyPrescription (نسخه آماده)
# ==================================================================

class ReadyPrescription(models.Model):
    """نسخه آماده — فقط خلاصه بیماری + دواها"""

    title = models.CharField(max_length=200, verbose_name="عنوان", db_index=True)

    signs_symptoms = models.TextField(blank=True, verbose_name="علائم و نشانه‌ها")
    diagnosis = models.CharField(max_length=500, blank=True, verbose_name="تشخیص")
    impression = models.TextField(blank=True, verbose_name="برداشت بالینی")
    doctor_note = models.TextField(blank=True, verbose_name="یادداشت داکتر")

    advice = models.TextField(blank=True, verbose_name="توصیه‌ها")

    medications = models.JSONField(default=list, blank=True, verbose_name="لیست دواها")

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_favorite = models.BooleanField(default=False, verbose_name="پرکاربرد")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نسخه آماده"
        verbose_name_plural = "نسخه‌های آماده"
        ordering = ["-is_favorite", "title"]

    def __str__(self):
        return self.title

    @property
    def medications_count(self):
        return len(self.medications or [])