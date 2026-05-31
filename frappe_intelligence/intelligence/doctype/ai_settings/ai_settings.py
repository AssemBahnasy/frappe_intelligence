# Copyright (c) 2026, AssemBahnasy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

_LANG_CACHE_KEY = "fi_response_languages"
_ROUTE_MAP_CACHE_KEY = "fi_route_map"
_WIDGET_ROLES_CACHE_KEY = "fi_widget_roles"


class AISettings(Document):
	def on_update(self):
		frappe.cache().delete_value(_LANG_CACHE_KEY)
		frappe.cache().delete_value(_ROUTE_MAP_CACHE_KEY)
		frappe.cache().delete_value(_WIDGET_ROLES_CACHE_KEY)
