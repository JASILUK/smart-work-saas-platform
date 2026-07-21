"""
Enterprise Standers Pagination Matrix

Defines standard unified layout wrappers for database tracking sequence chunks.
Implements native limit-offset parsing to match enterprise frontend query strings.
"""

from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class StandardLimitOffsetPagination(LimitOffsetPagination):
    """
    Global enterprise standard layout for limit-offset table pagination loops.
    Correctly implements LimitOffsetPagination to parse ?limit= and ?offset=.
    """
    default_limit = 50             # Default entries per page if not provided
    limit_query_param = "limit"     # Maps to frontend ?limit= parameter
    offset_query_param = "offset"   # Maps to frontend ?offset= parameter
    max_limit = 200                # Upper limits protection against database strain


class PaginationAdapter:
    """
    Adapts any DRF pagination class to extract unified metadata.
    Works with LimitOffsetPagination, PageNumberPagination, or CursorPagination.
    """

    @staticmethod
    def adapt(paginator, request=None) -> dict:
        """
        Unified pagination metadata generator.
        Extracts count, next, previous, limit, and offset details.
        """
        if not paginator:
            return {
                "count": 0,
                "next": None,
                "previous": None,
                "limit": None,
                "offset": None,
            }

        count = getattr(paginator, "count", 0)
        limit = getattr(paginator, "limit", None)
        offset = getattr(paginator, "offset", None)

        next_link = None
        previous_link = None

        if hasattr(paginator, "get_next_link"):
            next_link = paginator.get_next_link()
        if hasattr(paginator, "get_previous_link"):
            previous_link = paginator.get_previous_link()

        return {
            "count": count,
            "next": next_link,
            "previous": previous_link,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def get_metadata(paginator, page):
        """
        Returns: {count, next, previous}
        Works with any DRF pagination class.
        """
        if hasattr(paginator, 'count'):
            return {
                "count": paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }

        if hasattr(paginator, 'page') and hasattr(paginator.page, 'paginator'):
            return {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }

        return {
            "count": len(page) if page else 0,
            "next": None,
            "previous": None,
        }