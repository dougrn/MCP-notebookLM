"""Servidor MCP em Python para conexão com o Google NotebookLM.

Construído utilizando FastMCP e o SDK oficial do Model Context Protocol,
integrado com o motor RPC do Google NotebookLM.

Como executar:
    python server.py                  # Executa no modo stdio (padrão para clientes MCP)
    python server.py --transport http # Executa servidor HTTP local
    fastmcp dev server.py             # Abre a interface interativa FastMCP Inspector
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from notebooklm import NotebookLMClient
from notebooklm.mcp.server import create_server as create_base_server
from notebooklm.paths import get_master_token_path, get_storage_path

# Carrega variáveis de ambiente do .env caso exista
load_dotenv()


def check_auth_status(profile: str | None = None) -> dict[str, Any]:
    """Inspeciona o arquivo de credenciais e a presença de Master Token."""
    storage_path = get_storage_path(profile=profile)
    master_token_path = get_master_token_path(profile=profile)

    storage_exists = storage_path.exists()
    master_token_exists = master_token_path.exists()

    return {
        "authenticated": storage_exists,
        "master_token": master_token_exists,
        "storage_path": str(storage_path),
        "master_token_path": str(master_token_path),
        "message": (
            "Credenciais locais encontradas (Sessão com Master Token durável)."
            if master_token_exists
            else (
                "Credenciais locais encontradas (Apenas cookies voláteis - execute 'python login.py' para Master Token durável)."
                if storage_exists
                else "Credenciais locais ausentes. Execute 'python login.py' para autenticar no Google."
            )
        ),
    }


def build_server(profile: str | None = None) -> FastMCP:
    """Cria e configura a instância do servidor FastMCP com ferramentas do NotebookLM."""
    # Inicializa o servidor base que gerencia o ciclo de vida do cliente e keep-alive
    server = create_base_server(profile=profile)

    # Ferramenta auxiliar de verificação rápida de integridade da autenticação
    @server.tool(name="auth_check")
    async def auth_check() -> dict[str, Any]:
        """Verifica se a autenticação com o Google NotebookLM está configurada e válida."""
        status = check_auth_status(profile=profile)
        if not status["authenticated"]:
            return {
                "status": "unauthenticated",
                "master_token": False,
                "message": (
                    "Autenticação não configurada. "
                    "Abra o terminal neste projeto e execute 'python login.py' para fazer o login no Google."
                ),
                "storage_path": status["storage_path"],
            }

        try:
            async with NotebookLMClient.from_storage(profile=profile) as client:
                notebooks = await client.notebooks.list()
                return {
                    "status": "authenticated",
                    "master_token": status["master_token"],
                    "storage_path": status["storage_path"],
                    "total_notebooks": len(notebooks),
                    "active_account": await client.get_account_email(),
                    "message": "Autenticação ativa e conectada ao NotebookLM com sucesso.",
                }
        except Exception as exc:
            return {
                "status": "expired_or_error",
                "master_token": status["master_token"],
                "storage_path": status["storage_path"],
                "error": str(exc),
                "message": (
                    "A sessão expirou. Execute 'python login.py' no terminal para autenticar com Master Token durável."
                    if not status["master_token"]
                    else f"Erro ao validar sessão com Master Token: {exc}. Tente chamar 'auth_reconnect'."
                ),
            }

    # Ferramenta de reconexão / re-emissão de cookies em background
    @server.tool(name="auth_reconnect")
    async def auth_reconnect() -> dict[str, Any]:
        """Tenta reconectar a sessão do NotebookLM re-emitindo cookies a partir do Master Token."""
        status = check_auth_status(profile=profile)
        if not status["master_token"]:
            return {
                "status": "manual_action_required",
                "master_token": False,
                "message": (
                    "Não há um Master Token configurado. Cookies voláteis do Google não podem ser "
                    "renovados de forma autônoma pela IA. O usuário precisa executar no terminal: "
                    "'python login.py' para salvar o Master Token durável."
                ),
            }

        try:
            from notebooklm._auth.master_token import remint_from_stored_token

            storage_path = Path(status["storage_path"])
            await remint_from_stored_token(storage_path)

            async with NotebookLMClient.from_storage(profile=profile) as client:
                notebooks = await client.notebooks.list()
                return {
                    "status": "reconnected",
                    "master_token": True,
                    "total_notebooks": len(notebooks),
                    "active_account": await client.get_account_email(),
                    "message": "Sessão renovada com sucesso em segundo plano via Master Token!",
                }
        except Exception as exc:
            return {
                "status": "error",
                "master_token": True,
                "error": str(exc),
                "message": f"Falha ao re-emitir credenciais: {exc}. Execute 'python login.py' para reautenticar.",
            }

    # Ferramenta para abrir a janela de autenticação interativa na tela do usuário
    @server.tool(name="auth_login")
    async def auth_login(browser: str = "chrome") -> dict[str, Any]:
        """Abre uma nova janela no desktop do usuário para autenticação interativa no Google.

        Esta ferramenta não bloqueia o harness: ela dispara a janela do navegador desanexada
        e retorna imediatamente para que a IA possa pedir ao usuário para concluir o login.
        """
        python_exe = sys.executable
        script_path = Path(__file__).parent / "login.py"

        try:
            creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            proc = subprocess.Popen(
                [python_exe, str(script_path), "--browser", browser],
                creationflags=creationflags,
            )
            return {
                "status": "login_window_opened",
                "pid": proc.pid,
                "browser": browser,
                "message": (
                    "A janela de login do Google (com Master Token persistente) foi aberta na tela do usuário. "
                    "Peça ao usuário para realizar o login na janela aberta. "
                    "Assim que ele concluir, utilize a ferramenta 'auth_check' para confirmar a conexão."
                ),
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "message": (
                    f"Não foi possível abrir a janela automaticamente: {exc}. "
                    "Peça ao usuário para executar 'python login.py' manualmente no terminal."
                ),
            }

    # Ferramenta de resumo rápido de um caderno
    @server.tool(name="notebook_quick_summary")
    async def notebook_quick_summary(notebook_id: str) -> dict[str, Any]:
        """Obtém resumo rápido de um caderno, incluindo lista de fontes e tópicos sugeridos.

        Args:
            notebook_id: ID do caderno no NotebookLM.
        """
        async with NotebookLMClient.from_storage(profile=profile) as client:
            nb = await client.notebooks.get(notebook_id)
            sources = await client.sources.list(notebook_id)
            prompts = []
            try:
                prompts = await client.chat.suggest_prompts(notebook_id)
            except Exception:
                pass

            return {
                "id": nb.id,
                "title": getattr(nb, "title", "Sem título"),
                "source_count": len(sources),
                "sources": [
                    {
                        "id": getattr(s, "id", ""),
                        "title": getattr(s, "title", "Sem título"),
                        "type": str(getattr(s, "type", "unknown")),
                    }
                    for s in sources
                ],
                "suggested_prompts": [str(p) for p in prompts[:5]],
            }

    # Prompt para orientar pesquisas no caderno
    @server.prompt(name="research_notebook")
    def research_notebook(notebook_id: str, topic: str) -> str:
        """Gera um prompt instruindo o modelo a conduzir uma pesquisa estruturada no caderno."""
        return (
            f"Por favor, use o caderno com ID '{notebook_id}' para pesquisar profundamente sobre o tópico '{topic}'.\n"
            "Diretrizes:\n"
            "1. Utilize a ferramenta 'chat_ask' para realizar consultas fundamentadas nas fontes adicionadas.\n"
            "2. Cite as fontes e trechos originais retornados.\n"
            "3. Se faltar informação relevante, sugira novas fontes a serem adicionadas com 'source_add'.\n"
            "4. Organize os achados em formato executivo com pontos-chave e conclusões."
        )

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor FastMCP para Google NotebookLM")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Tipo de transporte MCP (padrão: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host para modo HTTP (padrão: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8000)),
        help="Porta para modo HTTP (padrão: 8000)",
    )
    parser.add_argument(
        "--profile",
        default=os.environ.get("NOTEBOOKLM_PROFILE", None),
        help="Perfil de autenticação do NotebookLM (padrão: default)",
    )

    args = parser.parse_args()

    # Informa no stderr se a autenticação não estiver pronta
    auth_info = check_auth_status(profile=args.profile)
    if not auth_info["authenticated"]:
        sys.stderr.write(
            "[AVISO] Credenciais do NotebookLM não encontradas em "
            f"{auth_info['storage_path']}.\n"
            "Execute 'python login.py' para autenticar com sua conta Google.\n"
        )
    elif not auth_info["master_token"]:
        sys.stderr.write(
            "[AVISO] Sessão configurada apenas com cookies voláteis.\n"
            "Recomendado executar 'python login.py' para salvar o Master Token e evitar perda de conexão.\n"
        )

    server = build_server(profile=args.profile)

    if args.transport == "http":
        print(f"[*] Iniciando servidor MCP NotebookLM em http://{args.host}:{args.port}")
        server.run(transport="http", host=args.host, port=args.port)
    else:
        # stdio é o formato padrão esperado por Claude Desktop, Cursor e Antigravity
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
