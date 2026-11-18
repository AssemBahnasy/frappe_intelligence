"""Strings Frappe or ERPNext translate plainly wrong that the app shows only at run time, such as a
DocType's name in a card. Listed here so they are extracted into locale/main.pot and the app's own
translation wins (docs/guidelines/translations.md). Nothing imports this module."""

from frappe import _lt

STRINGS = (_lt("GL Entry"),)
