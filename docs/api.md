# Guia da API

A referência completa e interativa está no **Swagger** (`/api/docs/`). Ali cada endpoint aparece com descrição, parâmetros, exemplos e perfis permitidos. Este guia resume os conceitos.

## Autenticação (JWT)

```http
POST /api/auth/token/
Content-Type: application/json

{"email": "gerente.centro@superbenfica.com.br", "password": "..."}
```

Resposta: `{"access": "...", "refresh": "..."}`. O `access` traz as claims `nome`, `role` e `loja_id`.

Envie o token assim: `Authorization: Bearer <access>`.

| Endpoint | Uso |
|----------|-----|
| `POST /api/auth/token/` | Login |
| `POST /api/auth/token/refresh/` | Novo `access` (o `refresh` é rotacionado) |
| `POST /api/auth/token/verify/` | Verifica se um token é válido |
| `POST /api/auth/logout/` | Invalida o `refresh` (blacklist) |
| `POST /api/auth/registrar/` | Autocadastro público de cliente |

No Swagger, clique em **Authorize** e cole só o valor do `access` (sem "Bearer").

## Perfis e escopo

| Recurso | ADMIN | GERENTE | SEPARADOR | CAIXA | CLIENTE |
|---------|:-----:|:-------:|:---------:|:-----:|:-------:|
| Filiais: ler | ✔ | ✔ | ✔ | ✔ | ✔ |
| Filiais: escrever | ✔ | | | | |
| Usuários | todos | da filial | | | |
| Produtos: ler | ✔ | ✔ | ✔ | ✔ | ativos |
| Produtos: escrever | ✔ | ✔ | | | |
| Estoque: ler | todas | da filial | da filial | da filial | |
| Estoque: escrever/ajustar | ✔ | da filial | | | |
| Clientes: ler | ✔ | ✔ | ✔ | ✔ | o próprio |
| Clientes: criar | ✔ | ✔ | | ✔ | via `/auth/registrar/` |
| Pedidos: ler | todos | da filial | da filial | da filial | os próprios |
| Pedidos: criar | ✔ | da filial | | da filial | para si |
| Iniciar/concluir separação | ✔ | ✔ | ✔ | | |
| Finalizar pedido | ✔ | ✔ | | ✔ | |
| Cancelar pedido | ✔ | ✔ | ✔ | ✔ | se PENDENTE |
| Relatórios | todas | da filial | | | |

## Endpoints

| Recurso | Rotas |
|---------|-------|
| Usuários | `GET/POST /api/usuarios/`, `GET/PUT/PATCH/DELETE /api/usuarios/{id}/`, `GET /api/usuarios/me/` |
| Filiais | `/api/lojas/` (CRUD) |
| Produtos | `/api/produtos/` (CRUD; filtros `categoria`, `ativo`; `search`) |
| Estoque | `/api/estoques/` (CRUD; filtros `loja`, `produto`, `abaixo_do_minimo`), `POST /api/estoques/{id}/ajustar/` |
| Clientes | `/api/clientes/`, `/api/enderecos/` |
| Pedidos | `GET/POST /api/pedidos/`, `POST /api/pedidos/{id}/cancelar/`, `POST /api/pedidos/{id}/iniciar-separacao/`, `POST /api/pedidos/{id}/finalizar/` |
| Separações | `GET /api/separacoes/`, `POST /api/separacoes/{id}/concluir/` |
| Relatórios | `GET /api/relatorios/vendas/`, `produtos-mais-vendidos/`, `pedidos-por-status/`, `estoque-baixo/` (parâmetros `loja`, `inicio`, `fim`, `limite`) |

Todas as listagens são paginadas (`?page=`, 20 por página) e aceitam `?ordering=`.

### Exemplo: criar pedido

```http
POST /api/pedidos/
Authorization: Bearer <access do cliente>

{"loja": 1, "itens": [{"produto": 5, "quantidade": 2}], "observacao": "Sem sacolas"}
```

Um funcionário também informa `"cliente": <id>`. Se faltar estoque, a resposta é **409**.

## Códigos de resposta

| Código | Significado |
|--------|-------------|
| 400 | Dados inválidos (detalhes por campo) |
| 401 | Token ausente, inválido ou expirado |
| 403 | O perfil não permite a operação ou a filial é outra |
| 404 | Recurso inexistente ou fora do seu escopo |
| 409 | Regra de negócio: estoque insuficiente, produto indisponível ou transição de status inválida |
| 429 | Limite de requisições (60/min anônimo, 600/min autenticado) |

## WebSocket

| Canal | Quem conecta | Eventos |
|-------|--------------|---------|
| `ws(s)://<host>/ws/lojas/<loja_id>/?token=<access>` | Funcionários da filial (ADMIN: qualquer filial) | `pedido.criado`, `pedido.atualizado`, `estoque.atualizado`, `estoque.abaixo_do_minimo` |
| `ws(s)://<host>/ws/notificacoes/?token=<access>` | Qualquer usuário autenticado | `pedido.criado`, `pedido.atualizado` dos próprios pedidos |

Formato das mensagens: `{"evento": "pedido.atualizado", "dados": {"pedido_id": 1, "codigo": "PED-...", "status": "SEPARADO"}}`.

Envie `{"acao": "ping"}` para receber `{"evento": "pong"}`. A conexão é fechada com código **4401** (sem autenticação) ou **4403** (sem acesso à filial).

```js
const ws = new WebSocket(`wss://api.exemplo.com/ws/lojas/1/?token=${access}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
