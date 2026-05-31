"""
transcriber.py
--------------
Local voice-to-text using Faster-Whisper (CPU-safe, Arabic-first).

This module wraps the ``faster-whisper`` library and exposes a single
``transcribe(audio_file_path, language)`` helper.  The underlying
``WhisperModel`` is lazily initialised as a process-level singleton so
the model is loaded only once across multiple Frappe worker requests.

Configuration (all optional, set in site_config.json / frappe.conf)
----------------------------------------------------------------------
whisper_model_size : str
    One of ``tiny``, ``base``, ``small``, ``medium``, ``large-v3``.
    Defaults to ``"medium"`` — a good balance for Arabic accuracy on CPU.
whisper_device : str
    ``"cpu"`` (default) or ``"cuda"`` if a CUDA GPU is available.
whisper_compute_type : str
    ``"int8"`` (default, smallest memory footprint on CPU) or
    ``"float16"`` / ``"float32"`` for GPU.

Usage
-----
    from frappe_intelligence.models.transcriber import transcribe

    text = transcribe("/tmp/voice_command.webm", language="ar")
"""
from __future__ import annotations

import os
import threading
from typing import Optional

import frappe

# ---------------------------------------------------------------------------
# Thread-safe singleton for the WhisperModel
# ---------------------------------------------------------------------------
_model_lock = threading.Lock()
_whisper_model = None


def _get_model():
    """
    Return the process-level WhisperModel singleton, initialising it on
    first call.

    Raises
    ------
    ImportError
        If ``faster-whisper`` is not installed.
    RuntimeError
        If the model cannot be loaded (bad model name, out of memory, etc.).
    """
    global _whisper_model  # noqa: PLW0603

    if _whisper_model is not None:
        return _whisper_model

    with _model_lock:
        # Double-checked locking
        if _whisper_model is not None:
            return _whisper_model

        try:
            from faster_whisper import WhisperModel  # type: ignore[import]
        except ImportError as exc:
            frappe.log_error(
                title="FasterWhisper not installed",
                message="Run: bench pip install faster-whisper",
            )
            raise ImportError(
                "faster-whisper is not installed. "
                "Add it to pyproject.toml and run `bench pip install`."
            ) from exc

        model_size: str = getattr(frappe.conf, "whisper_model_size", "medium")
        device: str = getattr(frappe.conf, "whisper_device", "cpu")
        compute_type: str = getattr(
            frappe.conf, "whisper_compute_type", "int8")

        frappe.logger().info(
            f"[Transcriber] Loading Whisper model '{model_size}' "
            f"on {device}/{compute_type} — first load may take a moment."
        )

        _whisper_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    return _whisper_model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe(audio_file_path: str, language: str | None = None) -> str:
    """
    Transcribe an audio file to text.

    Parameters
    ----------
    audio_file_path:
        Absolute path to the audio file.  Accepts any format that
        *ffmpeg* can decode: ``.webm``, ``.ogg``, ``.wav``, ``.mp3``, etc.
        Frappe's upload_file API stores files under
        ``/sites/<site>/private/files/``.
    language:
        BCP-47 language code.  Defaults to ``"ar"`` (Arabic).
        Pass ``None`` to let Whisper auto-detect the language.

    Returns
    -------
    str
        The transcribed text, stripped of leading/trailing whitespace.
        Returns an empty string if no speech was detected.

    Raises
    ------
    FileNotFoundError
        If *audio_file_path* does not exist.
    RuntimeError
        If the Whisper model fails to process the file.
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    model = _get_model()

    segments, _info = model.transcribe(
        audio_file_path,
        language=language,
        beam_size=5,
        vad_filter=True,       # skip silent segments
        vad_parameters={"min_silence_duration_ms": 500},
    )

    # ``segments`` is a generator — consume it fully
    text = " ".join(seg.text for seg in segments).strip()
    return text
