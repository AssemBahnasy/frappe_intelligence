"""
install.py
----------
Post-installation hook for frappe_intelligence.

Runs automatically after `bench install-app frappe_intelligence`.
Seeds built-in document templates, default document requirements, and
prints a post-install checklist so the admin knows exactly what still
needs to be configured manually.
"""
from __future__ import annotations

import importlib
import subprocess

import frappe


def after_install() -> None:
    from frappe_intelligence.utils.requirement_seeder import seed_requirements

    seed_requirements()          # no-op by default; integrating apps add entries

    frappe.msgprint(
        frappe._(
            "Frappe Intelligence installed. "
            "Open AI Settings to configure your AI provider (Ollama or Claude). "
            "Run  bench fi-check-deps  to verify dependencies."
        )
    )

    _print_checklist()


# ---------------------------------------------------------------------------
# Post-install checklist
# ---------------------------------------------------------------------------

def _print_checklist() -> None:
    """
    Print a dependency + configuration checklist to the bench log so the
    admin can see at a glance what is ready and what still needs attention.
    """
    lines: list[str] = [
        "",
        "=" * 60,
        "  Frappe Intelligence — Post-Install Checklist",
        "=" * 60,
    ]

    # Python packages
    lines.append("\nPython packages:")
    for pkg, label in [
        ("pypdf",         "PDF text extraction"),
        ("easyocr",       "Image OCR (Arabic + English)"),
        ("faster_whisper", "Voice transcription"),
        ("anthropic",     "Claude API provider"),
        ("requests",      "HTTP client (Ollama adapter)"),
    ]:
        ok = _pkg_available(pkg)
        mark = "✓" if ok else "✗ MISSING"
        lines.append(f"  {mark}  {pkg} — {label}")

    # System tools
    lines.append("\nSystem tools:")
    ffmpeg_ok = _binary_available("ffmpeg")
    lines.append(
        f"  {'✓' if ffmpeg_ok else '✗ MISSING'}  ffmpeg — audio decoding for voice transcription"
    )

    # Ollama
    lines.append("\nOllama (optional — only needed when provider = Ollama):")
    ollama_ok = _binary_available("ollama")
    lines.append(
        f"  {'✓' if ollama_ok else '–'}  ollama binary {'found' if ollama_ok else 'not found'}"
    )
    if not ollama_ok:
        lines.append("     Self-hosted: run  bench fi-setup-ollama")
        lines.append("     Frappe Cloud: use Claude instead (see AI Settings)")

    # Next steps
    lines += [
        "",
        "Next steps:",
        "  1. Open AI Settings in Frappe desk → Model tab",
        "  2. Choose Provider (Ollama or Claude) and fill in the config",
        "  3. Click 'Test Connection'",
        "  4. Run  bench fi-check-deps  any time to re-check this list",
        "",
        "Document templates:",
        "  No templates are pre-installed. Define your document types via:",
        "  - Frappe desk: AI Document Template → New",
        "  - JSON bundle: seed_template_bundle(path) in your after_install",
        "  See docs/SEED_TEMPLATES.md for the full guide.",
        "",
        "Improving accuracy over time:",
        "  AI Training Pairs capture user corrections automatically.",
        "  Review them periodically and tune extraction rules in the desk.",
        "  See docs/TRAINING_GUIDE.md for the full improvement workflow.",
        "=" * 60,
        "",
    ]

    # Print to console (visible in bench logs)
    print("\n".join(lines))

    # Also log to Frappe so it's visible in the Error Log if needed
    frappe.logger().info("\n".join(lines))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pkg_available(package: str) -> bool:
    try:
        importlib.import_module(package)
        return True
    except ImportError:
        return False


def _binary_available(binary: str) -> bool:
    try:
        return subprocess.run(
            ["which", binary], capture_output=True
        ).returncode == 0
    except Exception:
        return False
