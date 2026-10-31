// Browser actions returned by the agent's desk tools (agent/tools/desk.py).

const HANDLERS = {
	set_route: ({ route }) => open_route(route),
	open_form: ({ doctype, name }) => frappe.set_route("Form", doctype, name),
	new_doc: ({ doctype, defaults }) => frappe.new_doc(doctype, defaults || {}),
	chart: () => {}, // drawn under the answer
};

export function perform_action(action) {
	HANDLERS[action?.type]?.(action);
}

// "/app/sales-invoice?status=Unpaid" → set_route("sales-invoice") with route options.
export function open_route(route) {
	const url = new URL(route, window.location.origin);
	const parts = url.pathname.split("/").filter(Boolean);
	if (["app", "desk"].includes(parts[0])) parts.shift();
	const options = Object.fromEntries(url.searchParams);
	if (Object.keys(options).length) frappe.route_options = options;
	frappe.set_route(...parts);
}
