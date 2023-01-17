"""The custom user model: e-mail is the identity, plus sign-up enrichment."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from tradecore_api.models.managers.user_manager import UserManager

EMAIL_MAX_LENGTH = 254  # RFC 5321 limit on a full address
NAME_MAX_LENGTH = 30


class User(AbstractBaseUser, PermissionsMixin):
    """An account, identified by e-mail rather than a username.

    ``geolocation_data`` and ``joined_on_holiday`` are filled in at sign-up
    from the enrichment providers.  Both have defaults, because enrichment is
    best-effort: a provider being unavailable must not stop registration.
    """

    email = models.EmailField(max_length=EMAIL_MAX_LENGTH, unique=True, db_index=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    geolocation_data = models.JSONField(default=dict, blank=True)
    joined_on_holiday = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        # Normalising here rather than in the serializer keeps the uniqueness
        # guarantee true for the admin and shell as well as for the API.
        self.email = self.email.lower().strip()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.email})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
