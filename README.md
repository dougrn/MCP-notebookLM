# 📓 NotebookLM MCP Server (Python & FastMCP)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?style=for-the-badge&logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-green?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/Framework-FastMCP-purple?style=for-the-badge" alt="FastMCP" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" alt="Platform" />
</p>

Servidor **Model Context Protocol (MCP)** profissional em Python construído com **FastMCP** para conectar assistentes e agentes de IA (**Antigravity IDE, Claude Desktop, Cursor, Claude Code, Windsurf**) diretamente ao **Google NotebookLM**.

Diferente de soluções lentas baseadas em automação visual contínua (DOM/UI scraping), este servidor opera diretamente sobre as **chamadas RPC internas de alta performance do NotebookLM**, permitindo:
- Consultas RAG rápidas fundamentadas com citações.
- Gerenciamento completo de cadernos e ingestão de fontes (URLs, YouTube, documentos e textos).
- Disparo e download assíncrono de **Audio Overviews (Podcasts / Deep Dives)** e relatórios.
- Pesquisa aprofundada automatizada (**Deep Research**).
- Gerenciamento de sessão persistente com keep-alive e renovação de cookies.

---

## ⚡ Quickstart

```powershell
# 1. Clone o repositório
git clone https://github.com/dougrn/MCP-notebookLM.git
cd MCP-notebookLM

# 2. Instale e sincronize as dependências com o uv
uv sync
uv run playwright install chromium

# 3. Faça o login persistente com Master Token (não perde sessão)
uv run python login.py --master-token --account seu_email@gmail.com

# 4. Inicie o servidor MCP em modo stdio
uv run python server.py
```

---

## 🏗️ Arquitetura

```
┌────────────────────────────────────────────────────────┐
│   Clientes MCP (Claude Desktop, Cursor, Antigravity)   │
└──────────────────────────┬─────────────────────────────┘
                           │  JSON-RPC (stdio / http)
                           ▼
┌────────────────────────────────────────────────────────┐
│          NotebookLM FastMCP Server (server.py)         │
│  - 40 Ferramentas Registradas                          │
│  - Health Checking & Auth Status                       │
│  - Prompt Templates & Resources                        │
└──────────────────────────┬─────────────────────────────┘
                           │  FastMCP Lifespan & RPC Client
                           ▼
┌────────────────────────────────────────────────────────┐
│           Google NotebookLM Backend Engine             │
│  - Gemini 2.5 Grounded Session RAG                     │
│  - Source Ingestion & Parser (URLs / YouTube / Text)   │
│  - Studio Artifact Generation (Audio Overviews / .m4a) │
└────────────────────────────────────────────────────────┘
```

---

## 📦 Estrutura do Repositório

```
MCP-notebookLM/
├── server.py             # Ponto de entrada do servidor FastMCP
├── login.py              # Script CLI amigável para login e verificação de sessão
├── requirements.txt      # Dependências com versões exatas travadas
├── pyproject.toml        # Manifesto de configuração do pacote Python
├── .env.example          # Modelo de configuração de ambiente
├── .gitignore            # Regras de exclusão de artefatos
├── LICENSE               # Licença MIT
└── README.md             # Documentação oficial
```

---

## 🔑 Autenticação e Sessão Persistente

### Por que a sessão comum do Google cai rápido?
Os cookies de autenticação web do Google (`__Secure-1PSIDTS`, `OSID`) possuem um tempo de vida muito curto (poucas horas) e são rotacionados automaticamente pela nuvem sempre que você acessa o Gmail, YouTube ou fecha o navegador. Sem um **Master Token**, a biblioteca não consegue renovar esses cookies e a sessão expira.

### Solução: Login com Master Token (Durável)
Com o **Master Token**, o NotebookLM utiliza o protocolo OAuth de dispositivo do Google para re-emitir cookies atualizados em segundo plano silenciosamente (headless), garantindo que o servidor MCP permaneça conectado continuamente.

#### 1. Login Interativo (Recomendado)

```powershell
uv run python login.py --master-token --account seu_email@gmail.com
```

* No Windows, o script utiliza por padrão o **Microsoft Edge** (`--browser msedge`), evitando qualquer conflito de concorrência com o seu Google Chrome do dia a dia.
* Uma janela se abrirá para autenticação na sua conta Google e o token será salvo em `~/.notebooklm/profiles/default/master_token.json`.

#### 2. Método Alternativo via Cookie `oauth_token` (Sem abrir janela)

Caso prefira não usar automação de navegador ou o Google bloqueie o browser automatizado:
1. No seu Chrome comum, acesse [accounts.google.com/EmbeddedSetup](https://accounts.google.com/EmbeddedSetup).
2. Faça login com a sua conta Google.
3. Abra as Ferramentas do Desenvolvedor (`F12`) ➔ aba **Application** ➔ **Cookies** ➔ `accounts.google.com`.
4. Copie o valor do cookie **`oauth_token`**.
5. Execute:
   ```powershell
   uv run python login.py --master-token --account seu_email@gmail.com --oauth-token SEU_TOKEN_AQUI
   ```

### Checagem de Saúde da Sessão

Para verificar a qualquer momento se a sessão continua ativa e se o Master Token está presente:
```powershell
uv run python login.py --check
```


---

## 🔌 Configuração nos Clientes MCP

### 1. Antigravity IDE
Edite `~/.gemini/antigravity-ide/mcp_config.json` ou `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "notebooklm-python": {
      "command": "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\.venv\\Scripts\\python.exe",
      "args": [
        "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\server.py"
      ]
    }
  }
}
```

### 2. Claude Desktop
Adicione ao seu `%APPDATA%\Claude\claude_desktop_config.json` (Windows) ou `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\.venv\\Scripts\\python.exe",
      "args": [
        "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\server.py"
      ]
    }
  }
}
```

### 3. Cursor
No Cursor, configure em `.cursor/mcp.json` ou nas configurações de MCP:

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\.venv\\Scripts\\python.exe",
      "args": [
        "c:\\Users\\dougl\\Desktop\\Serviços\\_Pessoais\\MCP-notebookLM\\server.py"
      ]
    }
  }
}
```

### 4. Claude Code (CLI)
```bash
claude mcp add notebooklm -- c:/Users/dougl/Desktop/Serviços/_Pessoais/MCP-notebookLM/.venv/Scripts/python.exe c:/Users/dougl/Desktop/Serviços/_Pessoais/MCP-notebookLM/server.py
```

---

## 🧰 Catálogo de Ferramentas Disponíveis

| Categoria | Ferramenta | Descrição |
| :--- | :--- | :--- |
| **Diagnóstico & Auth** | `auth_check` | Verifica status de conexão e presença do Master Token durável |
| | `auth_reconnect` | Força renovação silenciosa de cookies via Master Token em background |
| | `auth_login` | Dispara a janela de login na tela do usuário a partir do harness |
| | `server_info` | Detalhes do servidor, versão do runtime e perfil ativo |
| **Cadernos** | `notebook_list` | Lista todos os cadernos com ID, título, contagem de fontes e datas |
| | `notebook_create` | Cria um novo caderno no NotebookLM |
| | `notebook_describe` | Detalhes aprofundados e metadados de um caderno |
| | `notebook_quick_summary` | Resumo instantâneo das fontes e perguntas sugeridas |
| | `notebook_rename` | Renomeia um caderno existente |
| | `notebook_delete` | Exclui um caderno com confirmação |
| **Fontes** | `source_list` | Lista todas as fontes indexadas no caderno |
| | `source_read` | Retorna o texto extraído de uma fonte |
| | `source_add` | Ingestão de URL web, link do YouTube ou texto bruto |
| | `source_add_drive_file` | Adiciona arquivo direto do Google Drive |
| | `source_delete` | Remove uma fonte do caderno |
| | `source_wait` | Aguarda a conclusão da indexação assíncrona da fonte |
| **Chat & RAG** | `chat_ask` | Faz perguntas ao caderno com fundamentação e citações |
| | `chat_start` | Inicia uma nova conversa persistente no caderno |
| | `chat_configure` | Configura o tom e diretrizes de resposta do chat |
| | `suggest_prompts` | Gera ideias de perguntas com base nas fontes |
| **Studio & Áudio**| `studio_generate` | Dispara geração de Audio Overview (podcast), vídeo ou quiz |
| | `studio_status` | Consulta o status de processamento da geração |
| | `studio_download` | Faz o download do arquivo de áudio (`.m4a`) gerado |
| | `studio_list` | Lista todos os artefatos de estúdio gerados |
| **Notas & Pesquisa**| `note_save` | Salva notas de pesquisa diretamente no caderno |
| | `research_start` | Inicia uma rotina de Deep Research sobre um tema |
| | `research_import` | Importa os achados da pesquisa para o caderno |

---

## 🧪 Teste Interativo com FastMCP Inspector

Para testar e interagir visualmente com as ferramentas pelo navegador:

```powershell
fastmcp dev server.py
```

---

## 📄 Licença

Este projeto está sob a licença [MIT](LICENSE).
