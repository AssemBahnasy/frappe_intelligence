"""
commands.py
-----------
Custom bench CLI commands for frappe_intelligence.

Usage (from inside frappe-bench/):
    bench fi-setup-ollama              # install Ollama + pull qwen2.5:7b
    bench fi-setup-ollama --model llama3.2-vision:11b
    bench fi-check-deps                # print dependency status
    bench --site <site> fi-record-tutorial [--topic ask] [--lang en]
    bench --site <site> fi-tutorial-sample-data
"""

from __future__ import annotations

import subprocess
import sys

import click
from frappe.commands import get_site, pass_context

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
	svc = subprocess.run(["ollama", "list"], capture_output=True, text=True)
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
	click.echo("  Provider         = Ollama")
	click.echo("  Ollama Base URL  = http://localhost:11434")
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
	_check_python("easyocr", "Photos and scanned PDFs (optional: the ocr extra)")
	_check_python("faster_whisper", "Voice input (optional: the voice extra)")
	_check_python("openai", "OpenAI and Ollama providers")
	_check_python("anthropic", "Claude provider")
	_check_python("google.genai", "Gemini provider")
	_check_python("requests", "HTTP client (Ollama model checks)")

	_step("System tools")
	_check_binary("ffmpeg", "Audio decoding for voice input (optional)")

	_step("Ollama service")
	result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
	if result.returncode == 0:
		models = [line.split()[0] for line in result.stdout.strip().splitlines()[1:] if line.strip()]
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


# ---------------------------------------------------------------------------
# fi-record-tutorial
# ---------------------------------------------------------------------------


@click.command("fi-record-tutorial")
@click.option("--topic", "topics", multiple=True, help="A topic key; repeat for more. Default: all.")
@click.option("--lang", "languages", multiple=True, default=("en", "ar"), show_default=True)
@click.option("--first-name", default="Sara", show_default=True, help="Name the assistant greets.")
@pass_context
def record_tutorial(context, topics, languages, first_name) -> None:
	"""Record the tutorial's demo videos on a development site (docs/tutorial/videos.md)."""
	import frappe

	from frappe_intelligence.tutorial import recorder

	frappe.init(get_site(context))
	frappe.connect()
	try:
		recorder.record(list(topics), list(languages), first_name)
	finally:
		frappe.destroy()


@click.command("fi-tutorial-sample-data")
@pass_context
def tutorial_sample_data(context) -> None:
	"""Create the fictional records the demo videos show, on a development site."""
	import frappe

	from frappe_intelligence.tutorial import sample_data

	frappe.init(get_site(context))
	frappe.connect()
	try:
		sample_data.create()
	finally:
		frappe.destroy()


commands = [setup_ollama, check_deps, record_tutorial, tutorial_sample_data]
