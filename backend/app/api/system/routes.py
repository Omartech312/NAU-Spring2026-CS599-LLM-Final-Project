"""
System info API: local IP address detection and CLI tool status.
"""
import subprocess
import socket
import shutil
from flask import Blueprint, jsonify

system_bp = Blueprint("system", __name__, url_prefix="/api/system")


def get_local_ip() -> str:
    """Detect the machine's local IPv4 address."""
    try:
        # Method 1: connect to an external host (Google DNS) to determine routing IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    try:
        # Method 2: macOS
        result = subprocess.run(
            ["ipconfig", "getifaddr", "en0"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    try:
        # Method 3: Linux
        result = subprocess.run(
            ["hostname", "-I"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split()[0]
    except Exception:
        pass

    return "127.0.0.1"


def _detect_cli(name: str, cmd: list[str], version_args: list[str], install_hint: str) -> dict:
    """Detect a CLI tool: check if it's on PATH, get version, return status dict."""
    found = shutil.which(cmd[0]) is not None
    version = "unknown"
    error = None

    if found:
        try:
            result = subprocess.run(
                cmd + version_args,
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                version = result.stdout.strip().split("\n")[0].strip()
            else:
                error = result.stderr.strip().split("\n")[0] if result.stderr else "no output"
        except subprocess.TimeoutExpired:
            error = "command timed out"
        except Exception as e:
            error = str(e)

    return {
        "name": name,
        "found": found,
        "version": version if found else None,
        "error": error if found else None,
        "install_hint": install_hint if not found else None,
    }


@system_bp.route("/info", methods=["GET"])
def get_system_info():
    """
    Return system info: local IP, hostname, etc.
    """
    local_ip = get_local_ip()
    hostname = socket.gethostname()

    return jsonify({
        "local_ip": local_ip,
        "hostname": hostname,
        "frontend_url": f"http://{local_ip}:3000",
        "backend_url": f"http://{local_ip}:5001",
    }), 200


@system_bp.route("/cli-test", methods=["POST"])
def test_cli():
    """
    Run a quick test query against Claude CLI or Codex CLI.
    Body: { "cli": "claude" | "codex", "question": "..." }
    Returns the model's answer and latency.
    """
    from flask import request
    from app.services.claude_service import query_claude
    from app.services.codex_service import query_codex

    data = request.get_json() or {}
    cli = data.get("cli", "").lower()
    question = data.get("question", "What is 2+2?").strip()

    if cli not in ("claude", "codex"):
        return jsonify({"error": "cli must be 'claude' or 'codex'"}), 400

    if not shutil.which(cli):
        return jsonify({"error": f"{cli} is not installed or not on PATH"}), 424

    test_context = (
        "Context: [1] The sum of 2 and 2 is 4. "
        "[2] Addition is a basic arithmetic operation."
    )

    try:
        if cli == "claude":
            result = query_claude(
                context=test_context,
                question=question,
                model="claude-opus-4-6",
                timeout=60,
            )
        else:
            result = query_codex(
                context=test_context,
                question=question,
                timeout=60,
            )
        return jsonify({
            "cli": cli,
            "question": question,
            "model_name": result.get("model_name"),
            "answer_text": result.get("answer_text"),
            "latency_ms": round(result.get("latency_ms", 0)),
            "tokens_used": result.get("tokens_used", 0),
            "success": result.get("success", False),
            "error": result.get("error"),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e), "cli": cli, "success": False}), 500


@system_bp.route("/cli-status", methods=["GET"])
def get_cli_status():
    """
    Detect availability of Claude CLI and Codex CLI.

    Returns per-CLI status:
      - found: bool
      - version: string (if found)
      - error: string (if found but version check failed)
      - install_hint: string (if not found)
    """
    clis = [
        _detect_cli(
            name="Claude CLI",
            cmd=["claude"],
            version_args=["--version"],
            install_hint=(
                "npm install -g @anthropic/claude-code  # or: brew install claude-code"
            ),
        ),
        _detect_cli(
            name="Codex CLI",
            cmd=["codex"],
            version_args=["--version"],
            install_hint=(
                "OpenAI Codex CLI — see https://github.com/openai/codex or "
                "install via: npm install -g @openai/codex"
            ),
        ),
    ]

    return jsonify({
        "clis": clis,
        "all_available": all(c["found"] for c in clis),
    }), 200


# Map CLI name → (install commands by platform, binary name)
_CLI_INSTALL_DEFS = {
    "claude": {
        "darwin": ["brew install claude-code"],
        "linux": ["npm install -g @anthropic/claude-code"],
        "windows": ["npm install -g @anthropic/claude-code"],
        "binary": "claude",
    },
    "codex": {
        "darwin": ["npm install -g @openai/codex"],
        "linux": ["npm install -g @openai/codex"],
        "windows": ["npm install -g @openai/codex"],
        "binary": "codex",
    },
}


def _get_install_cmds(cli: str) -> list[str]:
    """Return platform-appropriate install commands for a CLI."""
    import platform
    system = platform.system().lower()  # Darwin | Linux | Windows
    if cli not in _CLI_INSTALL_DEFS:
        return []
    defn = _CLI_INSTALL_DEFS[cli]
    # Try exact match first, then fallback to linux
    cmds = defn.get(system, defn.get("linux", []))
    if isinstance(cmds, str):
        cmds = [cmds]
    return cmds


@system_bp.route("/cli-install", methods=["POST"])
def install_cli():
    """
    Install a CLI tool by running its platform-appropriate install command.
    Body: { "cli": "claude" | "codex" }
    Runs the install command asynchronously and returns immediately.
    The frontend should poll /cli-status after a few seconds to verify.
    """
    from flask import request

    data = request.get_json() or {}
    cli = data.get("cli", "").lower()

    if cli not in _CLI_INSTALL_DEFS:
        return jsonify({
            "error": "cli must be 'claude' or 'codex'",
            "cli": cli,
        }), 400

    # Already installed?
    if shutil.which(cli):
        return jsonify({
            "cli": cli,
            "status": "already_installed",
            "message": f"{cli} is already installed.",
        }), 200

    cmds = _get_install_cmds(cli)
    if not cmds:
        return jsonify({
            "cli": cli,
            "error": f"No install command known for platform {platform.system()}",
        }), 400

    # Detect which command is likely to work (prefer brew if on macOS)
    import platform as _platform
    chosen_cmd = cmds[0]
    if _platform.system() == "Darwin" and len(cmds) > 1:
        chosen_cmd = cmds[1]  # npm version for macOS (brew needs separate formula)

    try:
        proc = subprocess.Popen(
            chosen_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return jsonify({
            "cli": cli,
            "status": "installing",
            "command": chosen_cmd,
            "pid": proc.pid,
            "message": (
                f"Install started. Run `make status` or refresh after 30s "
                "to check if {cli} was installed successfully."
            ),
        }), 202
    except Exception as e:
        return jsonify({
            "cli": cli,
            "error": str(e),
            "install_command": chosen_cmd,
        }), 500
