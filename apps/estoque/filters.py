"""Filtros de consulta do estoque (django-filter)."""

from django.db.models import F, QuerySet
from django_filters import rest_framework as filters

from apps.estoque.models import EstoqueLocal


class EstoqueLocalFilter(filters.FilterSet):
    """Filtra por produto, filial e saldo abaixo do mínimo."""

    abaixo_do_minimo = filters.BooleanFilter(method="filtrar_abaixo_do_minimo", label="Somente saldos abaixo do mínimo")

    class Meta:
        model = EstoqueLocal
        fields = ("produto", "loja", "abaixo_do_minimo")

    def filtrar_abaixo_do_minimo(
        self, queryset: QuerySet[EstoqueLocal], name: str, value: bool | None
    ) -> QuerySet[EstoqueLocal]:
        """Aplica ``quantidade <= quantidade_minima`` (ou o inverso)."""
        if value is None:
            return queryset
        condicao = {"quantidade__lte": F("quantidade_minima")}
        return queryset.filter(**condicao) if value else queryset.exclude(**condicao)
