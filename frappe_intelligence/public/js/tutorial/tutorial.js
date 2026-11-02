// The tutorial page's Vue app, mounted by the page controller (intelligence/page/intelligence_tutorial).

import { createPinia } from "pinia";
import { createApp } from "vue";
import TutorialRoot from "./Tutorial.vue";
import { useTutorial } from "./store";
import { show_me } from "./tour";

export class Tutorial {
	constructor({ wrapper, page, topic }) {
		this.page = page;
		this.pinia = createPinia();
		this.app = createApp(TutorialRoot);
		SetVueGlobals(this.app);
		this.app.use(this.pinia);
		this.store = useTutorial(this.pinia);
		this.setup_page();
		this.app.mount($(wrapper).get(0));
		this.open(topic);
	}

	setup_page() {
		this.page.clear_actions();
		this.page.clear_menu();
		this.page.set_title(__("Tutorial"));
		if (!this.store.assistant) return;
		// Not returned: the page would show the button as busy for as long as the walk lasts.
		this.page.set_primary_action(__("Show me"), () => {
			this.show_me();
		});
		// fi-try-it: a Show me step can point at it (tour.js).
		this.page
			.set_secondary_action(__("Try it now"), () => this.try_it())
			.addClass("fi-try-it");
	}

	// Walks through the open topic on the desk; finishing the walk marks the topic done.
	async show_me() {
		const topic = this.store.current;
		if (!topic || this.touring) return; // a second click while the walk starts
		this.touring = true;
		try {
			const { finished } = await show_me(topic);
			if (finished && this.store) this.store.mark_done(topic.key);
		} finally {
			this.touring = false;
		}
	}

	open(topic) {
		this.store.open(topic);
	}

	// Opens the real place the open topic is about.
	try_it() {
		const target = this.store.current?.try || {};
		if (target.panel) frappe_intelligence.assistant.open();
		else if (target.new_doc) frappe.new_doc(target.new_doc);
		else if (target.route) frappe.set_route(...target.route);
	}

	destroy() {
		this.app?.unmount();
		this.store?.$dispose();
		this.app = this.store = this.pinia = null;
	}
}
