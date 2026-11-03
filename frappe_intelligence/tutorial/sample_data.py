"""Fictional records the demo videos show (`bench fi-tutorial-sample-data`). See docs/tutorial/videos.md.

Created once on a development site, in the default company; running it again adds nothing. Dates
are counted back from the day it runs, so some invoices are overdue.
"""

import json
import os

import frappe
from frappe.utils import add_days, today

DATA = os.path.join(os.path.dirname(__file__), "sample_data.json")
REMARK = "Tutorial sample data"


def create() -> None:
	if not frappe.conf.developer_mode:
		frappe.throw("Tutorial sample data goes on a development site (developer_mode).")
	with open(DATA) as f:
		data = json.load(f)
	company = frappe.defaults.get_global_default("company")
	for name in data["customers"]:
		make_customer(name)
	for name in data["suppliers"]:
		make_supplier(name)
	rates = {item["item_code"]: item["rate"] for item in data["items"]}
	for item in data["items"]:
		make_item(item)
	if not frappe.db.exists("Sales Invoice", {"remarks": REMARK}):
		for invoice in data["sales_invoices"]:
			make_sales_invoice(company, invoice, rates)
	for document in data["documents"]:
		make_document(document)
	for sessions in data["workflow_sessions"]:
		make_workflow_sessions(sessions)
	frappe.db.commit()


def make_customer(name: str) -> None:
	if frappe.db.exists("Customer", name):
		return
	frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Company",
			"customer_group": "Commercial",
			"territory": "Saudi Arabia",
		}
	).insert()


def make_supplier(name: str) -> None:
	if frappe.db.exists("Supplier", name):
		return
	frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_type": "Company",
			"supplier_group": "Local",
		}
	).insert()


def make_item(item: dict) -> None:
	if frappe.db.exists("Item", item["item_code"]):
		return
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item["item_code"],
			"item_group": item["item_group"],
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"standard_rate": item["rate"],
		}
	).insert()


def make_sales_invoice(company: str, invoice: dict, rates: dict) -> None:
	posting_date = add_days(today(), -invoice["posted_days_ago"])
	frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"customer": invoice["customer"],
			"set_posting_time": 1,
			"posting_date": posting_date,
			"due_date": add_days(today(), -invoice["due_days_ago"]),
			"remarks": REMARK,
			"items": [{"item_code": code, "qty": qty, "rate": rates[code]} for code, qty in invoice["items"]],
		}
	).insert().submit()


# The app's own records (packs, templates, logs, workflows...): `_key` finds one that exists, else the
# name its DocType is named by ("field:..." autoname).
def make_document(document: dict) -> None:
	doc = dict(document)
	key = doc.pop("_key", None)
	if key is None:
		autoname = frappe.get_meta(doc["doctype"]).autoname or ""
		key = doc[autoname.removeprefix("field:")]
	if frappe.db.exists(doc["doctype"], key):
		return
	for field, value in doc.items():
		if isinstance(value, dict):
			doc[field] = frappe.as_json(value)
	for row in (row for value in doc.values() if isinstance(value, list) for row in value):
		for field, value in row.items():
			if isinstance(value, list):
				row[field] = frappe.as_json(value)
	frappe.get_doc(doc).insert()


# Finished, open and abandoned conversations on a workflow, for Session Analytics: each `turns`
# messages long, the workflow's questions and short answers in turn.
def make_workflow_sessions(sessions: dict) -> None:
	workflow = frappe.get_doc("AI Workflow", sessions["workflow"])
	if frappe.db.exists("AI Conversation", {"workflow": workflow.name, "mode": "Workflow"}):
		return
	questions = [step.prompt_to_user for step in workflow.steps]
	for status in ("Completed", "Active", "Abandoned"):
		for _ in range(sessions.get(status, 0)):
			messages = [
				{"role": "assistant", "content": questions[(i // 2) % len(questions)]}
				if i % 2 == 0
				else {"role": "user", "content": "…"}
				for i in range(sessions["turns"])
			]
			frappe.get_doc(
				{
					"doctype": "AI Conversation",
					"title": workflow.title,
					"mode": "Workflow",
					"channel": "Desk",
					"status": status,
					"workflow": workflow.name,
					"messages": messages,
				}
			).insert()
