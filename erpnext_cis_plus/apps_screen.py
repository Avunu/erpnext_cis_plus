# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""Keeps this app off the apps screen."""


def not_listed() -> bool:
	"""Say no to add_to_apps_screen, whose entry is only there for the About dialog's logo."""
	return False
