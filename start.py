"""
start.py  —  Lanceur du projet Reconstruction IA
=================================================
Usage :  python start.py
         python start.py --no-browser   (ne pas ouvrir le navigateur)
         python start.py --port 8080    (port personnalisé)
=================================================
"""

import os
import sys
import time
import socket
import argparse
import webbrowser
import subprocess
import platform

# ── Project root & virtual-env Python ───────────────────────────────────────
ROOT    = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, "paddle_env", "Scripts", "python.exe")
PYTHON  = VENV_PY if os.path.exists(VENV_PY) else sys.executable

# ── ANSI colors (works on Windows 10 + PowerShell / CMD with VT support) ────
def _enable_color():
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception:
            return False
    return True

USE_COLOR = _enable_color()

def _c(text, code):  return f"\033[{code}m{text}\033[0m" if USE_COLOR else text
def bold(t):   return _c(t, "1")
def cyan(t):   return _c(t, "36")
def green(t):  return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")
def dim(t):    return _c(t, "2")

# ── Banner ───────────────────────────────────────────────────────────────────
def print_banner(port):
    url = f"http://localhost:{port}"
    print()
    print(cyan("  ╔══════════════════════════════════════════════════════╗"))
    print(cyan("  ║") + bold("   🤖  Reconstruction IA — Documents Administratifs   ") + cyan("║"))
    print(cyan("  ║") + dim("         PaddleOCR 2.7  ·  Flask  ·  Python           ") + cyan("║"))
    print(cyan("  ╚══════════════════════════════════════════════════════╝"))
    print()
    print(f"  {bold('Python  :')} {dim(PYTHON)}")
    print(f"  {bold('URL     :')} {green(url)}")
    print(f"  {bold('Arrêt   :')} {yellow('Ctrl+C')}")
    print()

# ── Wait for the server to be ready ─────────────────────────────────────────
def wait_for_server(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.4)
    return False

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lance le serveur web Reconstruction IA")
    parser.add_argument("--port",       type=int, default=5000, help="Port HTTP (défaut: 5000)")
    parser.add_argument("--no-browser", action="store_true",    help="Ne pas ouvrir le navigateur")
    args = parser.parse_args()

    print_banner(args.port)

    # Set PORT env var so web/app.py can pick it up
    env = os.environ.copy()
    env["FLASK_PORT"] = str(args.port)

    cmd = [PYTHON, "-c",
           f"import os,sys; sys.path.insert(0,r'{ROOT}'); "
           f"from web.app import app; "
           f"app.run(debug=False, host='0.0.0.0', port={args.port}, use_reloader=False)"]

    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env)
    except FileNotFoundError:
        print(red(f"\n  ✗  Python introuvable : {PYTHON}"))
        print(dim("     Assurez-vous que paddle_env/ existe.\n"))
        sys.exit(1)

    print(dim("  ⏳  Démarrage du serveur …"), end="", flush=True)

    if wait_for_server(args.port):
        url = f"http://localhost:{args.port}"
        print(f"\r  {green('✔  Serveur prêt')}  →  {bold(url)}           ")
        print()
        if not args.no_browser:
            webbrowser.open(url)
    else:
        print(f"\r  {yellow('⚠  Le serveur tarde à répondre — vérifiez la console.')}  ")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print(yellow("\n\n  [arrêt demandé — au revoir !]\n"))
        proc.terminate()

if __name__ == "__main__":
    main()
