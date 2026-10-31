// The desk page the user is on, sent with each message (agent/prompts.py → page_note).

export function page_context({ with_tab = false } = {}) {
	// null at desk start-up, before the router has run
	const route = frappe.get_route() || [];
	const [view, doctype, name] = route;
	if (view === "Form" && doctype && name && !name.startsWith("new-")) {
		const tab = with_tab && cur_frm?.docname === name ? cur_frm.get_active_tab?.()?.label : null;
		return { doctype, docname: name, ...(tab ? { tab } : {}) };
	}
	if (view === "List" && doctype) {
		const filters = cur_list?.doctype === doctype ? cur_list.get_filters_for_args?.() : null;
		return { doctype, ...(filters?.length ? { list_filters: filters } : {}) };
	}
	return { route: route.join("/") };
}

export function context_label(context) {
	if (context?.docname) return `${__(context.doctype)} · ${context.docname}`;
	if (context?.doctype) return __("{0} list", [__(context.doctype)]);
	return "";
}
