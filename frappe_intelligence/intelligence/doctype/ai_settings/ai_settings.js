frappe.ui.form.on("AI Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => frm.trigger("test_connection"));
		frm.trigger("check_whatsapp");
	},

	test_connection(frm) {
		const provider = frm.doc.ai_provider || "Ollama";
		frappe.show_alert({ message: __("Testing connection…"), indicator: "blue" });
		frappe.call({
			method: "frappe_intelligence.api.settings.test_connection",
			callback(r) {
				if (r.message && r.message.ok) {
					frappe.show_alert({
						message: __("Connected successfully to {0}!", [provider]),
						indicator: "green",
					});
				} else {
					frappe.msgprint({
						title: __("Connection Failed"),
						message: r.message ? r.message.error : __("Unknown error"),
						indicator: "red",
					});
				}
			},
		});
	},

	// The WhatsApp tab only shows when frappe_whatsapp is installed. A tab keeps its own field
	// definition and reads it on refresh (form/tab.js), so set_df_property does not reach it; and
	// every headline is added, not replaced (form/layout.js show_message), so it is cleared first.
	check_whatsapp(frm) {
		frappe.call({
			method: "frappe_intelligence.api.settings.is_whatsapp_installed",
			callback(r) {
				const installed = r.message === true;
				const tab = frm.layout.tabs.find((t) => t.df.fieldname === "whatsapp_tab");
				if (tab) {
					tab.df.hidden = installed ? 0 : 1;
					tab.refresh();
				}
				frm.dashboard.clear_headline();
				if (!installed) {
					frm.dashboard.set_headline(
						__(
							"WhatsApp integration requires the frappe_whatsapp app to be installed."
						)
					);
				}
			},
		});
	},
});
