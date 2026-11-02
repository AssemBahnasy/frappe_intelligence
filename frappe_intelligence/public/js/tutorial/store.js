// Tutorial state: which topics this user sees, which are done, the open one, the search, and how
// the topic list is shown (one chapter open, or folded to a rail).

import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { CHAPTERS, TOPICS } from "./content";

const API = "frappe_intelligence.api.tutorial";
// Done topics, a JSON list in the user's defaults (loaded with the desk; tutorial/progress.py).
const DONE_KEY = "fi_tutorial_done";
// Whether the topic list is folded: a convenience kept per browser.
const FOLDED_KEY = "fi_tutorial_folded";

export const useTutorial = defineStore("fi_tutorial", () => {
	// Set by boot.py only for users AI Settings → Allowed Roles lets use the assistant.
	const assistant = frappe.boot.fi_assistant || null;
	const topics = assistant ? TOPICS.map(with_status).filter((t) => t.status !== "hidden") : [];

	const done = ref(new Set(read_done()));
	const open_key = ref(null);
	const search = ref("");
	const expanded = ref(null); // the one chapter showing its topics
	const folded = ref(read_folded());

	const current = computed(() => topics.find((t) => t.key === open_key.value) || null);
	// The first topic not done yet, reading in order: what Continue suggests.
	const next = computed(() => topics.find((t) => !done.value.has(t.key)) || null);
	const progress = computed(() => ({
		done: topics.filter((t) => done.value.has(t.key)).length,
		total: topics.length,
	}));
	// Every chapter this user has topics in, numbered by its place in the whole tutorial.
	const all_chapters = computed(() =>
		CHAPTERS.map((chapter, index) => {
			const list = topics.filter((t) => t.chapter === chapter.key);
			return {
				...chapter,
				n: index + 1,
				topics: list,
				done: list.filter((t) => done.value.has(t.key)).length,
				total: list.length,
			};
		}).filter((chapter) => chapter.total)
	);
	const chapters = computed(() => {
		const query = search.value.trim().toLowerCase();
		if (!query) return all_chapters.value;
		return all_chapters.value
			.map((chapter) => ({
				...chapter,
				topics: chapter.topics.filter((t) => matches(t, query)),
			}))
			.filter((chapter) => chapter.topics.length);
	});
	const previous_topic = computed(() => topics[topics.indexOf(current.value) - 1] || null);
	const next_topic = computed(() =>
		current.value ? topics[topics.indexOf(current.value) + 1] || null : null
	);

	// An unknown or hidden topic opens the next one up; its chapter opens with it.
	function open(key) {
		const topic = topics.find((t) => t.key === key) || next.value || topics[0];
		open_key.value = topic?.key || null;
		expanded.value = topic?.chapter || null;
	}

	function state_of(topic) {
		if (topic.key === open_key.value) return "open";
		if (done.value.has(topic.key)) return "done";
		if (topic.key === next.value?.key) return "next";
		return "todo";
	}

	// A chapter takes the state of what it holds: the open topic, else all done, else next up.
	function chapter_state(chapter) {
		const states = chapter.topics.map(state_of);
		if (states.includes("open")) return "open";
		if (chapter.done === chapter.total) return "done";
		if (states.includes("next")) return "next";
		return "todo";
	}

	// While searching, every chapter with a match is open.
	const is_expanded = (chapter) => !!search.value.trim() || expanded.value === chapter.key;

	function toggle_chapter(chapter) {
		expanded.value = expanded.value === chapter.key ? null : chapter.key;
	}

	// The topic a chapter starts at: its first one not done yet.
	const chapter_start = (chapter) =>
		chapter.topics.find((t) => !done.value.has(t.key)) || chapter.topics[0];

	const related = (topic) => topics.filter((t) => topic.related?.includes(t.key));

	// Shown at once; the server's list then replaces it, and the desk's copy of the defaults is
	// updated so the page still knows after leaving and coming back without a reload.
	async function mark_done(key) {
		if (done.value.has(key)) return;
		done.value.add(key);
		try {
			const keys = await frappe.xcall(`${API}.set_done`, { topic: key, done: 1 });
			done.value = new Set(keys);
			frappe.defaults.set_user_default_local(DONE_KEY, JSON.stringify(keys));
		} catch {
			done.value.delete(key); // xcall has already shown the error
		}
	}

	function toggle_fold() {
		folded.value = !folded.value;
		try {
			folded.value
				? localStorage.setItem(FOLDED_KEY, "1")
				: localStorage.removeItem(FOLDED_KEY);
		} catch {
			// storage unavailable: the list just opens unfolded next time
		}
	}

	return {
		assistant,
		topics,
		done,
		open_key,
		search,
		folded,
		current,
		next,
		progress,
		all_chapters,
		chapters,
		previous_topic,
		next_topic,
		open,
		state_of,
		chapter_state,
		is_expanded,
		toggle_chapter,
		chapter_start,
		related,
		mark_done,
		toggle_fold,
	};
});

function with_status(topic) {
	const allowed = topic.report
		? !!frappe.boot.allowed_reports?.[topic.report]
		: !topic.doctype || frappe.model.can_read(topic.doctype);
	if (!allowed) return { ...topic, status: "hidden" };
	return { ...topic, status: topic.status?.(frappe.boot.fi_assistant) || null };
}

function matches(topic, query) {
	return [topic.title, topic.text].some((text) => text.toLowerCase().includes(query));
}

function read_done() {
	try {
		return JSON.parse(frappe.defaults.get_user_default(DONE_KEY) || "[]");
	} catch {
		return [];
	}
}

function read_folded() {
	try {
		return !!localStorage.getItem(FOLDED_KEY);
	} catch {
		return false;
	}
}
