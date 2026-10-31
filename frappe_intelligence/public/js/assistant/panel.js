// The docked assistant panel: an <aside> beside the desk with the Vue app inside.
// Created once by the launcher on first use; it stays mounted across routes.

import { createPinia } from "pinia";
import { createApp } from "vue";
import Panel from "./components/Panel.vue";
import { useAssistant } from "./store";

export class AssistantPanel {
	constructor({ on_toggle = () => {} } = {}) {
		this.on_toggle = on_toggle;
		this.$aside = $(`<aside class="fi-assistant" hidden></aside>`)
			.attr("aria-label", frappe.boot.fi_assistant.name)
			.appendTo(document.body);
		this.pinia = createPinia();
		this.app = createApp(Panel, { host: this });
		SetVueGlobals(this.app);
		this.app.use(this.pinia);
		this.app.mount(this.$aside[0]);
		this.store = useAssistant(this.pinia);
		this.store.restore();
	}

	get is_open() {
		return !this.$aside.prop("hidden");
	}

	open() {
		this.$aside.prop("hidden", false);
		$("body").addClass("fi-assistant-open");
		this.on_toggle(true);
		this.$aside.find("textarea").trigger("focus");
	}

	close() {
		this.$aside.prop("hidden", true);
		$("body").removeClass("fi-assistant-open");
		this.on_toggle(false);
	}

	toggle() {
		this.is_open ? this.close() : this.open();
	}

	destroy() {
		this.app.unmount();
		this.store.$dispose();
		this.$aside.remove();
		$("body").removeClass("fi-assistant-open");
	}
}
