from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes

RU_SEARCH_PARAM = OpenApiParameter(
    name='search',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Поисковый запрос.',
)
RU_ORDERING_PARAM = OpenApiParameter(
    name='ordering',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description='Поле для сортировки результатов (например, `title` или `-created_at`).',
)
RU_LIMIT_PARAM = OpenApiParameter(
    name='limit',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Количество результатов на странице.',
)
RU_PAGE_PARAM = OpenApiParameter(
    name='page',
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description='Номер страницы в пагинированном наборе результатов.',
)