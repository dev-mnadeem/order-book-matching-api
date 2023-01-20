"""Admin registrations."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from tradecore_api.models import Post, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for the e-mail-identified user model."""

    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "joined_on_holiday", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "joined_on_holiday")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("date_joined", "last_login", "geolocation_data")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Sign-up enrichment", {"fields": ("geolocation_data", "joined_on_holiday")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Admin for posts."""

    list_display = ("title", "author", "moderation_status", "created_at")
    list_filter = ("moderation_status", "created_at")
    search_fields = ("title", "description", "author__email")
    # Without this the changelist issues one extra query per row for the author.
    list_select_related = ("author",)
    raw_id_fields = ("author",)
    filter_horizontal = ("likes",)
