"""AI providers. `get_provider()` returns the one chosen in AI Settings."""

from __future__ import annotations

import importlib

import frappe

from frappe_intelligence.providers.base import (
	Message,
	Provider,
	ProviderConfig,
	ProviderError,
	Reply,
	ToolCall,
)
from frappe_intelligence.providers.fallback import FallbackProvider

# AI Settings "Provider" option → class. Imported lazily so only the chosen SDK loads.
PROVIDERS = {
	"OpenAI": "frappe_intelligence.providers.openai.OpenAIProvider",
	"Claude": "frappe_intelligence.providers.claude.ClaudeProvider",
	"Gemini": "frappe_intelligence.providers.gemini.GeminiProvider",
	"Ollama": "frappe_intelligence.providers.ollama.OllamaProvider",
}
LOCAL_PROVIDER = "Ollama"


def get_provider() -> Provider | FallbackProvider:
	settings = frappe.get_cached_doc("AI Settings")
	name = settings.ai_provider or LOCAL_PROVIDER
	provider = build(name, settings)
	if settings.enable_ollama_fallback and name != LOCAL_PROVIDER:
		return FallbackProvider(provider, build(LOCAL_PROVIDER, settings))
	return provider


def build(name: str, settings) -> Provider:
	if name not in PROVIDERS:
		frappe.throw(frappe._("Unknown AI provider: {0}").format(name))
	module, _, cls = PROVIDERS[name].rpartition(".")
	return getattr(importlib.import_module(module), cls).from_settings(settings)


__all__ = [
	"FallbackProvider",
	"Message",
	"Provider",
	"ProviderConfig",
	"ProviderError",
	"Reply",
	"ToolCall",
	"build",
	"get_provider",
]
