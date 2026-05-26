import uuid

from .tav_user import TavUser
from django.core.validators import RegexValidator
from django.db import models


class Account(models.Model):
    """
    Base Account class for all user accounts.
    """

    user = models.OneToOneField(
        TavUser, on_delete=models.CASCADE, related_name="account"
    )
    date_of_birth = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    mobile = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\d{11}$",
                message="Mobile number must be exactly 11 digits.",
            )
        ],
    )
    profile_picture = models.URLField(
        blank=True,
        null=True,
        default="https://i.imgur.co m/placeholder.png",
    )

    def __str__(self):
        return self.user.email

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = self.generate_unique_id()
        super().save(*args, **kwargs)
