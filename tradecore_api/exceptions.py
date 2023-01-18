"""Domain exceptions and the API-wide error shape."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class PostRejected(APIException):
    """Raised when moderation refuses to publish a post."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Post rejected by moderation."
    default_code = "post_rejected"


def api_exception_handler(exc, context):
    """Give every error the same envelope: ``{"error": {...}}``.

    The handlers in this project previously each invented their own key
    ("message", "msg", "validation error"), which meant a client had to guess
    where the text was.  One shape is easier to consume and easier to test.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    code = getattr(exc, "default_code", "error")
    if isinstance(detail, dict) and set(detail.keys()) == {"detail"}:
        payload = {"code": code, "message": str(detail["detail"])}
    elif isinstance(detail, dict):
        payload = {"code": code, "message": "Validation failed.", "fields": detail}
    else:
        payload = {"code": code, "message": detail}

    response.data = {"error": payload}
    return response
