from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "مرد"
        FEMALE = "F", "زن"

    first_name = models.CharField(max_length=50, verbose_name="نام")
    last_name = models.CharField(max_length=50, verbose_name="تخلص")
    father_name = models.CharField(max_length=100, verbose_name="نام پدر")
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        verbose_name="جنسیت",
    )
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        verbose_name="سن",
    )
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        verbose_name="شماره تماس",
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="آدرس",
    )

    class Meta:
        verbose_name = "مریض"
        verbose_name_plural = "مریضان"
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"