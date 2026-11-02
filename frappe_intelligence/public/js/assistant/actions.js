// Browser actions returned by the agent's desk tools (agent/tools/desk.py).

const SETTLE_MS = 300;

const HANDLERS = {
	set_route: ({ route }) => open_route(route),
	open_form: ({ doctype, name }) => frappe.set_route("Form", doctype, name),
	new_doc: ({ doctype, defaults }) => open_new_form(doctype, defaults),
	fill_form,
	chart: () => {}, // drawn under the answer
};

// Into the new form the user has open; if they have left it, a new form gets the values instead.
async function fill_form({ doctype, values }) {
	const frm = window.cur_frm;
	if (frm?.doctype !== doctype || !frm.is_new()) return open_new_form(doctype, values);
	const known = Object.fromEntries(
		Object.entries(values).filter(([field]) => frm.fields_dict[field])
	);
	await frm.set_value(known);
	// A link (e.g. the supplier) makes the form fetch its defaults, which can overwrite values the
	// user confirmed (e.g. the due date); put those back once the form has finished.
	await settled();
	const changed = Object.entries(known).filter(
		([field, value]) => !Array.isArray(value) && frm.doc[field] != value
	);
	if (changed.length) frm.set_value(Object.fromEntries(changed));
}

// The full form, filled: frappe.new_doc would open Quick Entry where a DocType has one, and hands it the
// values through frappe.route_options, which a list page takes as its filters first.
async function open_new_form(doctype, values = {}) {
	await frappe.model.with_doctype(doctype);
	const doc = frappe.model.get_new_doc(doctype, null, null, true);
	for (const [field, value] of Object.entries(values)) {
		const df = frappe.meta.get_docfield(doctype, field);
		if (!df) continue;
		if (frappe.model.table_fields.includes(df.fieldtype)) {
			doc[field] = []; // drops the empty row a mandatory table starts with
			(Array.isArray(value) ? value : []).forEach((row) =>
				Object.assign(frappe.model.add_child(doc, df.options, field), row)
			);
		} else {
			doc[field] = value;
		}
	}
	frappe.set_route("Form", doctype, doc.name);
}

// Form scripts chain server calls from callbacks, so wait until none has been running for a moment.
async function settled() {
	do {
		await frappe.after_ajax();
		await new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
	} while (frappe.request.ajax_count);
}

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
