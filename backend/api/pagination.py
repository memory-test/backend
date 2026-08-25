from rest_framework.pagination import PageNumberPagination


class PageNumberLimitPagination(PageNumberPagination):
    """Пагинация с контролем количества объектов через параметр."""

    page_size_query_param = 'limit'
