"""Script auxiliar de autenticação com o Google NotebookLM.

Executa o fluxo de login via Google Chrome utilizando um PERFIL PERSISTENTE
em `~/.notebooklm/profiles/default/browser_profile`.

Com o perfil persistente, o Chrome salva sua conta e credenciais:
você faz o login uma vez e não precisa ficar digitando usuário e senha toda vez.

Como usar:
    python login.py                  # Abre o Chrome com Perfil Persistente (Recomendado)
    python login.py --browser msedge # Usa o Microsoft Edge com perfil persistente
    python login.py --check          # Verifica o status da autenticação atual
    python login.py --cookies chrome # Extrai cookies do Chrome local
    python login.py --force          # Limpa o perfil do navegador e força novo login
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path


def detect_saved_account() -> str | None:
    """Tenta detectar a conta Google salva anteriormente."""
    try:
        from notebooklm.paths import get_storage_path
        from notebooklm._auth.storage import get_account_email_for_storage

        return get_account_email_for_storage(get_storage_path())
    except Exception:
        return None


def get_default_browser() -> str:
    """Detecta o navegador instalado para evitar o Chromium genérico do Playwright."""
    chrome_path = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    edge_path = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    if chrome_path.exists():
        return "chrome"
    if edge_path.exists():
        return "msedge"
    return "chromium"


def check_current_auth(verbose: bool = True) -> bool:
    """Verifica se as credenciais atuais são válidas."""
    from notebooklm.paths import get_storage_path, get_browser_profile_dir

    storage_path = get_storage_path()
    browser_profile = get_browser_profile_dir()

    if not storage_path.exists():
        if verbose:
            print(f"[!] Arquivo de autenticação não encontrado em: {storage_path}")
        return False

    if verbose:
        print(f"[*] Inspecionando credenciais em: {storage_path}")
        print(f"[*] Perfil do navegador: {browser_profile} ({'Existe' if browser_profile.exists() else 'Novo'})")

    try:
        from notebooklm import NotebookLMClient

        async def _test():
            async with NotebookLMClient.from_storage() as client:
                notebooks = await client.notebooks.list()
                if verbose:
                    account = getattr(client, "active_account", None) or detect_saved_account() or "Conta Google"
                    print(f"\n[OK] Conexão ativa com sucesso para: {account}")
                    print(f"[OK] Total de cadernos acessíveis: {len(notebooks)}")
                    for nb in notebooks[:5]:
                        title = getattr(nb, "title", "Sem título")
                        nb_id = getattr(nb, "id", "")
                        print(f"   - {title} (ID: {nb_id})")
                return True

        return asyncio.run(_test())
    except Exception as exc:
        if verbose:
            print(f"[!] Credenciais expiradas ou inválidas: {exc}")
        return False


def run_login(
    browser: str = "chrome",
    read_cookies: str | None = None,
    use_master_token: bool = False,
    account_email: str | None = None,
    force: bool = False,
    cdp_url: str | None = None,
    oauth_token: str | None = None,
) -> bool:
    """Dispara o processo de login do NotebookLM."""
    python_exe = sys.executable

    if read_cookies:
        print("=" * 65)
        print("Importando Cookies do Navegador Local")
        print("=" * 65)
        cmd = [python_exe, "-m", "notebooklm", "login", "--browser-cookies", read_cookies]
        if account_email:
            cmd.extend(["--account", account_email])
    elif use_master_token or oauth_token or cdp_url:
        email = account_email or detect_saved_account() or "doug.americo@gmail.com"
        print("=" * 65)
        print("Autenticação via Master Token (Headless)")
        print("=" * 65)
        cmd = [
            python_exe,
            "-m",
            "notebooklm",
            "login",
            "--master-token",
            "--account",
            email,
        ]
        if cdp_url:
            cmd.extend(["--cdp-url", cdp_url])
        elif oauth_token:
            cmd.extend(["--oauth-token", oauth_token])
        else:
            cmd.extend(["--browser", browser])

        if force:
            cmd.append("--force")
    else:
        from notebooklm.paths import get_browser_profile_dir

        browser_profile = get_browser_profile_dir()
        print("=" * 65)
        print("Autenticação com Perfil Persistente do Chrome")
        print("=" * 65)
        print(f"[*] Perfil do navegador: {browser_profile}")
        print("[*] As credenciais do Google ficam salvas neste perfil permanente.")
        print("[*] Uma vez logado, você não precisará redigitar login e senha!")
        print(f"[*] Abrindo o {browser.upper()}...")
        print("=" * 65)

        cmd = [python_exe, "-m", "notebooklm", "login", "--browser", browser]
        if force:
            cmd.append("--fresh")

    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\n[OK] Processo de login concluído com sucesso!")
            return check_current_auth(verbose=True)
        else:
            print(f"\n[ERRO] O comando de login retornou código {result.returncode}")
            return False
    except KeyboardInterrupt:
        print("\n[!] Operação cancelada pelo usuário.")
        return False
    except Exception as exc:
        print(f"\n[ERRO] Falha ao executar login: {exc}")
        return False


def main():
    default_browser = get_default_browser()

    parser = argparse.ArgumentParser(
        description="Autenticação com Google NotebookLM usando perfil persistente do Chrome."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica se o login atual está ativo",
    )
    parser.add_argument(
        "--browser",
        choices=["chrome", "msedge", "chromium"],
        default=None,
        help="Navegador a ser aberto para login (padrão: chromium para master-token, ou navegador do sistema)",
    )
    parser.add_argument(
        "--cookies",
        choices=["chrome", "edge", "brave", "firefox"],
        default=None,
        help="Extrair cookies de sessão diretamente do navegador instalado",
    )
    parser.add_argument(
        "--master-token",
        action="store_true",
        help="Tenta autenticar com Master Token em vez do perfil persistente",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="E-mail da conta Google",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Limpa o perfil do navegador e força novo login",
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default=None,
        help="Conecta a um Chrome já aberto com --remote-debugging-port (ex: http://localhost:9222)",
    )
    parser.add_argument(
        "--oauth-token",
        type=str,
        default=None,
        help="Token de uso único obtido do cookie oauth_token em accounts.google.com/EmbeddedSetup",
    )

    args = parser.parse_args()

    if args.check:
        success = check_current_auth(verbose=True)
        sys.exit(0 if success else 1)

    # Se já estiver autenticado e não forçado:
    if not args.force and check_current_auth(verbose=False):
        print("\n[INFO] Você já possui uma sessão ativa e válida do NotebookLM!")
        try:
            resp = input("Deseja abrir o navegador para trocar de conta? (s/N): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
        if resp not in ("s", "sim", "y", "yes"):
            print("Login mantido. Pronto para usar!")
            sys.exit(0)

    chosen_browser = args.browser or ("msedge" if args.master_token else default_browser)

    success = run_login(
        browser=chosen_browser,
        read_cookies=args.cookies,
        use_master_token=args.master_token,
        account_email=args.account,
        force=args.force,
        cdp_url=args.cdp_url,
        oauth_token=args.oauth_token,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
