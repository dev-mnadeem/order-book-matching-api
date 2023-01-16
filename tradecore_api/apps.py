"""App configuration."""

from django.apps import AppConfig


class TradecoreApiConfig(AppConfig):
    """The single application in this project."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tradecore_api"
    verbose_name = "TradeCore posts API"
