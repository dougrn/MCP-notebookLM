"""Script auxiliar de autenticação com o Google NotebookLM.

Executa o fluxo de login via navegador e salva os cookies de sessão
em `~/.notebooklm/profiles/default/storage_state.json`.

Como usar:
    python login.py                  # Abre navegador Playwright para login
    python login.py --browser chrome # Usa o Google Chrome instalado
    python login.py --browser msedge # Usa o Microsoft Edge
    python login.py --cookies chrome # Extrai cookies do Chrome local
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path


def check_current_auth() -> bool:
    """Verifica se as credenciais atuais são válidas."""
    storage_path = Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"
    if not storage_path.exists():
        print(f"[!] Arquivo de autenticação não encontrado em: {storage_path}")
        return False

    print(f"[*] Verificando credenciais existentes em: {storage_path}...")
    try:
        from notebooklm import NotebookLMClient

        async def _test():
            async with NotebookLMClient.from_storage() as client:
                notebooks = await client.notebooks.list()
                print(f"[OK] Autenticação válida! Total de notebooks na conta: {len(notebooks)}")
                for nb in notebooks[:5]:
                    title = getattr(nb, "title", "Sem título")
                    nb_id = getattr(nb, "id", "")
                    print(f"   - {title} (ID: {nb_id})")
                return True

        return asyncio.run(_test())
    except Exception as exc:
        print(f"[!] Credenciais existentes expiraram ou são inválidas: {exc}")
        return False


def run_login(browser: str = "chromium", read_cookies: str | None = None) -> bool:
    """Dispara o processo de login do NotebookLM."""
    print("=" * 60)
    print("Autenticação Google NotebookLM")
    print("=" * 60)

    python_exe = sys.executable

    if read_cookies:
        print(f"[*] Tentando importar cookies diretamente do navegador '{read_cookies}'...")
        cmd = [python_exe, "-m", "notebooklm", "login", "--browser-cookies", read_cookies]
    else:
        print(f"[*] Abrindo janela do navegador ({browser}) para login na sua conta Google...")
        print("[*] Faça o login no Google na janela que abrir. Os cookies serão salvos automaticamente!")
        cmd = [python_exe, "-m", "notebooklm", "login", "--browser", browser]

    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("[OK] Processo de login concluído!")
            return check_current_auth()
        else:
            print(f"[ERRO] O comando de login retornou código {result.returncode}")
            return False
    except KeyboardInterrupt:
        print("\n[!] Operação cancelada pelo usuário.")
        return False
    except Exception as exc:
        print(f"[ERRO] Falha ao executar login: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Autenticação com Google NotebookLM para o servidor MCP.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Apenas verifica se o login atual está ativo",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "chrome", "msedge"],
        default="chromium",
        help="Navegador a ser aberto para login (padrão: chromium)",
    )
    parser.add_argument(
        "--cookies",
        choices=["chrome", "edge", "brave", "firefox"],
        default=None,
        help="Extrair cookies de sessão diretamente do navegador instalado",
    )

    args = parser.parse_args()

    if args.check:
        success = check_current_auth()
        sys.exit(0 if success else 1)

    # Se já estiver autenticado e o usuário não forçou, avisa antes
    if check_current_auth():
        print("\n[INFO] Você já possui uma sessão ativa válida do NotebookLM!")
        resp = input("Deseja fazer login novamente para trocar de conta? (s/N): ").strip().lower()
        if resp not in ("s", "sim", "y", "yes"):
            print("Login mantido. Pronto para usar!")
            sys.exit(0)

    success = run_login(browser=args.browser, read_cookies=args.cookies)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
