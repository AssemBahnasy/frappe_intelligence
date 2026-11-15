// A report the agent exported (agent/tools/reports.py: export_report), through Frappe's own Export:
// frappe.desk.query_report.export_query runs the report again and checks the Export right.

const EXPORT_METHOD = "frappe.desk.query_report.export_query";
const EXTENSIONS = { Excel: "xlsx", CSV: "csv" };

function export_args({ report_name, filters }, file_format) {
	return {
		report_name,
		file_format_type: file_format,
		filters: JSON.stringify(filters || {}),
		custom_columns: "[]",
	};
}

// Logged as the report page's Export button logs it (query_report.js: make_access_log).
function log_export({ report_name, filters }, file_format) {
	frappe.call("frappe.core.doctype.access_log.access_log.make_access_log", {
		report_name,
		filters,
		file_type: file_format,
		method: "Export",
	});
}

// Fetched rather than posted as a form, so the card knows when the file has arrived or why it failed.
export async function download_report(action, file_format) {
	log_export(action, file_format);
	const response = await fetch(`/api/method/${EXPORT_METHOD}`, {
		method: "POST",
		headers: { "X-Frappe-CSRF-Token": frappe.csrf_token, Accept: "application/json" },
		body: new URLSearchParams(export_args(action, file_format)),
	});
	const type = response.headers.get("Content-Type") || "";
	if (!response.ok) throw new Error(await server_message(response));
	// Frappe answers "No data to export" with a web page instead of a file.
	if (type.includes("text/html")) throw new Error(__("No data to export. Try other filters."));
	save(await response.blob(), `${__(action.report_name)}.${EXTENSIONS[file_format]}`);
}

// Frappe prepares the file in the background and emails the user a link; it shows its own message.
export function email_report(action, file_format) {
	log_export(action, file_format);
	return frappe.call({
		method: EXPORT_METHOD,
		args: { ...export_args(action, file_format), export_in_background: 1 },
	});
}

export function open_report({ report_name, filters }) {
	frappe.route_options = { ...(filters || {}) };
	frappe.set_route("query-report", report_name);
}

// The filters as label and value, for the card.
export function filter_rows(filters) {
	return Object.entries(filters || {})
		.filter(([, value]) => value !== null && value !== "" && value !== undefined)
		.map(([key, value]) => ({ label: __(frappe.unscrub(key)), value: shown(value) }));
}

function shown(value) {
	if (Array.isArray(value)) return value.map(shown).join(", ");
	if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return frappe.datetime.str_to_user(value);
	}
	// Select options ("Due Date") read as the report's own filters show them.
	return typeof value === "string" ? __(value) : String(value);
}

function save(blob, file_name) {
	const url = URL.createObjectURL(blob);
	const link = Object.assign(document.createElement("a"), { href: url, download: file_name });
	link.click();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function server_message(response) {
	try {
		const body = await response.json();
		const messages = JSON.parse(body._server_messages || "[]");
		// Without a message, Frappe sends the exception as "frappe.exceptions.PermissionError: …".
		const message = messages.length
			? JSON.parse(messages[0]).message
			: (body.exception || "").replace(/^[\w.]+: /, "");
		if (message) return frappe.utils.html2text(message);
	} catch {
		// not JSON
	}
	return __("The export did not work.");
}
