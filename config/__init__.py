"""Pacote de configuração do projeto Super Benfica.

Importa a aplicação Celery para que as tasks com ``@shared_task`` sejam
registradas assim que o Django iniciar.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
