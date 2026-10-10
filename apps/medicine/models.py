from django.db import models


class Medication(models.Model):
    """بانک دواها — یک بار برای همیشه"""

    class Form(models.TextChoices):
        TABLET      = "tablet",      "tablet"
        CAPSULE     = "capsule",     "capsule"
        SYRUP       = "syrup",       "syrup"
        SUSPENSION  = "suspension",  "suspension"
        INJECTION   = "injection",   "injection"
        DROPS       = "drops",       "drops"
        OINTMENT    = "ointment",    "ointment"
        CREAM       = "cream",       "cream"
        GEL         = "gel",         "gel"
        SPRAY       = "spray",       "spray"
        INHALER     = "inhaler",     "inhaler"
        SUPPOSITORY = "suppository", "suppository"
        POWDER      = "powder",      "powder"
        OTHER       = "other",       "other"

    class Unit(models.TextChoices):
        MG    = "mg",    "mg"
        G     = "g",     "g"
        ML    = "ml",    "ml"
        L     = "l",     "l"
        IU    = "IU",    "IU"
        MCG   = "mcg",   "mcg"
        DROP  = "drop",  "drop"
        PUFF  = "puff",  "puff"
        OTHER = "other", "other"

    # ═══ اطلاعات اصلی ═══
    name = models.CharField(max_length=200, verbose_name="نام دوا", db_index=True)
    generic_name = models.CharField(max_length=200, blank=True, verbose_name="نام جنریک", db_index=True)
    form = models.CharField(max_length=20, choices=Form.choices, default=Form.TABLET, verbose_name="شکل دوا")
    strength = models.CharField(max_length=50, blank=True, verbose_name="قدرت")
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.MG, blank=True, verbose_name="واحد")
    manufacturer = models.CharField(max_length=150, blank=True, verbose_name="شرکت سازنده")

    # ═══ پیش‌فرض‌های تجویز ═══
    default_dose = models.CharField(
        max_length=50, blank=True,
        verbose_name="Default Dose (دوز پیش‌فرض)",
        help_text="مثال: 1 Tablet, 2 Capsules, 5 ml"
    )
    default_frequency = models.CharField(
        max_length=50, blank=True,
        verbose_name="Default Frequency (دفعات پیش‌فرض)",
        help_text="مثال: 2x, 3x, q8h — یا متن دلخواه"
    )
    default_timing = models.CharField(
        max_length=50, blank=True,
        verbose_name="Default Timing (زمان مصرف پیش‌فرض)",
        help_text="مثال: after_meal, at_bedtime — یا متن دلخواه"
    )
    default_route = models.CharField(
        max_length=50, blank=True, default="oral",
        verbose_name="Default Route (طریقه مصرف پیش‌فرض)",
        help_text="مثال: oral, topical, injection — یا متن دلخواه"
    )
    default_duration = models.CharField(
        max_length=50, blank=True,
        verbose_name="Default Duration (مدت پیش‌فرض)",
        help_text="مثال: 3 Days, 7 Days, 1 Month"
    )

    # ═══ وضعیت ═══
    is_active = models.BooleanField(default=True, verbose_name="فعال است")
    is_favorite = models.BooleanField(default=False, verbose_name="دوا پرکاربرد")

    # ═══ زمان‌ها ═══
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "دوا"
        verbose_name_plural = "بانک دواها"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["generic_name"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_active", "is_favorite"]),
        ]

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        parts = [self.name]
        if self.strength:
            parts.append(f"{self.strength}{self.unit}")
        return " ".join(parts)