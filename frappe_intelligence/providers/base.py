"""Provider-neutral types and the interface every AI provider implements."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

import frappe
from frappe import _

OnText = Callable[[str], None]
ErrorKinds = tuple[tuple[type[BaseException], str], ...]


class ProviderError(Exception):
	"""A provider call failed; the message is safe to show to the user."""


@dataclass
class ToolCall:
	id: str
	name: str
	arguments: dict[str, Any]


@dataclass
class Message:
	"""One conversation turn.

	`raw` keeps the provider's own form of an assistant turn (thinking blocks,
	signatures) so the same provider can replay it unchanged; `raw_provider`
	names the provider that produced it. Tool turns carry the tool `name`
	and the `tool_call_id` they answer.
	"""

	role: Literal["user", "assistant", "tool"]
	content: str = ""
	tool_calls: list[ToolCall] = field(default_factory=list)
	tool_call_id: str | None = None
	name: str | None = None
	raw: Any = None
	raw_provider: str | None = None


@dataclass
class Reply:
	text: str = ""
	tool_calls: list[ToolCall] = field(default_factory=list)
	stop_reason: Literal["end", "tool_calls", "length", "refusal"] = "end"
	raw: Any = None
	raw_provider: str | None = None
	usage: dict[str, int] = field(default_factory=dict)

	def as_message(self) -> Message:
		return Message(
			role="assistant",
			content=self.text,
			tool_calls=self.tool_calls,
			raw=self.raw,
			raw_provider=self.raw_provider,
		)


@dataclass
class ProviderConfig:
	model: str
	api_key: str | None = None
	base_url: str | None = None
	timeout: int = 60
	keep_loaded: bool = False


class Provider(ABC):
	"""A chat model with tool calling and streaming.

	Subclasses set `name` (the AI Settings option) and `settings_prefix`
	(their `<prefix>_api_key`, `<prefix>_model` and `<prefix>_base_url` fields).
	"""

	name: ClassVar[str]
	settings_prefix: ClassVar[str]
	default_model: ClassVar[str] = ""
	default_base_url: ClassVar[str | None] = None
	requires_api_key: ClassVar[bool] = True

	def __init__(self, config: ProviderConfig):
		self.config = config

	@classmethod
	def from_settings(cls, settings) -> Provider:
		def value(fieldname: str):
			return settings.get(fieldname) or frappe.conf.get(fieldname)

		prefix = cls.settings_prefix
		api_key = None
		if cls.requires_api_key:
			api_key = settings.get_password(f"{prefix}_api_key", raise_exception=False) or frappe.conf.get(
				f"{prefix}_api_key"
			)
		return cls(
			ProviderConfig(
				model=value(f"{prefix}_model") or cls.default_model,
				api_key=api_key,
				base_url=value(f"{prefix}_base_url") or cls.default_base_url,
				timeout=int(settings.get("request_timeout") or 60),
				keep_loaded=bool(settings.get("keep_model_loaded")),
			)
		)

	@abstractmethod
	def complete(
		self,
		messages: list[Message],
		*,
		system: str | None = None,
		tools: list[dict] | None = None,
		on_text: OnText | None = None,
		json_mode: bool = False,
	) -> Reply:
		"""Run one model turn. Tools are `{"name", "description", "parameters"}` dicts.

		Streams text through `on_text`; raises ProviderError on failure.
		"""

	def checked(self, reply: Reply) -> Reply:
		"""Never hand back a tool call that may be incomplete."""
		if reply.stop_reason == "length" and reply.tool_calls:
			raise self.error("cut_off")
		if reply.stop_reason == "refusal":
			reply.tool_calls = []
		return reply

	def test_connection(self) -> None:
		"""Raise ProviderError if the provider cannot answer."""
		self.complete([Message(role="user", content="Reply with the single word OK.")])

	def ensure_configured(self) -> None:
		if self.requires_api_key and not self.config.api_key:
			raise self.error("missing_key")
		if not self.config.model:
			raise self.error("missing_model")

	def error(self, kind: str, detail: str = "") -> ProviderError:
		messages = {
			"missing_key": _("{0} API key is not set in AI Settings."),
			"missing_model": _("{0} model is not set in AI Settings."),
			"auth": _("{0} rejected the API key."),
			"model": _("{0} has no model named {1}."),
			"rate_limit": _("{0} rate limit reached. Try again shortly."),
			"timeout": _("{0} did not answer within {2} seconds."),
			"connection": _("Cannot reach {0} at {3}."),
			"cut_off": _("{0} stopped before finishing a tool call. Try a shorter request."),
			"other": _("{0} request failed: {4}"),
		}
		url = self.config.base_url or self.default_base_url or self.name
		return ProviderError(
			messages[kind].format(self.name, self.config.model, self.config.timeout, url, detail)
		)

	def error_from(self, exc: BaseException, kinds: ErrorKinds) -> ProviderError:
		"""Translate an SDK exception using `(exception class, kind)` pairs, most specific first."""
		kind = next((kind for cls, kind in kinds if isinstance(exc, cls)), "other")
		return self.error(kind, getattr(exc, "message", None) or str(exc))


def parse_arguments(raw: str | dict | None) -> dict[str, Any]:
	"""Tool arguments arrive as JSON text from some providers and as objects from others."""
	if isinstance(raw, dict):
		return raw
	try:
		parsed = json.loads(raw or "{}")
	except json.JSONDecodeError:
		return {}
	return parsed if isinstance(parsed, dict) else {}
