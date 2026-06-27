from rest_framework.pagination import PageNumberPagination

class StandardLimitOffsetPagination(PageNumberPagination):
    """
    Global enterprise standard layout for limit-offset table pagination loops.
    """
    page_size = 50  # Default number of entries per page
    page_size_query_param = "limit"  # Allows frontend to pass ?limit=100
    max_page_size = 200




from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class PaginationAdapter:
    """
    Adapts any DRF pagination class to extract unified metadata.
    Works with LimitOffsetPagination, PageNumberPagination, or CursorPagination.
    """
    
    @staticmethod
    def get_metadata(paginator, page):
        """
        Returns: {count, next, previous}
        Works with any DRF pagination class.
        """
        # LimitOffsetPagination
        if hasattr(paginator, 'count'):
            return {
                "count": paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }
        
        # PageNumberPagination
        if hasattr(paginator, 'page') and hasattr(paginator.page, 'paginator'):
            return {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
            }
        
        # Fallback — no pagination or unknown
        return {
            "count": len(page) if page else 0,
            "next": None,
            "previous": None,
        }