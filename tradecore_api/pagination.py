"""Pagination for post listings."""

from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class PostPagination(PageNumberPagination):
    """Page-number pagination with a caller-settable, capped page size.

    The cap matters: without it ``?page_size=1000000`` is a cheap way to ask
    the database for every row the previous unbounded endpoint returned.
    """

    page_size_query_param = "page_size"

    @property
    def page_size(self):
        return settings.POST_PAGE_SIZE

    @property
    def max_page_size(self):
        return settings.POST_MAX_PAGE_SIZE
