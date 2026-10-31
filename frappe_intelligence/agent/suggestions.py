"""Starter questions for a new chat, picked by the user's roles."""

from __future__ import annotations

import frappe
from frappe import _

GROUP_LIMIT = 2
PROMPTS_PER_GROUP = 2


def _groups() -> list[dict]:
	return [
		{
			"label": _("Accounts"),
			"roles": {"Accounts User", "Accounts Manager"},
			"prompts": [
				_("Which sales invoices become overdue this week?"),
				_("Chart monthly sales for this year"),
				_("Which customers owe the most right now?"),
			],
		},
		{
			"label": _("Selling"),
			"roles": {"Sales User", "Sales Manager"},
			"prompts": [
				_("How many open sales orders do we have?"),
				_("Who are our top 5 customers this quarter?"),
			],
		},
		{
			"label": _("Buying"),
			"roles": {"Purchase User", "Purchase Manager"},
			"prompts": [
				_("Which purchase orders are still to be received?"),
				_("Which suppliers did we buy from most this year?"),
			],
		},
		{
			"label": _("Stock"),
			"roles": {"Stock User", "Stock Manager"},
			"prompts": [
				_("Which items are below their reorder level?"),
				_("How many items do we have in stock?"),
			],
		},
		{
			"label": _("HR"),
			"roles": {"HR User", "HR Manager"},
			"prompts": [
				_("Who is on leave this week?"),
				_("How many active employees do we have per department?"),
			],
		},
		{
			"label": _("Getting started"),
			"roles": set(),
			"prompts": [
				_("What can you help me with?"),
				_("Which reports can I run?"),
			],
		},
	]


def for_user(user: str | None = None) -> list[dict]:
	"""Up to two groups matching the user's roles, falling back to general questions."""
	roles = set(frappe.get_roles(user))
	groups = [group for group in _groups() if group["roles"] & roles][:GROUP_LIMIT] or [_groups()[-1]]
	return [{"label": group["label"], "prompts": group["prompts"][:PROMPTS_PER_GROUP]} for group in groups]
