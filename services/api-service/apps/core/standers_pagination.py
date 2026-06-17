from rest_framework.pagination import PageNumberPagination

class StandardLimitOffsetPagination(PageNumberPagination):
    """
    Global enterprise standard layout for limit-offset table pagination loops.
    """
    page_size = 50  # Default number of entries per page
    page_size_query_param = "limit"  # Allows frontend to pass ?limit=100
    max_page_size = 200