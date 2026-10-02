"""Configuração da aplicação Celery (processamento assíncrono).

As opções são lidas do settings do Django com o prefixo ``CELERY_`` e as tasks
são descobertas automaticamente no módulo ``tasks.py`` de cada app.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("superbenfica")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
