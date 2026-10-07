"""Serializers do app ``pedidos``."""

from typing import Any

from rest_framework import serializers

from apps.clientes.models import Cliente, EnderecoCliente
from apps.core.mixins import validar_loja_do_usuario
from apps.filiais.models import Loja
from apps.pagamentos.models import FormaPagamento
from apps.pedidos.models import ItemPedido, Pedido, Separacao, TipoEntrega
from apps.pedidos.services import ItemSolicitado, criar_pedido
from apps.produtos.models import Produto


class ItemPedidoSerializer(serializers.ModelSerializer):
    """Item de pedido (somente leitura)."""

    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    produto_codigo_barras = serializers.CharField(source="produto.codigo_barras", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ItemPedido
        fields = (
            "id",
            "produto",
            "produto_nome",
            "produto_sku",
            "produto_codigo_barras",
            "quantidade",
            "preco_unitario",
            "subtotal",
            "separado",
        )
        read_only_fields = fields


class MarcarItemSerializer(serializers.Serializer):
    """Marca ou desmarca um item no checklist da separação."""

    item = serializers.IntegerField(min_value=1, help_text="ID do item do pedido.")
    separado = serializers.BooleanField()


class SeparacaoSerializer(serializers.ModelSerializer):
    """Separação de um pedido (somente leitura)."""

    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True)
    pedido_codigo = serializers.CharField(source="pedido.codigo", read_only=True)

    class Meta:
        model = Separacao
        fields = (
            "id",
            "pedido",
            "pedido_codigo",
            "usuario",
            "usuario_nome",
            "status",
            "data_inicio",
            "data_conclusao",
        )
        read_only_fields = fields


class PedidoSerializer(serializers.ModelSerializer):
    """Pedido completo com itens, total e separações."""

    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    loja_nome = serializers.CharField(source="loja.nome", read_only=True)
    forma_pagamento_nome = serializers.CharField(source="forma_pagamento.nome", read_only=True, default=None)
    itens = ItemPedidoSerializer(many=True, read_only=True)
    separacoes = SeparacaoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id",
            "codigo",
            "cliente",
            "cliente_nome",
            "loja",
            "loja_nome",
            "status",
            "forma_pagamento",
            "forma_pagamento_nome",
            "tipo_entrega",
            "endereco_entrega",
            "observacao",
            "itens",
            "total",
            "separacoes",
            "data_criacao",
            "data_atualizacao",
        )
        read_only_fields = fields


class ItemPedidoEntradaSerializer(serializers.Serializer):
    """Produto e quantidade informados na criação do pedido."""

    produto = serializers.PrimaryKeyRelatedField(queryset=Produto.objects.filter(ativo=True))
    quantidade = serializers.IntegerField(min_value=1, max_value=999)


class PedidoCreateSerializer(serializers.Serializer):
    """Criação de pedido.

    - CLIENTE: o pedido é feito em seu nome (``cliente`` é ignorado).
    - Funcionário: informa ``cliente`` e só pode vender na própria filial.
    """

    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(), required=False, help_text="Obrigatório para funcionários."
    )
    loja = serializers.PrimaryKeyRelatedField(queryset=Loja.objects.filter(ativa=True))
    forma_pagamento = serializers.PrimaryKeyRelatedField(
        queryset=FormaPagamento.objects.filter(ativa=True),
        help_text="ID de uma forma de pagamento ativa (veja GET /api/formas-pagamento/).",
    )
    itens = ItemPedidoEntradaSerializer(many=True, allow_empty=False)
    observacao = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)
    tipo_entrega = serializers.ChoiceField(choices=TipoEntrega.choices, default=TipoEntrega.RETIRADA)
    endereco = serializers.PrimaryKeyRelatedField(
        queryset=EnderecoCliente.objects.all(),
        required=False,
        allow_null=True,
        default=None,
        help_text="ID de um endereço do cliente. Obrigatório quando tipo_entrega é DOMICILIO.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Define o cliente do pedido conforme o perfil de quem está pedindo."""
        user = self.context["request"].user
        if not user.is_equipe:
            cliente = Cliente.objects.filter(usuario=user).first()
            if cliente is None:
                raise serializers.ValidationError("Seu usuário não possui cadastro de cliente.")
            attrs["cliente"] = cliente
        else:
            if "cliente" not in attrs:
                raise serializers.ValidationError({"cliente": "Informe o cliente do pedido."})
            validar_loja_do_usuario(user, attrs["loja"].pk)
        self._validar_entrega(attrs)
        return attrs

    @staticmethod
    def _validar_entrega(attrs: dict[str, Any]) -> None:
        """Na entrega em domicílio, exige um endereço do próprio cliente do pedido."""
        if attrs["tipo_entrega"] != TipoEntrega.DOMICILIO:
            attrs["endereco"] = None
            return
        endereco = attrs["endereco"]
        if endereco is None:
            raise serializers.ValidationError({"endereco": "Informe o endereço de entrega."})
        if endereco.cliente_id != attrs["cliente"].pk:
            # Mesma resposta de um ID inexistente: não revela endereços de outros clientes.
            raise serializers.ValidationError({"endereco": "Endereço não encontrado para este cliente."})

    def create(self, validated_data: dict[str, Any]) -> Pedido:
        """Delegação para o serviço que baixa o estoque e grava o pedido."""
        itens = [ItemSolicitado(item["produto"], item["quantidade"]) for item in validated_data["itens"]]
        return criar_pedido(
            cliente=validated_data["cliente"],
            loja=validated_data["loja"],
            itens=itens,
            forma_pagamento=validated_data["forma_pagamento"],
            observacao=validated_data["observacao"],
            tipo_entrega=validated_data["tipo_entrega"],
            endereco=validated_data["endereco"],
        )

    def to_representation(self, instance: Pedido) -> dict[str, Any]:
        """Retorna o pedido criado no formato de ``PedidoSerializer``."""
        return PedidoSerializer(instance, context=self.context).data
