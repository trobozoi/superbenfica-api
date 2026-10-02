"""Models do app ``clientes``.

Um ``Cliente`` pode existir sem login (cadastrado no caixa) ou estar vinculado
a um ``Usuario`` com role CLIENTE (autocadastro pelo app).
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class UF(models.TextChoices):
    """Unidades federativas do Brasil."""

    AC = "AC", "Acre"
    AL = "AL", "Alagoas"
    AP = "AP", "Amapá"
    AM = "AM", "Amazonas"
    BA = "BA", "Bahia"
    CE = "CE", "Ceará"
    DF = "DF", "Distrito Federal"
    ES = "ES", "Espírito Santo"
    GO = "GO", "Goiás"
    MA = "MA", "Maranhão"
    MT = "MT", "Mato Grosso"
    MS = "MS", "Mato Grosso do Sul"
    MG = "MG", "Minas Gerais"
    PA = "PA", "Pará"
    PB = "PB", "Paraíba"
    PR = "PR", "Paraná"
    PE = "PE", "Pernambuco"
    PI = "PI", "Piauí"
    RJ = "RJ", "Rio de Janeiro"
    RN = "RN", "Rio Grande do Norte"
    RS = "RS", "Rio Grande do Sul"
    RO = "RO", "Rondônia"
    RR = "RR", "Roraima"
    SC = "SC", "Santa Catarina"
    SP = "SP", "São Paulo"
    SE = "SE", "Sergipe"
    TO = "TO", "Tocantins"


validar_cep = RegexValidator(r"^\d{5}-?\d{3}$", "Informe o CEP no formato 00000-000.")


class Cliente(models.Model):
    """Cliente do supermercado."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuário",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cliente",
    )
    nome = models.CharField("nome", max_length=150)
    email = models.EmailField("e-mail", unique=True)
    telefone = models.CharField("telefone", max_length=20, blank=True, default="")
    loja = models.ForeignKey(
        "filiais.Loja",
        verbose_name="loja preferida",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes",
    )
    data_cadastro = models.DateTimeField("data de cadastro", default=timezone.now)

    class Meta:
        db_table = "sb_cliente"
        ordering = ["nome"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        indexes = [models.Index(fields=["nome"], name="sb_cliente_nome_idx")]

    def __str__(self) -> str:
        return f"{self.nome} <{self.email}>"


class EnderecoCliente(TimeStampedModel):
    """Endereço de entrega de um cliente. Cada cliente tem no máximo um principal."""

    cliente = models.ForeignKey(Cliente, verbose_name="cliente", on_delete=models.CASCADE, related_name="enderecos")
    endereco = models.CharField("logradouro", max_length=255)
    numero = models.CharField("número", max_length=20)
    complemento = models.CharField("complemento", max_length=100, blank=True, default="")
    bairro = models.CharField("bairro", max_length=100)
    cidade = models.CharField("cidade", max_length=100)
    estado = models.CharField("estado", max_length=2, choices=UF.choices)
    cep = models.CharField("CEP", max_length=9, validators=[validar_cep])
    principal = models.BooleanField("principal", default=False)

    class Meta:
        db_table = "sb_endereco_cliente"
        ordering = ["cliente", "-principal", "id"]
        verbose_name = "endereço do cliente"
        verbose_name_plural = "endereços dos clientes"
        constraints = [
            models.UniqueConstraint(
                fields=["cliente"],
                condition=models.Q(principal=True),
                name="sb_endereco_um_principal_por_cliente",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.endereco}, {self.numero} - {self.bairro}, {self.cidade}/{self.estado}"
