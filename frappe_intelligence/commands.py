"""
commands.py
-----------
Custom bench CLI commands for frappe_intelligence.

Usage (from inside frappe-bench/):
    bench fi-setup-ollama              # install Ollama + pull qwen2.5:7b
    bench fi-setup-ollama --model llama3.2-vision:11b
    bench fi-check-deps                # print dependency status
"""
from __future__ import annotations

import subprocess
import sys

import click


# ---------------------------------------------------------------------------
# fi-setup-ollama
# ---------------------------------------------------------------------------

@click.command("fi-setup-ollama")
@click.option(
    "--model",
    default="qwen2.5:7b",
    show_default=True,
    help="Ollama model to pull after installation.",
)
@click.option(
    "--skip-install",
    is_flag=True,
    default=False,
    help="Skip Ollama binary installation (just pull the model).",
)
def setup_ollama(model: str, skip_install: bool) -> None:
    """
    Install Ollama on this server and pull the default VLM model.

    Requires root / sudo access.  Not supported on Frappe Cloud
    (managed environment — use Claude instead).
    """
    # Guard: only makes sense on Linux / macOS
    if sys.platform.startswith("win"):
        click.echo("Ollama installation is not supported on Windows.", err=True)
        raise SystemExit(1)

    if not skip_install:
        _step("Checking for Ollama binary")
        result = subprocess.run(["which", "ollama"], capture_output=True)

        if result.returncode == 0:
            ollama_path = result.stdout.decode().strip()
            click.echo(f"  ✓ Ollama already installed at {ollama_path}")
        else:
            _step("Installing Ollama via official install script")
            click.echo("  Running: curl -fsSL https://ollama.com/install.sh | sh")
            click.echo("  (This requires sudo and an internet connection)")
            try:
                subprocess.run(
                    "curl -fsSL https://ollama.com/install.sh | sh",
                    shell=True,
                    check=True,
                )
                click.echo("  ✓ Ollama installed")
            except subprocess.CalledProcessError as exc:
                click.echo(f"  ✗ Installation failed: {exc}", err=True)
                click.echo(
                    "  Try installing manually: https://ollama.com/download",
                    err=True,
                )
                raise SystemExit(1) from exc

    _step("Checking Ollama service")
    svc = subprocess.run(
        ["ollama", "list"], capture_output=True, text=True
    )
    if svc.returncode != 0:
        click.echo("  Ollama is not running. Starting it…")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        time.sleep(3)
    else:
        click.echo("  ✓ Ollama service is running")

    _step(f"Pulling model: {model}")
    click.echo("  This may take several minutes on first run (~4 GB download).")
    try:
        subprocess.run(["ollama", "pull", model], check=True)
        click.echo(f"  ✓ Model '{model}' is ready")
    except subprocess.CalledProcessError as exc:
        click.echo(f"  ✗ Pull failed for model '{model}'.", err=True)
        click.echo("", err=True)
        click.echo("  Known working models (pick one and retry with --model):", err=True)
        click.echo("    qwen2.5:7b          — Arabic/English, JSON-structured output (recommended)", err=True)
        click.echo("    llava:7b            — Vision-language, lighter on RAM", err=True)
        click.echo("    llama3.2-vision:11b — Meta vision model, high accuracy", err=True)
        click.echo("    minicpm-v:8b        — Compact vision model", err=True)
        click.echo("", err=True)
        click.echo("  Example: bench fi-setup-ollama --skip-install --model llava:7b", err=True)
        raise SystemExit(1) from exc

    click.echo("")
    click.echo("All done! Now open AI Settings in Frappe desk and set:")
    click.echo(f"  Provider         = Ollama")
    click.echo(f"  Ollama Base URL  = http://localhost:11434")
    click.echo(f"  Ollama Model     = {model}")


# ---------------------------------------------------------------------------
# fi-check-deps
# ---------------------------------------------------------------------------

@click.command("fi-check-deps")
def check_deps() -> None:
    """
    Print a dependency status report for frappe_intelligence.

    Checks Python packages, system tools, and Ollama availability.
    """
    _step("Python packages")
    _check_python("pypdf", "PDF text extraction")
    _check_python("easyocr", "Image OCR (Arabic + English)")
    _check_python("faster_whisper", "Voice transcription")
    _check_python("anthropic", "Claude API provider")
    _check_python("requests", "HTTP client (Ollama adapter)")

    _step("System tools")
    _check_binary("ffmpeg", "Audio decoding for Faster-Whisper")

    _step("Ollama service")
    result = subprocess.run(
        ["ollama", "list"], capture_output=True, text=True
    )
    if result.returncode == 0:
        models = [
            line.split()[0]
            for line in result.stdout.strip().splitlines()[1:]
            if line.strip()
        ]
        if models:
            click.echo(f"  ✓ Ollama running — models: {', '.join(models)}")
        else:
            click.echo("  ⚠  Ollama running but no models pulled yet")
            click.echo("     Run: bench fi-setup-ollama")
    else:
        click.echo("  ✗ Ollama not running or not installed")
        click.echo("     Run: bench fi-setup-ollama  (self-hosted only)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step(title: str) -> None:
    click.echo(f"\n{click.style(title, bold=True)}")


def _check_python(package: str, description: str) -> None:
    try:
        __import__(package)
        click.echo(f"  ✓ {package:<20} {description}")
    except ImportError:
        click.echo(f"  ✗ {package:<20} {description}  ← missing")


def _check_binary(binary: str, description: str) -> None:
    result = subprocess.run(["which", binary], capture_output=True)
    if result.returncode == 0:
        click.echo(f"  ✓ {binary:<20} {description}")
    else:
        click.echo(f"  ✗ {binary:<20} {description}  ← not found")


commands = [setup_ollama, check_deps]
