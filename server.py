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
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from notebooklm import NotebookLMClient
from notebooklm.mcp.server import create_server as create_base_server
from notebooklm.paths import get_storage_path


def check_auth_status() -> dict[str, Any]:
    """Inspeciona o arquivo de credenciais de autenticação local."""
    storage_path = get_storage_path()
    exists = os.path.exists(storage_path)

    return {
        "authenticated": exists,
        "storage_path": str(storage_path),
        "message": (
            "Credenciais locais encontradas."
            if exists
            else "Credenciais locais ausentes. Execute 'python login.py' para autenticar no Google."
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
        status = check_auth_status()
        if not status["authenticated"]:
            return {
                "status": "unauthenticated",
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
                    "storage_path": status["storage_path"],
                    "total_notebooks": len(notebooks),
                    "active_account": await client.get_account_email(),
                    "message": "Autenticação ativa e conectada ao NotebookLM com sucesso.",
                }
        except Exception as exc:
            return {
                "status": "expired_or_error",
                "storage_path": status["storage_path"],
                "error": str(exc),
                "message": (
                    "A sessão expirou ou é inválida. "
                    "Execute 'python login.py' para renovar os cookies do Google."
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
        default="127.0.0.1",
        help="Host para modo HTTP (padrão: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Porta para modo HTTP (padrão: 8000)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Perfil de autenticação do NotebookLM (padrão: default)",
    )

    args = parser.parse_args()

    # Informa no stderr se a autenticação não estiver pronta
    auth_info = check_auth_status()
    if not auth_info["authenticated"]:
        sys.stderr.write(
            "[AVISO] Credenciais do NotebookLM não encontradas em "
            f"{auth_info['storage_path']}.\n"
            "Execute 'python login.py' para autenticar com sua conta Google.\n"
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
