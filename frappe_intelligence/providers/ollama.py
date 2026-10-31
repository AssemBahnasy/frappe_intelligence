"""Local models through Ollama's OpenAI-compatible endpoint, so data stays on the server."""

from __future__ import annotations

import openai
import requests
from frappe import _

from frappe_intelligence.providers.base import ProviderError
from frappe_intelligence.providers.openai import OpenAIProvider

_preloaded: set[tuple[str, str]] = set()


class OllamaProvider(OpenAIProvider):
	name = "Ollama"
	settings_prefix = "ollama"
	default_model = "qwen2.5:7b"
	default_base_url = "http://localhost:11434"
	requires_api_key = False

	def complete(self, messages, **kwargs):
		if self.config.keep_loaded:
			self._keep_model_loaded()
		return super().complete(messages, **kwargs)

	def test_connection(self) -> None:
		installed = {model["name"] for model in self._request("get", "/api/tags").get("models", [])}
		wanted = self.config.model if ":" in self.config.model else f"{self.config.model}:latest"
		if wanted not in installed:
			raise ProviderError(_("Ollama has no model {0}. Run: ollama pull {0}").format(self.config.model))

	def _client(self) -> openai.OpenAI:
		return openai.OpenAI(api_key="ollama", base_url=f"{self._root()}/v1", timeout=self.config.timeout)

	def _keep_model_loaded(self) -> None:
		"""Ollama keeps a model in memory indefinitely after a request with keep_alive -1."""
		key = (self._root(), self.config.model)
		if key in _preloaded:
			return
		self._request("post", "/api/generate", json={"model": self.config.model, "keep_alive": -1})
		_preloaded.add(key)

	def _root(self) -> str:
		return self.config.base_url.rstrip("/")

	def _request(self, method: str, path: str, **kwargs) -> dict:
		try:
			response = requests.request(
				method, f"{self._root()}{path}", timeout=self.config.timeout, **kwargs
			)
			response.raise_for_status()
		except requests.RequestException as exc:
			raise self.error_from(
				exc, ((requests.Timeout, "timeout"), (requests.ConnectionError, "connection"))
			) from exc
		return response.json()
