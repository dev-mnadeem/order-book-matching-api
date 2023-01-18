"""Serializers for accounts."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from tradecore_api.models import User


class UserSerializer(serializers.ModelSerializer):
    """The public view of an account.

    ``geolocation_data`` is deliberately absent: it is derived from the
    caller's IP at sign-up and is nobody else's business.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "full_name", "date_joined")
        read_only_fields = fields


class PrivateUserSerializer(UserSerializer):
    """The account's own view of itself, including its enrichment."""

    class Meta(UserSerializer.Meta):
        fields = (*UserSerializer.Meta.fields, "geolocation_data", "joined_on_holiday")
        read_only_fields = fields


class SignUpSerializer(serializers.ModelSerializer):
    """Validates a registration request."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def validate_email(self, value: str) -> str:
        normalised = value.lower().strip()
        if User.objects.filter(email=normalised).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalised

    def validate_password(self, value: str) -> str:
        # Run Django's configured validators here so a weak password comes back
        # as a normal 400 field error rather than an exception in the view.
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class LoginSerializer(serializers.Serializer):
    """Validates the shape of a login request."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_email(self, value: str) -> str:
        # Addresses are stored lower-cased, and the auth backend looks the
        # value up exactly, so "Alice@Example.com" must be folded here or the
        # owner of that address cannot log in.
        return value.lower().strip()
