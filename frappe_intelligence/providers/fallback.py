"""Retry a failed call on a second provider (AI Settings → Enable Ollama Fallback)."""

from __future__ import annotations

import frappe

from frappe_intelligence.providers.base import Message, OnText, Provider, ProviderError, Reply


class FallbackProvider:
	"""Same interface as Provider; answers from `fallback` when `primary` fails before streaming anything."""

	def __init__(self, primary: Provider, fallback: Provider):
		self.primary = primary
		self.fallback = fallback

	@property
	def name(self) -> str:
		return self.primary.name

	@property
	def config(self):
		return self.primary.config

	def complete(self, messages: list[Message], *, on_text: OnText | None = None, **kwargs) -> Reply:
		streamed = False

		def relay(text: str) -> None:
			nonlocal streamed
			streamed = True
			if on_text:
				on_text(text)

		try:
			return self.primary.complete(messages, on_text=relay, **kwargs)
		except ProviderError as exc:
			if streamed:
				raise
			# File logger, not Error Log: extraction calls this from worker threads.
			frappe.logger("frappe_intelligence").warning(
				f"{self.primary.name} failed, answering with {self.fallback.name}: {exc}"
			)
			return self.fallback.complete(messages, on_text=on_text, **kwargs)

	def test_connection(self) -> None:
		self.primary.test_connection()
