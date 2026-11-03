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
	rates = {item["item_code"]: item["rate"] for item in data["items"]}
	for item in data["items"]:
		make_item(item)
	if not frappe.db.exists("Sales Invoice", {"remarks": REMARK}):
		for invoice in data["sales_invoices"]:
			make_sales_invoice(company, invoice, rates)
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
