// Sortable, paged tables inside rendered answers (approved board 1: "1–5 of 7").

const PAGE_SIZE = 5;
const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
const icon = (name) => frappe.utils.icon(name, "xs", "", "", "", true);

export function enhance_tables(root) {
	root.querySelectorAll("table:not([data-fi-enhanced])").forEach(enhance);
}

function enhance(table) {
	table.dataset.fiEnhanced = "1";
	const body = table.tBodies[0];
	if (!body) return;
	const wrapper = document.createElement("div");
	wrapper.className = "fi-table";
	table.replaceWith(wrapper);
	wrapper.append(table);

	const rows = [...body.rows];
	const state = { page: 0, column: -1, ascending: true };
	const pager = rows.length > PAGE_SIZE ? make_pager(wrapper, state, () => render()) : null;

	[...(table.tHead?.rows[0]?.cells || [])].forEach((cell, index) => {
		const button = document.createElement("button");
		button.type = "button";
		button.className = "fi-sort";
		button.append(...cell.childNodes);
		cell.append(button);
		button.addEventListener("click", () => {
			state.ascending = state.column === index ? !state.ascending : true;
			state.column = index;
			state.page = 0;
			render();
		});
	});

	function render() {
		const sorted = state.column < 0 ? rows : [...rows].sort(compare);
		body.replaceChildren(...sorted.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE));
		table.querySelectorAll("th").forEach((th, i) => {
			th.setAttribute("aria-sort", i === state.column ? (state.ascending ? "ascending" : "descending") : "none");
			th.querySelector(".fi-sort-icon")?.remove();
			if (i === state.column) {
				th.querySelector(".fi-sort")?.insertAdjacentHTML(
					"beforeend",
					`<span class="fi-sort-icon">${icon(state.ascending ? "arrow-up" : "arrow-down")}</span>`
				);
			}
		});
		pager?.update(rows.length);
	}

	function compare(a, b) {
		const order = collator.compare(cell_text(a), cell_text(b));
		return state.ascending ? order : -order;

		function cell_text(row) {
			return (row.cells[state.column]?.textContent || "").replace(/,/g, "").trim();
		}
	}

	render();
}

function make_pager(wrapper, state, render) {
	const [back, forward] = frappe.utils.is_rtl() ? ["chevron-right", "chevron-left"] : ["chevron-left", "chevron-right"];
	const pager = document.createElement("div");
	pager.className = "fi-table-pager";
	pager.innerHTML = `
		<span class="fi-table-range" aria-live="polite"></span>
		<button type="button" class="fi-table-page" data-step="-1" aria-label="${__("Previous page")}">${icon(back)}</button>
		<button type="button" class="fi-table-page" data-step="1" aria-label="${__("Next page")}">${icon(forward)}</button>`;
	wrapper.append(pager);
	const pages = (total) => Math.ceil(total / PAGE_SIZE);
	let total = 0;
	pager.querySelectorAll("button").forEach((button) =>
		button.addEventListener("click", () => {
			state.page = Math.min(Math.max(state.page + Number(button.dataset.step), 0), pages(total) - 1);
			render();
		})
	);
	return {
		update(count) {
			total = count;
			const first = state.page * PAGE_SIZE + 1;
			const last = Math.min(first + PAGE_SIZE - 1, total);
			pager.querySelector(".fi-table-range").textContent = __("{0}–{1} of {2}", [first, last, total]);
			const [previous, next] = pager.querySelectorAll("button");
			previous.disabled = state.page === 0;
			next.disabled = state.page >= pages(total) - 1;
		},
	};
}
