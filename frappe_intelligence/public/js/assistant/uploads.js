// Files attached in the panel: uploaded as private Files through Frappe's own upload endpoint.

export const ACCEPTED_FILES = ".pdf,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp,.txt";
export const MAX_FILES = 3; // api/chat.py MAX_ATTACHMENTS

export async function upload_file(file) {
	const form = new FormData();
	form.append("file", file, file.name);
	form.append("is_private", "1");
	const response = await fetch("/api/method/upload_file", {
		method: "POST",
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": frappe.csrf_token },
		body: form,
	});
	const data = await response.json().catch(() => ({}));
	if (!response.ok) throw new Error(server_message(data) || __("The file could not be uploaded."));
	return { file_url: data.message.file_url, file_name: data.message.file_name };
}

// "PDF", "Image" or the extension, for the file chip.
export function file_kind(file_name) {
	const ext = (file_name.split(".").pop() || "").toLowerCase();
	if (ext === "pdf") return __("PDF");
	if (["png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp"].includes(ext)) return __("Image");
	return ext.toUpperCase();
}

function server_message(data) {
	try {
		return JSON.parse(JSON.parse(data._server_messages)[0]).message;
	} catch {
		return data.exception || "";
	}
}
