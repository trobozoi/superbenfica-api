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
| Saiu para entrega / finalizar pedido | ✔ | ✔ | | ✔ | |
| Cancelar pedido | ✔ | ✔ | ✔ | ✔ | se PENDENTE |
| Relatórios | todas | da filial | | | |

## Endpoints

| Recurso | Rotas |
|---------|-------|
| Usuários | `GET/POST /api/usuarios/`, `GET/PUT/PATCH/DELETE /api/usuarios/{id}/`, `GET /api/usuarios/me/` |
| Filiais | `/api/lojas/` (CRUD) |
| Produtos | `/api/produtos/` (CRUD; filtros `categoria`, `ativo`, `codigo_barras`; `search` por nome/SKU/código de barras), `POST/DELETE /api/produtos/{id}/foto/` |
| Estoque | `/api/estoques/` (CRUD; filtros `loja`, `produto`, `abaixo_do_minimo`), `POST /api/estoques/{id}/ajustar/` |
| Clientes | `/api/clientes/`, `/api/enderecos/` |
| Formas de pagamento | `/api/formas-pagamento/` (leitura: todos; escrita: ADMIN; filtros `tipo`, `ativa`) |
| Pedidos | `GET/POST /api/pedidos/` (filtros `forma_pagamento` e `tipo_entrega`), `POST /api/pedidos/{id}/cancelar/`, `POST /api/pedidos/{id}/iniciar-separacao/`, `POST /api/pedidos/{id}/despachar/` (saiu para entrega; só entrega em domicílio), `POST /api/pedidos/{id}/finalizar/` |
| Separações | `GET /api/separacoes/`, `POST /api/separacoes/{id}/marcar-item/`, `POST /api/separacoes/{id}/concluir/` |
| Relatórios | `GET /api/relatorios/vendas/`, `produtos-mais-vendidos/`, `pedidos-por-status/`, `estoque-baixo/` (parâmetros `loja`, `inicio`, `fim`, `limite`) |

Todas as listagens são paginadas (`?page=`, 20 por página) e aceitam `?ordering=`.

### Exemplo: criar pedido

```http
POST /api/pedidos/
Authorization: Bearer <access do cliente>

{"loja": 1, "forma_pagamento": 1, "itens": [{"produto": 5, "quantidade": 2}], "observacao": "Sem sacolas"}
```

Um funcionário também informa `"cliente": <id>`. Se faltar estoque, a resposta é **409**. `forma_pagamento` é obrigatória e precisa estar ativa (**400** se faltar ou estiver inativa).

**Forma de entrega:** `tipo_entrega` é `RETIRADA` (padrão, retirada na loja) ou `DOMICILIO`. Na entrega em domicílio, informe `"endereco": <id>` com um endereço do próprio cliente (`/api/enderecos/`); sem ele, ou com endereço de outro cliente, a resposta é **400**. O endereço é copiado para `endereco_entrega` do pedido, então editá-lo ou excluí-lo depois não altera pedidos já feitos. A entrega não tem taxa: o total é a soma dos itens.

### Formas de pagamento

A tabela `sb_forma_pagamento` já vem com Pix, Cartão de crédito, Cartão de débito, Dinheiro (`permite_troco=true`) e Vale-alimentação. O ADMIN pode cadastrar variações (ex.: um vale de bandeira específica) com um dos tipos `PIX`, `CREDITO`, `DEBITO`, `DINHEIRO` ou `VALE_ALIMENTACAO`. Excluir uma forma apenas a desativa: ela some para os clientes e não pode ser usada em pedidos novos, mas continua nos pedidos antigos.

### Foto do produto

```http
POST /api/produtos/5/foto/
Authorization: Bearer <access de ADMIN ou GERENTE>
Content-Type: multipart/form-data; boundary=...

foto=<arquivo JPEG, PNG ou WebP de até 2 MB>
```

A imagem é validada pelo conteúdo (não pela extensão), regravada em WebP com no máximo 1200 px e sem metadados (EXIF/GPS), e substitui a anterior. A resposta é o produto, com `foto` em URL absoluta. `DELETE` remove a foto. Os arquivos ficam em `MEDIA_ROOT` (padrão `media/`); no Docker, no volume `media`, servido pelo Nginx em `/media/`.

### Código de barras

`codigo_barras` é opcional. Quando informado, precisa ser um GTIN válido (EAN-8, UPC-A, EAN-13 ou GTIN-14, só números, com dígito verificador correto) e único entre os produtos. Os itens do pedido trazem `produto_sku` e `produto_codigo_barras` para a conferência na separação.

### Checklist da separação

```http
POST /api/separacoes/7/marcar-item/
Authorization: Bearer <access do separador responsável, ADMIN ou GERENTE>

{"item": 12, "separado": true}
```

Marca (ou desmarca, com `false`) um item do pedido como já separado; o estado fica em `itens[].separado`. Só vale com a separação em andamento (**409** se não) e publica `pedido.atualizado` no WebSocket. A conclusão da separação não exige todos os itens marcados (o painel é que pede isso ao separador).

## Códigos de resposta

| Código | Significado |
|--------|-------------|
| 400 | Dados inválidos (detalhes por campo) |
| 401 | Token ausente, inválido ou expirado |
| 403 | O perfil não permite a operação ou a filial é outra |
| 404 | Recurso inexistente ou fora do seu escopo |
| 409 | Regra de negócio: estoque insuficiente, produto indisponível ou transição de status inválida |
| 429 | Limite de requisições excedido; aguarde os segundos do cabeçalho `Retry-After` |

## Rate limit

Todos os endpoints têm um limite global, e os sensíveis ou custosos têm um limite próprio. Os valores podem ser ajustados no `.env` (ex.: `THROTTLE_LOGIN=10/min`).

| Escopo | Variável | Padrão | Endpoints |
|--------|----------|--------|-----------|
| anônimo | `THROTTLE_ANON` | 60/min por IP | qualquer endpoint sem login |
| usuário | `THROTTLE_USER` | 600/min por usuário | qualquer endpoint autenticado |
| login | `THROTTLE_LOGIN` | 5/min por IP | `POST /api/auth/token/` |
| jwt | `THROTTLE_JWT` | 30/min | renovar e validar token, logout |
| registro | `THROTTLE_REGISTRO` | 10/hora por IP | `POST /api/auth/registrar/` |
| pedidos_criacao | `THROTTLE_PEDIDOS_CRIACAO` | 30/min | `POST /api/pedidos/` |
| pedidos_fluxo | `THROTTLE_PEDIDOS_FLUXO` | 120/min | cancelar, iniciar separação, marcar item, concluir, despachar, finalizar |
| estoque_ajuste | `THROTTLE_ESTOQUE_AJUSTE` | 60/min | `POST /api/estoques/{id}/ajustar/` |
| upload | `THROTTLE_UPLOAD` | 20/min | `POST/DELETE /api/produtos/{id}/foto/` |
| relatorios | `THROTTLE_RELATORIOS` | 30/min | `/api/relatorios/*` |

A contagem fica no cache do Django. Sem `REDIS_URL`, cada processo conta separado e a contagem zera ao reiniciar; em produção o Redis é obrigatório e a contagem é única para toda a API.

## WebSocket

| Canal | Quem conecta | Eventos |
|-------|--------------|---------|
| `ws(s)://<host>/ws/lojas/<loja_id>/?token=<access>` | Funcionários da filial (ADMIN: qualquer filial) | `pedido.criado`, `pedido.atualizado`, `estoque.atualizado`, `estoque.abaixo_do_minimo` |
| `ws(s)://<host>/ws/notificacoes/?token=<access>` | Qualquer usuário autenticado | `pedido.criado`, `pedido.atualizado` dos próprios pedidos |

Formato das mensagens: `{"evento": "pedido.atualizado", "dados": {"pedido_id": 1, "codigo": "PED-...", "status": "SEPARADO", "tipo_entrega": "RETIRADA"}}`.

Envie `{"acao": "ping"}` para receber `{"evento": "pong"}`. A conexão é fechada com código **4401** (sem autenticação) ou **4403** (sem acesso à filial).

```js
const ws = new WebSocket(`wss://api.exemplo.com/ws/lojas/1/?token=${access}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
