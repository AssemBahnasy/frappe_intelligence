"""Who may use the assistant and Agent mode, and the patch that moved access to the role; over fakes."""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

import frappe

from frappe_intelligence.api import chat
from frappe_intelligence.patches.v1_0 import intelligence_user_role
from frappe_intelligence.utils import access


class TestAssistantAccess(TestCase):
	def can_use(self, roles, user="someone@example.com"):
		with patch.object(access.frappe, "get_roles", return_value=roles):
			return access.can_use_assistant(user)

	def test_either_role_opens_it(self):
		self.assertTrue(self.can_use(["Desk User", access.USER_ROLE]))
		self.assertTrue(self.can_use(["Desk User", access.AGENT_ROLE]))

	def test_closed_without_a_role(self):
		self.assertFalse(self.can_use(["Desk User", "Accounts User"]))

	def test_needs_a_desk_user(self):
		self.assertFalse(self.can_use([access.USER_ROLE]))

	def test_never_a_guest(self):
		self.assertFalse(self.can_use(["Desk User", access.USER_ROLE], user="Guest"))


class TestAdministrator(TestCase):
	"""Administrator follows the roles ticked on its User form, not Frappe's every-role answer."""

	def ticked(self, roles):
		user = frappe._dict(roles=[frappe._dict(role=role) for role in roles])
		settings = frappe._dict(allow_agent_mode=1)
		return patch.object(
			access.frappe,
			"get_cached_doc",
			side_effect=lambda doctype, name=None: user if doctype == "User" else settings,
		)

	def test_unticked_roles_close_it(self):
		with self.ticked(["System Manager"]), patch.object(access.frappe, "get_roles") as get_roles:
			self.assertFalse(access.can_use_assistant("Administrator"))
		get_roles.assert_not_called()

	def test_ticked_role_opens_it(self):
		with self.ticked([access.USER_ROLE]):
			self.assertTrue(access.can_use_assistant("Administrator"))

	def test_agent_mode_needs_the_ticked_agent_role(self):
		with self.ticked([access.USER_ROLE]), patch.object(access, "_", side_effect=lambda text: text):
			self.assertIsNotNone(access.agent_mode_refusal("Administrator"))
		with self.ticked([access.AGENT_ROLE]):
			self.assertIsNone(access.agent_mode_refusal("Administrator"))


class TestAgentMode(TestCase):
	def refusal(self, switched_on, roles):
		settings = frappe._dict(allow_agent_mode=switched_on)
		with (
			patch.object(access.frappe, "get_cached_doc", return_value=settings),
			patch.object(access.frappe, "get_roles", return_value=roles),
			patch.object(access, "_", side_effect=lambda text: text),
		):
			return access.agent_mode_refusal("someone@example.com")

	def test_off_in_settings_closes_it_for_everyone(self):
		self.assertIn("AI Settings", self.refusal(0, ["Desk User", access.AGENT_ROLE]))

	def test_open_with_the_agent_role(self):
		self.assertIsNone(self.refusal(1, ["Desk User", access.AGENT_ROLE]))

	def test_closed_with_only_the_user_role(self):
		self.assertIn("administrator", self.refusal(1, ["Desk User", access.USER_ROLE]))

	def test_system_manager_does_not_get_it_by_itself(self):
		self.assertIn("administrator", self.refusal(1, ["Desk User", access.USER_ROLE, "System Manager"]))


class TestAgentModeOnSend(TestCase):
	def test_refused_with_the_reason(self):
		reason = "You have not been given Agent mode. Ask your administrator."
		with patch.object(chat, "agent_mode_refusal", return_value=reason):
			with self.assertRaises(frappe.PermissionError) as raised:
				chat._validated_mode("Agent")
		self.assertIn(reason, str(raised.exception))

	def test_ask_mode_needs_no_right(self):
		with patch.object(chat, "agent_mode_refusal", return_value="closed") as refusal:
			self.assertEqual(chat._validated_mode("Ask"), "Ask")
		refusal.assert_not_called()


class TestRolePatch(TestCase):
	def users(self, allowed_roles, users, with_role):
		def get_all(doctype, **kwargs):
			return users if doctype == "User" else with_role

		with patch.object(intelligence_user_role.frappe, "get_all", side_effect=get_all):
			return intelligence_user_role.users_with_access(allowed_roles)

	def test_no_allowed_roles_meant_every_desk_user(self):
		self.assertEqual(self.users([], ["a@x.com", "b@x.com"], []), ["a@x.com", "b@x.com"])

	def test_allowed_roles_keep_only_their_users(self):
		self.assertEqual(self.users(["Accounts User"], ["a@x.com", "b@x.com"], ["b@x.com"]), ["b@x.com"])

	def test_administrator_always_had_access(self):
		self.assertEqual(self.users(["Accounts User"], ["Administrator", "a@x.com"], []), ["Administrator"])
