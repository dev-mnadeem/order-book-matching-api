"""Manager for the custom user model."""

from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """Creates users with a hashed password and a normalised e-mail."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create an ordinary account."""
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_staff", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create an account with full admin rights."""
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        if not extra_fields["is_superuser"] or not extra_fields["is_staff"]:
            raise ValueError("Superuser must have is_superuser=True and is_staff=True.")
        return self._create_user(email, password, **extra_fields)
