# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

from typing import Any
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.redis_wrapper import RedisWrapper

from erpnext_cis_plus.erpnext_cis_plus.hooks import address as address_hooks

NOMINATIM_ADDRESS: dict[str, str] = {
	"city": "Lancaster",
	"county": "Lancaster County",
	"state": "Pennsylvania",
	"postcode": "17602",
	"country": "United States",
}
NOMINATIM_RESULT: dict[str, Any] = {"lat": "40.0379", "lon": "-76.3055", "address": NOMINATIM_ADDRESS}


def redis() -> RedisWrapper:
	cache = frappe.cache
	assert cache is not None
	return cache


def nominatim_response(results):
	response = MagicMock()
	response.json.return_value = results
	return response


class GeocodingTestCase(IntegrationTestCase):
	"""Nominatim is mocked (tests never reach the network); the rate limit is tested on its own."""

	def setUp(self):
		get = patch.object(address_hooks.requests, "get", return_value=nominatim_response([NOMINATIM_RESULT]))
		self.get = get.start()
		self.addCleanup(get.stop)
		slot = patch.object(address_hooks, "acquire_rate_limit_slot", return_value=True)
		self.slot = slot.start()
		self.addCleanup(slot.stop)
