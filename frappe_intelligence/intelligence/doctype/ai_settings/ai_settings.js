frappe.ui.form.on("AI Settings", {
	ai_provider(frm) {
		frm.trigger("refresh");
	},

	refresh(frm) {
		const provider = frm.doc.ai_provider || "Ollama";

		frm.add_custom_button(__("Test Connection"), () => {
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
		});

		// Show/hide WhatsApp tab based on whether frappe_whatsapp is installed
		frappe.call({
			method: "frappe_intelligence.api.settings.is_whatsapp_installed",
			callback(r) {
				const installed = r.message === true;
				frm.set_df_property("whatsapp_tab", "hidden", installed ? 0 : 1);
				if (!installed) {
					// Replace the tab with a clear message if the user somehow sees it
					frm.dashboard.set_headline(
						__("WhatsApp integration requires the frappe_whatsapp app to be installed.")
					);
				}
			},
		});
	},
});
