"""Comando ``python manage.py carga_inicial``: popula o banco com dados de exemplo.

O comando é idempotente: cada registro é localizado pela sua chave natural
(nome da loja, e-mail, SKU, código do pedido) com ``get_or_create``, então
pode ser executado várias vezes sem duplicar dados nem sobrescrever
alterações feitas depois da primeira carga.

Os dados ficam em ``apps/core/seed_data/*.json``. As senhas vêm do ``.env``:

- ``DJANGO_SUPERUSER_EMAIL`` / ``DJANGO_SUPERUSER_PASSWORD``: superusuário.
- ``SEED_DEFAULT_PASSWORD``: senha dos usuários de exemplo (um por role).

Os pedidos de exemplo são gravados diretamente (sem baixar estoque), pois
representam um histórico já existente.
"""

import json
import os
from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.clientes.models import Cliente, EnderecoCliente
from apps.core.constants import Role
from apps.estoque.models import EstoqueLocal
from apps.filiais.models import Loja
from apps.pagamentos.models import FormaPagamento
from apps.pedidos.models import ItemPedido, Pedido, Separacao, StatusPedido, StatusSeparacao
from apps.produtos.models import Produto
from apps.usuarios.models import Usuario

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed_data"
PREFIXO_PEDIDO_SEED = "SEED-"
QUANTIDADE_MINIMA_PADRAO = 10
SALDO_BAIXO = 4


def carregar(nome_arquivo: str) -> list[dict[str, Any]]:
    """Lê um arquivo JSON de ``seed_data``."""
    with (SEED_DIR / nome_arquivo).open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def saldo_inicial(indice_loja: int, indice_produto: int) -> int:
    """Saldo determinístico e variado; um a cada 7 produtos fica abaixo do mínimo."""
    if indice_produto % 7 == 3:
        return SALDO_BAIXO
    return 15 + (indice_loja * 17 + indice_produto * 11) % 85


class Command(BaseCommand):
    """Popula lojas, usuários, produtos, estoque, clientes e pedidos de exemplo."""

    help = "Popula o banco com a carga inicial de exemplo (idempotente)."

    def add_arguments(self, parser: CommandParser) -> None:
        """Opções ``--reset`` e ``--no-input``."""
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove os dados de exemplo antes de recriá-los (somente com DEBUG=True).",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            dest="no_input",
            help="Não pede confirmação para o --reset.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Executa a carga dentro de uma única transação."""
        self.verbosity = options["verbosity"]
        self.contagem: dict[str, list[int]] = {}
        senha_padrao = self._variavel_obrigatoria("SEED_DEFAULT_PASSWORD")

        if options["reset"]:
            self._resetar(confirmar=not options["no_input"])

        with transaction.atomic():
            self._criar_superusuario()
            lojas = self._criar_lojas()
            usuarios = self._criar_usuarios(lojas, senha_padrao)
            produtos = self._criar_produtos()
            self._criar_estoques(lojas, produtos)
            clientes = self._criar_clientes(lojas)
            self._criar_pedidos(lojas, produtos, clientes, usuarios)

        for rotulo, (criados, existentes) in self.contagem.items():
            self.stdout.write(f"  {rotulo}: {criados} criados, {existentes} já existiam")
        self.stdout.write(self.style.SUCCESS("Carga inicial concluída."))

    # ------------------------------------------------------------------ apoio

    def _variavel_obrigatoria(self, nome: str) -> str:
        """Lê uma variável de ambiente obrigatória ou aborta o comando."""
        valor = os.environ.get(nome, "")
        if not valor:
            raise CommandError(f"Defina {nome} no arquivo .env antes de rodar a carga inicial.")
        return valor

    def _registrar(self, rotulo: str, objeto: Any, criado: bool) -> None:
        """Contabiliza o resultado e, com ``-v 2``, mostra cada registro."""
        criados, existentes = self.contagem.setdefault(rotulo, [0, 0])
        self.contagem[rotulo] = [criados + int(criado), existentes + int(not criado)]
        if self.verbosity >= 2:
            self.stdout.write(f"    {'+' if criado else '='} {rotulo}: {objeto}")

    # ------------------------------------------------------------------ reset

    def _resetar(self, confirmar: bool) -> None:
        """Apaga somente os registros da carga de exemplo."""
        if not settings.DEBUG:
            raise CommandError("--reset só é permitido com DEBUG=True.")
        if confirmar:
            resposta = input("Isso apagará os dados de exemplo. Digite 'sim' para continuar: ")
            if resposta.strip().lower() != "sim":
                raise CommandError("Operação cancelada.")
        try:
            with transaction.atomic():
                Pedido.objects.filter(codigo__startswith=PREFIXO_PEDIDO_SEED).delete()
                Cliente.objects.filter(email__in=[c["email"] for c in carregar("clientes.json")]).delete()
                Produto.objects.filter(sku__in=[p["sku"] for p in carregar("produtos.json")]).delete()
                Usuario.objects.filter(email__in=[u["email"] for u in carregar("usuarios.json")]).delete()
                Loja.objects.filter(nome__in=[loja["nome"] for loja in carregar("lojas.json")]).delete()
        except ProtectedError as exc:
            raise CommandError("Há registros reais ligados aos dados de exemplo; o reset foi desfeito.") from exc
        self.stdout.write(self.style.WARNING("Dados de exemplo removidos."))

    # ------------------------------------------------------------- entidades

    def _criar_superusuario(self) -> None:
        """Cria o superusuário definido no ``.env`` (se ainda não existir)."""
        email = self._variavel_obrigatoria("DJANGO_SUPERUSER_EMAIL").lower()
        if Usuario.objects.filter(email=email).exists():
            self._registrar("superusuário", email, criado=False)
            return
        senha = self._variavel_obrigatoria("DJANGO_SUPERUSER_PASSWORD")
        Usuario.objects.create_superuser(email=email, password=senha, nome="Administrador")
        self._registrar("superusuário", email, criado=True)

    def _criar_lojas(self) -> dict[str, Loja]:
        """Cria as filiais e retorna um mapa ``nome -> Loja``."""
        lojas = {}
        for dados in carregar("lojas.json"):
            loja, criado = Loja.objects.get_or_create(
                nome=dados["nome"],
                defaults={
                    "endereco": dados["endereco"],
                    "telefone": dados["telefone"],
                    "horario_abertura": time.fromisoformat(dados["horario_abertura"]),
                    "horario_fechamento": time.fromisoformat(dados["horario_fechamento"]),
                },
            )
            lojas[loja.nome] = loja
            self._registrar("lojas", loja, criado)
        return lojas

    def _criar_usuarios(self, lojas: dict[str, Loja], senha: str) -> dict[str, Usuario]:
        """Cria um usuário por role e retorna um mapa ``email -> Usuario``."""
        usuarios = {}
        for dados in carregar("usuarios.json"):
            usuario = Usuario.objects.filter(email=dados["email"]).first()
            criado = usuario is None
            if criado:
                usuario = Usuario.objects.create_user(
                    email=dados["email"],
                    password=senha,
                    nome=dados["nome"],
                    telefone=dados["telefone"],
                    role=dados["role"],
                    loja=lojas[dados["loja"]],
                )
            if usuario.role == Role.CLIENTE:
                Cliente.objects.get_or_create(
                    email=usuario.email,
                    defaults={
                        "usuario": usuario,
                        "nome": usuario.nome,
                        "telefone": usuario.telefone,
                        "loja": usuario.loja,
                    },
                )
            usuarios[usuario.email] = usuario
            self._registrar("usuários", usuario, criado)
        return usuarios

    def _criar_produtos(self) -> list[Produto]:
        """Cria o catálogo de produtos."""
        produtos = []
        for dados in carregar("produtos.json"):
            produto, criado = Produto.objects.get_or_create(
                sku=dados["sku"],
                defaults={
                    "nome": dados["nome"],
                    "descricao": dados["descricao"],
                    "categoria": dados["categoria"],
                    "preco": Decimal(dados["preco"]),
                },
            )
            produtos.append(produto)
            self._registrar("produtos", produto, criado)
        return produtos

    def _criar_estoques(self, lojas: dict[str, Loja], produtos: list[Produto]) -> None:
        """Cadastra todos os produtos no estoque de todas as filiais."""
        for indice_loja, loja in enumerate(lojas.values()):
            for indice_produto, produto in enumerate(produtos):
                estoque, criado = EstoqueLocal.objects.get_or_create(
                    loja=loja,
                    produto=produto,
                    defaults={
                        "quantidade": saldo_inicial(indice_loja, indice_produto),
                        "quantidade_minima": QUANTIDADE_MINIMA_PADRAO,
                    },
                )
                self._registrar("estoques", estoque, criado)

    def _criar_clientes(self, lojas: dict[str, Loja]) -> dict[str, Cliente]:
        """Cria os clientes com endereço principal e retorna ``email -> Cliente``."""
        clientes = {}
        for dados in carregar("clientes.json"):
            cliente, criado = Cliente.objects.get_or_create(
                email=dados["email"],
                defaults={"nome": dados["nome"], "telefone": dados["telefone"], "loja": lojas[dados["loja"]]},
            )
            if criado:
                EnderecoCliente.objects.create(cliente=cliente, principal=True, **dados["endereco"])
            clientes[cliente.email] = cliente
            self._registrar("clientes", cliente, criado)
        return clientes

    def _criar_pedidos(
        self,
        lojas: dict[str, Loja],
        produtos: list[Produto],
        clientes: dict[str, Cliente],
        usuarios: dict[str, Usuario],
    ) -> None:
        """Cria os pedidos de exemplo com itens e separações."""
        por_sku = {produto.sku: produto for produto in produtos}
        # Formas cadastradas pela migration pagamentos.0002; a primeira de cada tipo é usada.
        formas: dict[str, FormaPagamento] = {}
        for forma in FormaPagamento.objects.filter(ativa=True).order_by("ordem"):
            formas.setdefault(forma.tipo, forma)
        for dados in carregar("pedidos.json"):
            pedido, criado = Pedido.objects.get_or_create(
                codigo=dados["codigo"],
                defaults={
                    "cliente": clientes[dados["cliente"]],
                    "loja": lojas[dados["loja"]],
                    "status": dados["status"],
                    "forma_pagamento": formas.get(dados.get("forma_pagamento", "")),
                    "observacao": dados.get("observacao", ""),
                },
            )
            if criado:
                ItemPedido.objects.bulk_create(
                    ItemPedido(
                        pedido=pedido,
                        produto=por_sku[item["sku"]],
                        quantidade=item["quantidade"],
                        preco_unitario=por_sku[item["sku"]].preco,
                    )
                    for item in dados["itens"]
                )
                self._criar_separacao(pedido, usuarios.get(dados.get("separador", "")))
            self._registrar("pedidos", pedido, criado)

    def _criar_separacao(self, pedido: Pedido, separador: Usuario | None) -> None:
        """Registra a separação compatível com o status do pedido de exemplo."""
        if separador is None:
            return
        concluida = pedido.status == StatusPedido.SEPARADO
        Separacao.objects.create(
            pedido=pedido,
            usuario=separador,
            status=StatusSeparacao.CONCLUIDA if concluida else StatusSeparacao.EM_ANDAMENTO,
            data_conclusao=timezone.now() if concluida else None,
        )
        self._registrar("separações", pedido.codigo, criado=True)
