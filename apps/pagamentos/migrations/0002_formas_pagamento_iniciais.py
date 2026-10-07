"""Cadastra as formas de pagamento padrão da rede.

Idempotente: usa o nome como chave e não altera formas já existentes. A volta
(``migrate pagamentos 0001``) não apaga nada, para não quebrar pedidos que já
usem essas formas.
"""

from django.db import migrations

FORMAS_INICIAIS = (
    # (nome, tipo, permite_troco, ordem)
    ("Pix", "PIX", False, 1),
    ("Cartão de crédito", "CREDITO", False, 2),
    ("Cartão de débito", "DEBITO", False, 3),
    ("Dinheiro", "DINHEIRO", True, 4),
    ("Vale-alimentação", "VALE_ALIMENTACAO", False, 5),
)


def cadastrar_formas(apps, schema_editor):
    """Cria as formas de pagamento que ainda não existem."""
    forma_pagamento = apps.get_model("pagamentos", "FormaPagamento")
    for nome, tipo, permite_troco, ordem in FORMAS_INICIAIS:
        forma_pagamento.objects.get_or_create(
            nome=nome, defaults={"tipo": tipo, "permite_troco": permite_troco, "ordem": ordem}
        )


class Migration(migrations.Migration):
    dependencies = [("pagamentos", "0001_initial")]

    operations = [migrations.RunPython(cadastrar_formas, migrations.RunPython.noop)]
