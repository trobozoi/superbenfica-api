#!/usr/bin/env python
"""Utilitário de linha de comando do Django para o projeto Super Benfica.

Por padrão usa ``config.settings.dev``. Em produção defina
``DJANGO_SETTINGS_MODULE=config.settings.prod``.
"""

import os
import sys


def main() -> None:
    """Executa a tarefa administrativa recebida pela linha de comando."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Verifique se ele está instalado e se o ambiente virtual está ativo."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
