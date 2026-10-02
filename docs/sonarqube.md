# SonarQube

## Como o código atende ao "Sonar way"

| Regra | Como é atendida |
|-------|-----------------|
| S2068: credenciais no código | Senhas, `SECRET_KEY` e o banco vêm do `.env`; o `.env` está no `.gitignore` e no `.dockerignore` |
| S3776: complexidade cognitiva ≤ 15 | Regras em funções pequenas; a carga inicial tem um método por entidade; o ruff aplica `max-complexity = 10` |
| S107: no máximo 7 parâmetros | Serviços usam argumentos nomeados e `dataclass` (`ItemSolicitado`) |
| S1192: literais duplicados | Roles e status em `TextChoices`/constantes (`apps/core/constants.py`) |
| S6553: `null=True` em texto | Campos de texto usam `blank=True, default=""` |
| S6554: `__str__` nos models | Todos os models definem `__str__` e `Meta` (`db_table`, `ordering`, `verbose_name`) |
| `fields = "__all__"` | Todos os serializers listam os campos explicitamente |
| Exceções genéricas | Só exceções específicas são capturadas (`TokenError`, `RedisError`, `ProtectedError`...) |
| Datas sem timezone | `USE_TZ=True` e `django.utils.timezone.now()` |
| Valores monetários | `DecimalField`/`Decimal` |
| Concorrência | `transaction.atomic` + `select_for_update` no estoque e nos pedidos |
| S5145: log injection | Texto livre do usuário (motivo do ajuste) não vai para o log |

Métricas atuais: **76 testes** e cobertura de **~98%** (meta do Quality Gate: ≥ 80%).

## Security Hotspots para revisão manual

| Local | Motivo | Situação |
|-------|--------|----------|
| `config/settings/base.py`: `CORS_ALLOWED_ORIGINS` | O CORS libera origens externas | Seguro: lista explícita vinda do `.env`, sem `CORS_ALLOW_ALL_ORIGINS` |
| `config/settings/dev.py`: `DEBUG = True` | Debug ativo | Seguro: só em desenvolvimento; `prod.py` força `DEBUG=False` |
| `docker-compose.yml`: `redis://redis:6379/0` | Protocolo sem TLS | Aceitável só na rede interna do Docker; em produção use `rediss://` com senha |
| `nginx/nginx.conf`: `listen 80` | HTTP sem TLS | Configuração de desenvolvimento; em produção adicione `listen 443 ssl` e redirecione para HTTPS |
| `apps/core/middleware.py`: token na query string | O token pode aparecer em logs de proxy | O navegador não envia cabeçalhos no handshake WebSocket; use sempre `wss://` e um `access` de vida curta (15 min) |
| `apps/usuarios/views.py`: `RegistroClienteView` com `AllowAny` | Endpoint público | Intencional (autocadastro); protegido por throttling (60/min) e validação de senha |
| `apps/pedidos/models.py`: `secrets.token_hex` | Geração de valor aleatório | Seguro: usa `secrets`, não `random` |
| `config/settings/test.py`: `MD5PasswordHasher` | Hash fraco | Só acelera os testes; o arquivo está fora da análise (`sonar.exclusions`) |
| `Dockerfile` | Execução do container | Imagem com tag fixa e usuário não-root (`USER app`) |

## SonarQube Cloud (CI)

A análise do CI usa o [SonarQube Cloud](https://sonarcloud.io), gratuito para repositórios públicos.

1. Entre em https://sonarcloud.io com a conta do GitHub e importe a organização `trobozoi`.
2. Analise o repositório `superbenfica-api`. A chave do projeto fica `trobozoi_superbenfica-api`, igual à do `sonar-project.properties`.
3. Em *Administration → Analysis Method*, **desative a Automatic Analysis**. O CI já faz a análise com cobertura, e as duas juntas dão conflito.
4. Gere um token em *My Account → Security* e crie o secret `SONAR_TOKEN` no GitHub (*Settings → Secrets and variables → Actions*).

## Rodando localmente

```bash
docker compose --profile quality up -d sonarqube    # http://localhost:9000 (admin/admin no 1º acesso)
pytest                                              # gera coverage.xml
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=<seu token> -Dsonar.projectKey=superbenfica-api
```
