"""Answer in a background job and stream progress to the browser.

Every event is sent on the realtime event `fi_assistant` to the conversation's owner and
carries the `run_id`, so a page applies only the events of the run it started.
"""

from __future__ import annotations

import time
from dataclasses import asdict

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

from frappe_intelligence.agent.loop import Hooks, Step, TurnResult, run_turn
from frappe_intelligence.workflows import turn as workflow_turn

EVENT = "fi_assistant"
QUEUE = "long"
TIMEOUT = 1500  # seconds; local models can take minutes on large documents
STOP_KEY = "fi_assistant_stop:{0}"
STOP_TTL = 3600
STOP_CHECK_SECONDS = 0.5
TEXT_FLUSH_SECONDS = 0.15
TEXT_FLUSH_CHARS = 200


def is_running(conversation) -> bool:
	return bool(conversation.active_run) and is_job_enqueued(conversation.active_run)


def ensure_idle(conversation) -> None:
	if is_running(conversation):
		frappe.throw(_("The assistant is still answering in this conversation."))


def start(conversation) -> str:
	"""Save the conversation (with its new user message) and answer it in a background job."""
	run_id = frappe.generate_hash(length=16)
	conversation.active_run = run_id
	conversation.save()
	frappe.enqueue(
		"frappe_intelligence.agent.runs.execute",
		queue=QUEUE,
		timeout=TIMEOUT,
		job_id=run_id,
		enqueue_after_commit=True,
		conversation=conversation.name,
		run_id=run_id,
	)
	return run_id


def stop(conversation, run_id: str) -> None:
	if run_id and conversation.active_run == run_id:
		frappe.cache.set_value(STOP_KEY.format(run_id), 1, expires_in_sec=STOP_TTL)


def execute(conversation: str, run_id: str) -> None:
	"""Background job: run the turn (a guided workflow's, or the agent's), saving after every step so a
	reload shows progress."""
	doc = frappe.get_doc("AI Conversation", conversation)
	if doc.active_run != run_id:
		return
	stream = Stream(doc.owner, conversation, run_id)
	hooks = Hooks(
		on_text=stream.text,
		on_step=stream.step,
		should_stop=StopFlag(run_id),
		checkpoint=lambda: _save(doc),
	)
	answer = workflow_turn.run_turn if doc.mode == "Workflow" else run_turn
	try:
		result = answer(doc, hooks)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(f"Assistant run {run_id} failed")
		doc = frappe.get_doc("AI Conversation", conversation)
		result = TurnResult(error=_("The assistant hit an unexpected error. Please try again."))
		doc.add_error(result.error)
	finally:
		frappe.cache.delete_value(STOP_KEY.format(run_id))

	doc.active_run = None
	_save(doc)
	stream.done(result)


def _save(doc) -> None:
	doc.save()
	frappe.db.commit()


class Stream:
	"""Publishes run events; text deltas are batched so the socket is not flooded per token."""

	def __init__(self, user: str, conversation: str, run_id: str):
		self.user, self.conversation, self.run_id = user, conversation, run_id
		self.buffer: list[str] = []
		self.flushed_at = time.monotonic()

	def text(self, delta: str) -> None:
		self.buffer.append(delta)
		if (
			sum(map(len, self.buffer)) >= TEXT_FLUSH_CHARS
			or time.monotonic() - self.flushed_at >= TEXT_FLUSH_SECONDS
		):
			self.flush()

	def flush(self) -> None:
		if self.buffer:
			self.publish("text", text="".join(self.buffer))
			self.buffer = []
		self.flushed_at = time.monotonic()

	def step(self, step: Step) -> None:
		self.flush()
		self.publish("step", **asdict(step))

	def done(self, result: TurnResult) -> None:
		self.flush()
		self.publish("done", **asdict(result))

	def publish(self, kind: str, **payload) -> None:
		frappe.publish_realtime(
			EVENT,
			{"run_id": self.run_id, "conversation": self.conversation, "type": kind, **payload},
			user=self.user,
		)


class StopFlag:
	"""`should_stop` for the loop: reads the Stop flag from Redis at most every half second."""

	def __init__(self, run_id: str):
		self.key = STOP_KEY.format(run_id)
		self.checked_at = 0.0
		self.stopped = False

	def __call__(self) -> bool:
		now = time.monotonic()
		if not self.stopped and now - self.checked_at >= STOP_CHECK_SECONDS:
			self.checked_at = now
			self.stopped = bool(frappe.cache.get_value(self.key, use_local_cache=False))
		return self.stopped
