# Arquitetura

## Estrutura de pastas

```
superbenfica-api/
├── config/                  # Projeto Django
│   ├── settings/            # base, dev, prod, test
│   ├── urls.py              # Rotas HTTP raiz + Swagger
│   ├── asgi.py              # HTTP + WebSocket (Channels)
│   ├── wsgi.py              # Somente HTTP
│   └── celery.py            # Aplicação Celery
├── apps/
│   ├── core/                # Roles, permissões, mixins, WebSocket, carga inicial
│   ├── filiais/             # Loja
│   ├── usuarios/            # Usuario (login por e-mail), JWT, autocadastro
│   ├── produtos/            # Produto (catálogo da rede)
│   ├── estoque/             # EstoqueLocal (saldo por filial) + serviços de movimentação
│   ├── clientes/            # Cliente, EnderecoCliente
│   ├── pedidos/             # Pedido, ItemPedido, Separacao + fluxo de status
│   └── relatorios/          # Consultas agregadas com cache
├── tests/                   # pytest
├── docs/                    # Esta documentação + openapi.yaml
├── nginx/                   # Proxy reverso
└── .github/workflows/       # CI com SonarQube
```

Cada app segue a mesma organização:

| Arquivo | Responsabilidade |
|---------|------------------|
| `models.py` | Entidades, constraints e índices |
| `serializers.py` | Validação de entrada e formato de saída |
| `views.py` | ViewSets, permissões e documentação Swagger (`extend_schema`) |
| `services.py` | Regras de negócio transacionais (estoque, pedidos, relatórios) |
| `tasks.py` | Tasks Celery |
| `urls.py` | Rotas do app |
| `admin.py` | Django Admin |

As views ficam enxutas: toda regra que altera mais de uma tabela ou exige bloqueio fica em `services.py`.

## Modelo de dados

```mermaid
erDiagram
    sb_loja ||--o{ sb_usuario : "funcionários"
    sb_loja ||--o{ sb_estoque_local : "estoque"
    sb_produto ||--o{ sb_estoque_local : "saldo"
    sb_loja ||--o{ sb_cliente : "loja preferida"
    sb_usuario |o--o| sb_cliente : "login do cliente"
    sb_cliente ||--o{ sb_endereco_cliente : "endereços"
    sb_cliente ||--o{ sb_pedido : "pedidos"
    sb_loja ||--o{ sb_pedido : "pedidos"
    sb_pedido ||--|{ sb_item_pedido : "itens"
    sb_produto ||--o{ sb_item_pedido : "vendido em"
    sb_pedido ||--o{ sb_separacao : "separações"
    sb_usuario ||--o{ sb_separacao : "separador"
```

Regras garantidas pelo banco:

| Tabela | Regra |
|--------|-------|
| `sb_produto` | `sku` único; `preco > 0` |
| `sb_estoque_local` | um registro por (produto, loja); `quantidade >= 0`; `quantidade_minima >= 0` |
| `sb_item_pedido` | um item por (pedido, produto); `quantidade > 0`; `preco_unitario > 0` |
| `sb_endereco_cliente` | no máximo um endereço `principal` por cliente |
| `sb_separacao` | no máximo uma separação `EM_ANDAMENTO` por pedido |

Registros com histórico não são apagados. Filiais, produtos e usuários são **desativados** (`ativa`/`ativo`/`is_active = false`), e pedidos protegem cliente, loja e produto (`on_delete=PROTECT`).

## Fluxo do pedido

```mermaid
stateDiagram-v2
    [*] --> PENDENTE: criar (baixa estoque)
    PENDENTE --> EM_SEPARACAO: iniciar-separacao
    EM_SEPARACAO --> SEPARADO: concluir separação
    SEPARADO --> FINALIZADO: finalizar
    PENDENTE --> CANCELADO: cancelar (devolve estoque)
    EM_SEPARACAO --> CANCELADO
    SEPARADO --> CANCELADO
```

- **Concorrência:** criar, cancelar e mudar de status são operações dentro de `transaction.atomic` com `select_for_update`. Duas vendas simultâneas não consomem o mesmo saldo, e duas pessoas não alteram o mesmo pedido ao mesmo tempo.
- **Preço congelado:** `ItemPedido.preco_unitario` guarda o preço do momento da compra.
- **Erros de negócio:** estoque insuficiente, produto indisponível e transição inválida retornam **HTTP 409**.

## Tempo real (WebSocket)

```mermaid
sequenceDiagram
    participant Caixa as Caixa (HTTP)
    participant API as Django (services)
    participant Redis as Channel layer (Redis)
    participant Equipe as Equipe da filial (WS)
    participant Cliente as Cliente (WS)
    Caixa->>API: POST /api/pedidos/
    API->>API: transaction.atomic + select_for_update
    API-->>Redis: on_commit → group_send loja_<id> / usuario_<id>
    Redis-->>Equipe: {"evento": "pedido.criado", ...}
    Redis-->>Cliente: {"evento": "pedido.criado", ...}
```

Os eventos são enviados só depois do commit (`transaction.on_commit`), então ninguém recebe notificação de uma operação desfeita. Se o Redis falhar, o erro vai para o log e a requisição não é interrompida.

## Tarefas assíncronas (Celery Beat)

| Task | Frequência | O que faz |
|------|-----------|-----------|
| `apps.estoque.tasks.verificar_estoque_minimo` | a cada hora | Publica `estoque.abaixo_do_minimo` para cada filial |
| `apps.relatorios.tasks.gerar_resumo_diario` | diária | Guarda as vendas do dia anterior no cache por 7 dias |

## Cache

Os relatórios (`/api/relatorios/*`) ficam em cache no Redis por `CACHE_TTL_RELATORIOS` segundos. A chave combina relatório, filial, período e limite.

## Configuração por ambiente

| Settings | Banco | Redis | Observações |
|----------|-------|-------|-------------|
| `dev` | PostgreSQL do `.env` | opcional | `DEBUG=True`, sessão habilitada para o Swagger |
| `prod` | PostgreSQL do `.env` | obrigatório na prática | HTTPS, HSTS, cookies seguros, falha sem `SECRET_KEY`/`ALLOWED_HOSTS` |
| `test` | SQLite em memória | em memória | Nunca acessa o Supabase |
