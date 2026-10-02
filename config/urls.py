"""Rotas HTTP raiz do projeto.

- ``/``: página de apresentação da API.
- ``/admin/``: Django Admin.
- ``/api/auth/``: autenticação JWT.
- ``/api/...``: recursos REST de cada app.
- ``/api/schema/``, ``/api/docs/`` e ``/api/redoc/``: documentação OpenAPI.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView

from apps.core.views import PaginaInicialView, SwaggerView

api_patterns = [
    path("auth/", include("apps.usuarios.urls_auth")),
    path("", include("apps.usuarios.urls")),
    path("", include("apps.filiais.urls")),
    path("", include("apps.produtos.urls")),
    path("", include("apps.estoque.urls")),
    path("", include("apps.clientes.urls")),
    path("", include("apps.pedidos.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("", PaginaInicialView.as_view(), name="inicio"),
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
]
