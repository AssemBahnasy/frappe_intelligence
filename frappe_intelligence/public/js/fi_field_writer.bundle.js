// Write with AI (approved board 3d): a sparkles button beside long text fields. The user says what the
// field should say, the AI writes it in place, and Undo puts the old text back. Nothing is saved: the
// user saves the form. Server side: api/writer.py; see docs/writer/.

import { job_result } from "./shared/background";

const API = "frappe_intelligence.api.writer";
const BUTTON = "fi-write-button";
const UNDO_SECONDS = 10;
const HIGHLIGHT_MS = 2500;
const CONTEXT_CHARS = 300;
// The form's other values the AI may use; the server keeps only fields the user can read.
const CONTEXT_TYPES = [
	"Data",
	"Link",
	"Dynamic Link",
	"Select",
	"Date",
	"Datetime",
	"Currency",
	"Float",
	"Int",
	"Percent",
	"Phone",
	"Read Only",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
];
// The last description per field, so writing it again starts from it.
const descriptions = new Map();

frappe.ui.form.on("*", {
	refresh(frm) {
		const types = frappe.boot.fi_assistant?.field_writer || [];
		for (const control of Object.values(frm.fields_dict)) {
			if (types.includes(control.df?.fieldtype) && !control.df.read_only)
				add_button(frm, control);
		}
	},
});

// Beside the label, not in it: Frappe rewrites the label's contents when it changes. Fields read-only
// by definition get none; the button hides itself while a field is read-only for the moment
// (stylesheet), so it follows read_only_depends_on, permissions and submit.
function add_button(frm, control) {
	const $label = control.$wrapper?.find(".control-label").first();
	if (!$label?.length || control.$wrapper.find(`.${BUTTON}`).length) return;
	const label = frappe.utils.escape_html(__("Write with AI"));
	const button = $(
		`<button type="button" class="${BUTTON}" title="${label}" aria-label="${label}">
			${frappe.utils.icon("sparkles", "sm", "", "", "", true)}
		</button>`
	).insertAfter($label)[0];
	const popover = new frappe.ui.Popover({
		trigger: button,
		side: "bottom",
		align: "start",
		css_class: "fi-write-popover",
		content: () => description_form(frm, control, popover),
		on_open: () => popover.panel?.querySelector("textarea")?.focus(),
	});
}

function description_form(frm, control, popover) {
	const key = `${frm.doctype}:${control.df.fieldname}`;
	const id = `fi-write-${frappe.utils.get_random(6)}`;
	const keys = `<kbd>${frappe.utils.is_mac() ? "⌘" : "Ctrl"}</kbd> <kbd>Enter</kbd>`;
	const hint = __("{0} to write", [keys]);
	const $form = $(`
		<form class="fi-write-form">
			<label class="fi-write-label" for="${id}">${__("What should this field say?")}</label>
			<textarea id="${id}" rows="3" dir="auto"></textarea>
			<div class="fi-write-actions">
				<span class="fi-write-hint">
					${hint}
				</span>
				<button type="submit" class="btn btn-primary btn-xs">${__("Write")}</button>
			</div>
		</form>
	`);
	const $text = $form.find("textarea").val(descriptions.get(key) || "");
	const submit = () => {
		const description = $text.val().trim();
		if (!description) return $text.trigger("focus");
		descriptions.set(key, description);
		popover.close();
		write(frm, control, description);
	};
	$form.on("submit", (e) => {
		e.preventDefault();
		submit();
	});
	$text.on("keydown", (e) => {
		if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
			e.preventDefault();
			submit();
		}
	});
	return $form[0];
}

async function write(frm, control, description) {
	const { fieldname, fieldtype, label } = control.df;
	const docname = frm.docname;
	const previous = frm.doc[fieldname];
	const toast = frappe.ui.toast({
		message: __("Writing {0}…", [__(label)]),
		loading: true,
		closable: false,
		duration: 0,
	});
	let job;
	try {
		({ job } = await frappe.xcall(`${API}.write_field`, {
			doctype: frm.doctype,
			fieldname,
			instruction: description,
			current: previous || "",
			context: context(frm, fieldname),
			docname: frm.is_new() ? null : docname,
		}));
	} catch {
		toast.dismiss(); // the server's message is already shown
		return;
	}
	try {
		const text = await job_result(job);
		if (frm.docname !== docname)
			throw new Error(__("The form changed before the text was ready."));
		if ((frm.doc[fieldname] || "") !== (previous || "")) {
			throw new Error(
				__("You changed the field while the text was written, so it was left as it is.")
			);
		}
		await frm.set_value(fieldname, fieldtype === "Text Editor" ? frappe.markdown(text) : text);
		highlight(control);
		toast.update({
			message: __("Field updated"),
			icon: "check",
			loading: false,
			closable: true,
			duration: UNDO_SECONDS * 1000,
			action: {
				label: __("Undo"),
				onclick: () => {
					frm.set_value(fieldname, previous ?? "");
					toast.dismiss();
				},
			},
		});
	} catch (e) {
		toast.update({
			type: "error",
			message: e.message || __("The text could not be written. Please try again."),
			loading: false,
			closable: true,
			duration: UNDO_SECONDS * 1000,
		});
	}
}

function context(frm, skip) {
	const values = {};
	for (const df of frm.meta.fields) {
		const value = frm.doc[df.fieldname];
		if (df.fieldname === skip || df.hidden || !CONTEXT_TYPES.includes(df.fieldtype)) continue;
		if (value === undefined || value === null || value === "") continue;
		values[df.fieldname] = typeof value === "string" ? value.slice(0, CONTEXT_CHARS) : value;
	}
	return values;
}

function highlight(control) {
	control.$wrapper.addClass("fi-written");
	setTimeout(() => control.$wrapper.removeClass("fi-written"), HIGHLIGHT_MS);
}
