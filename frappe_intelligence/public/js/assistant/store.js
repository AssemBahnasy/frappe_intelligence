// Panel state: the open conversation, its turns, and the answer being written.
// Answers arrive as `fi_assistant` realtime events (agent/runs.py); see docs/agent/live-replies.md.

import { defineStore } from "pinia";
import { computed, onScopeDispose, reactive, ref } from "vue";
import { perform_action } from "./actions";
import { page_context } from "./page_context";

const API = "frappe_intelligence.api.chat";
const EVENT = "fi_assistant";
const CONVERSATION_KEY = "fi_assistant_conversation";
const WATCH_SECONDS = 15;

export const useAssistant = defineStore("fi_assistant", () => {
	const conversation = ref(null);
	const mode = ref("Ask"); // Ask or Agent
	const turns = ref([]);
	const run = ref(null); // { id, turn } while an answer is being written
	const loading = ref(false);
	const context = ref(page_context());
	const context_dismissed = ref(false);
	// Events that arrive before send_message has returned the run id.
	let sending = false;
	let early_events = [];

	async function send(text) {
		text = text.trim();
		if (!text || run.value || sending) return;
		const turn = reactive(new_turn(text));
		turns.value.push(turn);
		sending = true;
		try {
			const r = await frappe.xcall(`${API}.send_message`, {
				message: text,
				conversation: conversation.value,
				context: context_dismissed.value ? null : page_context({ with_tab: true }),
				mode: mode.value,
			});
			set_conversation(r.conversation);
			run.value = { id: r.run_id, turn };
			early_events.filter((e) => e.run_id === r.run_id).forEach(on_event);
		} catch (e) {
			turn.pending = false;
			turn.error = error_text(e);
		} finally {
			sending = false;
			early_events = [];
		}
	}

	function stop() {
		if (!run.value) return;
		run.value.turn.stopping = true;
		frappe.xcall(`${API}.stop_message`, {
			conversation: conversation.value,
			run_id: run.value.id,
		});
	}

	function on_event(e) {
		if (!run.value) {
			if (sending) early_events.push(e);
			return;
		}
		if (e.run_id !== run.value.id) return;
		const turn = run.value.turn;
		if (e.type === "text") {
			const part = turn.reporting ? "report" : "answer";
			turn[part] = (turn[part] || "") + e.text;
		} else if (e.type === "step") {
			const step = turn.steps.find((s) => s.call_id === e.call_id);
			step ? Object.assign(step, e) : turn.steps.push({ ...e });
		} else if (e.type === "done") {
			Object.assign(turn, {
				pending: false,
				answer: turn.reporting ? turn.answer : turn.answer || e.reply,
				error: e.error,
				stopped: e.stopped,
				actions: e.actions || [],
			});
			turn.proposals.push(...(e.proposals || []).map((p) => ({ ...p, status: "pending" })));
			run.value = null;
			turn.actions.forEach(perform_action);
			refresh(); // picks up stored ids, used by feedback
		}
	}

	async function open_conversation(name) {
		loading.value = true;
		try {
			const r = await frappe.xcall(`${API}.get_conversation`, { name });
			set_conversation(r.name);
			mode.value = r.mode === "Agent" && frappe.boot.fi_assistant.agent_mode ? "Agent" : "Ask";
			turns.value = r.turns;
			const last = turns.value.at(-1);
			run.value = r.active_run && last ? { id: r.active_run, turn: last } : null;
			if (run.value) last.pending = true;
		} catch {
			new_chat();
		} finally {
			loading.value = false;
		}
	}

	async function refresh() {
		if (!conversation.value || run.value) return;
		const r = await frappe.xcall(`${API}.get_conversation`, { name: conversation.value });
		turns.value = r.turns;
	}

	// Confirm or reject a proposed change; the answer continues once none is left waiting.
	async function decide(turn, proposal, approve) {
		const r = await frappe.xcall(`${API}.decide_proposal`, {
			conversation: conversation.value,
			call_id: proposal.call_id,
			approve,
		});
		proposal.status = approve ? "approved" : "rejected";
		if (r.run_id) {
			turn.reporting = true; // what the model writes now reports on the change
			turn.pending = true;
			run.value = { id: r.run_id, turn };
		}
	}

	const has_pending_proposals = computed(() =>
		turns.value.some((t) => t.proposals?.some((p) => p.status === "pending"))
	);

	function new_chat() {
		set_conversation(null);
		turns.value = [];
		run.value = null;
	}

	function restore() {
		const name = storage("get");
		if (name) open_conversation(name);
	}

	function list_conversations() {
		return frappe.xcall(`${API}.list_conversations`);
	}

	async function rate(turn, value) {
		const feedback = turn.feedback === value ? null : value;
		turn.feedback = feedback;
		await frappe.xcall(`${API}.rate_reply`, {
			conversation: conversation.value,
			message: turn.answer_id,
			feedback,
		});
	}

	function track_page() {
		context.value = page_context();
		context_dismissed.value = false;
	}

	function set_conversation(name) {
		conversation.value = name;
		storage(name ? "set" : "remove", name);
	}

	// Not frappe.router.on: its off() cannot remove a handler (event_emitter.js).
	// A run whose worker died never sends "done", and a realtime event can be missed: while a run
	// is open, ask the server now and then whether it is still going.
	async function watch_run() {
		if (!run.value || !conversation.value) return;
		const id = run.value.id;
		const r = await frappe.xcall(`${API}.get_conversation`, { name: conversation.value }).catch(() => null);
		if (r && run.value?.id === id && r.active_run !== id) {
			run.value = null;
			turns.value = r.turns;
		}
	}
	const watcher = setInterval(watch_run, WATCH_SECONDS * 1000);

	frappe.realtime.on(EVENT, on_event);
	$(document).on("page-change.fi_assistant", track_page);
	onScopeDispose(() => {
		clearInterval(watcher);
		frappe.realtime.off(EVENT, on_event);
		$(document).off("page-change.fi_assistant");
	});

	return {
		conversation,
		mode,
		turns,
		has_pending_proposals,
		run,
		loading,
		context,
		context_dismissed,
		send,
		stop,
		open_conversation,
		new_chat,
		restore,
		list_conversations,
		rate,
		decide,
	};
});

function new_turn(question) {
	return {
		id: frappe.utils.get_random(8),
		question,
		created: frappe.datetime.now_datetime(),
		steps: [],
		proposals: [],
		actions: [],
		answer: "",
		report: "",
		pending: true,
	};
}

function error_text(e) {
	return e?.message || __("Could not send the message. Please try again.");
}

// The open conversation survives a reload; storage can be unavailable (private windows).
function storage(op, value) {
	try {
		if (op === "get") return localStorage.getItem(CONVERSATION_KEY);
		if (op === "set") localStorage.setItem(CONVERSATION_KEY, value);
		if (op === "remove") localStorage.removeItem(CONVERSATION_KEY);
	} catch {
		return null;
	}
}
