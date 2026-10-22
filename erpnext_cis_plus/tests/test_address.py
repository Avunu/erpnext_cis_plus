# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

import json
from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from erpnext_cis_plus.erpnext_cis_plus.hooks import address as address_hooks
from erpnext_cis_plus.tests.utils import (
	NOMINATIM_ADDRESS,
	NOMINATIM_RESULT,
	GeocodingTestCase,
	nominatim_response,
	redis,
)

DRAWN_POINT = json.dumps(
	{
		"type": "FeatureCollection",
		"features": [
			{
				"type": "Feature",
				"properties": {"point_type": "Point"},
				"geometry": {"type": "Point", "coordinates": [-76.1, 40.0]},
			}
		],
	}
)


def new_address(**fields):
	values = {
		"doctype": "Address",
		"address_title": "CIS Plus test",
		"address_type": "Billing",
		"address_line1": "1 Penn Square",
		"city": "Lancaster",
		"country": "United States",
	}
	values.update(fields)
	return frappe.get_doc(values)


class TestStateAbbreviation(IntegrationTestCase):
	def test_us_state_name_becomes_its_abbreviation(self):
		self.assertEqual(address_hooks.get_state_abbrev("Pennsylvania", "United States"), "PA")

	def test_unknown_us_state_is_kept(self):
		self.assertEqual(address_hooks.get_state_abbrev("Atlantis", "United States"), "Atlantis")

	def test_other_countries_are_kept(self):
		self.assertEqual(address_hooks.get_state_abbrev("Ontario", "Canada"), "Ontario")

	def test_empty_state_is_kept(self):
		self.assertIsNone(address_hooks.get_state_abbrev(None, "United States"))
		self.assertEqual(address_hooks.get_state_abbrev("", "United States"), "")


class TestRateLimit(IntegrationTestCase):
	def setUp(self):
		redis().delete(address_hooks.RATE_LIMIT_KEY)
		self.addCleanup(redis().delete, address_hooks.RATE_LIMIT_KEY)

	def test_one_request_per_interval(self):
		self.assertTrue(address_hooks.acquire_rate_limit_slot())
		with patch.object(address_hooks, "RATE_LIMIT_MAX_WAIT", 0):
			self.assertFalse(address_hooks.acquire_rate_limit_slot())

	def test_waits_for_the_slot_to_come_free(self):
		self.assertTrue(address_hooks.acquire_rate_limit_slot())
		with patch.object(address_hooks, "RATE_LIMIT_INTERVAL_MS", 200):
			redis().set(address_hooks.RATE_LIMIT_KEY, 1, px=200)
			self.assertTrue(address_hooks.acquire_rate_limit_slot())

	def test_no_redis_means_no_coordination(self):
		with patch.object(frappe, "cache", None):
			self.assertTrue(address_hooks.acquire_rate_limit_slot())


class TestGeolocateAddress(GeocodingTestCase):
	def test_sets_coordinates_and_fills_empty_fields(self):
		doc = new_address(country=None, city=None)
		address_hooks.geolocate_address(doc)

		self.assertEqual(doc.latitude, 40.0379)
		self.assertEqual(doc.longitude, -76.3055)
		self.assertEqual(doc.pincode, "17602")
		self.assertEqual(doc.country, "United States")
		self.assertEqual(doc.state, "PA")
		self.assertEqual(doc.county, "Lancaster County")
		self.assertEqual(doc.city, "Lancaster")

	def test_request_identifies_the_app_and_has_a_timeout(self):
		address_hooks.geolocate_address(new_address())

		self.get.assert_called_once()
		args, kwargs = self.get.call_args
		self.assertEqual(args, (address_hooks.NOMINATIM_URL,))
		self.assertEqual(kwargs["timeout"], address_hooks.REQUEST_TIMEOUT)
		self.assertTrue(kwargs["headers"]["User-Agent"].startswith("erpnext_cis_plus/"))
		self.assertIn("github.com/Avunu/erpnext_cis_plus", kwargs["headers"]["User-Agent"])
		self.assertEqual(kwargs["params"]["q"], "1 Penn Square, Lancaster, United States")
		self.assertEqual(kwargs["params"]["limit"], 1)

	def test_does_not_overwrite_fields_already_set(self):
		result = dict(NOMINATIM_RESULT, address={**NOMINATIM_ADDRESS, "city": None, "town": "Ephrata"})
		self.get.return_value = nominatim_response([result])
		doc = new_address(city="Lancaster", state="PA", pincode="17603", county="Lancaster")
		address_hooks.geolocate_address(doc)

		self.assertEqual(doc.city, "Lancaster")
		self.assertEqual(doc.state, "PA")
		self.assertEqual(doc.pincode, "17603")
		self.assertEqual(doc.county, "Lancaster")

	def test_town_or_village_fills_an_empty_city(self):
		result = dict(NOMINATIM_RESULT, address={"village": "Intercourse"})
		self.get.return_value = nominatim_response([result])
		doc = new_address(city=None)
		address_hooks.geolocate_address(doc)
		self.assertEqual(doc.city, "Intercourse")

	def test_no_result_leaves_the_address_alone(self):
		self.get.return_value = nominatim_response([])
		doc = new_address()
		address_hooks.geolocate_address(doc)
		self.assertFalse(doc.get("latitude"))
		self.assertFalse(doc.get("longitude"))

	def test_an_empty_address_is_not_looked_up(self):
		doc = frappe.get_doc({"doctype": "Address"})
		address_hooks.geolocate_address(doc)
		self.get.assert_not_called()

	def test_a_failed_lookup_does_not_block_the_save(self):
		for error in (requests.Timeout("timed out"), requests.ConnectionError("refused")):
			with self.subTest(error=error):
				self.get.side_effect = error
				doc = new_address()
				with patch.object(frappe, "log_error") as log_error:
					address_hooks.geolocate_address(doc)
				log_error.assert_called_once()
				self.assertFalse(doc.get("latitude"))

	def test_an_http_error_or_bad_json_does_not_block_the_save(self):
		bad_status = nominatim_response([])
		bad_status.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
		bad_json = nominatim_response(None)
		bad_json.json.side_effect = ValueError("Expecting value")
		for response in (bad_status, bad_json):
			with self.subTest(response=response):
				self.get.return_value = response
				doc = new_address()
				with patch.object(frappe, "log_error") as log_error:
					address_hooks.geolocate_address(doc)
				log_error.assert_called_once()
				self.assertFalse(doc.get("latitude"))

	def test_a_busy_service_skips_the_lookup(self):
		self.slot.return_value = False
		doc = new_address()
		address_hooks.geolocate_address(doc)
		self.get.assert_not_called()
		self.assertFalse(doc.get("latitude"))


class TestGeneratePoint(IntegrationTestCase):
	def test_point_from_coordinates(self):
		doc = new_address(latitude=40.0379, longitude=-76.3055)
		address_hooks.generate_point(doc)
		location = json.loads(doc.location)
		self.assertEqual(location["features"][0]["geometry"]["coordinates"], [-76.3055, 40.0379])

	def test_no_point_without_coordinates(self):
		doc = new_address()
		address_hooks.generate_point(doc)
		self.assertFalse(doc.get("location"))

	def test_a_drawn_point_without_coordinates_is_kept(self):
		doc = new_address(location=DRAWN_POINT)
		address_hooks.generate_point(doc)
		self.assertEqual(doc.location, DRAWN_POINT)

	def test_cleared_coordinates_clear_the_point(self):
		doc = new_address(location=DRAWN_POINT)
		doc.flags.coordinates_cleared = True
		address_hooks.generate_point(doc)
		self.assertFalse(doc.get("location"))


class TestAddressHooks(GeocodingTestCase):
	"""The doc_events on a saved Address."""

	def test_saving_geocodes_once_until_the_address_changes(self):
		doc = new_address().insert()
		self.assertEqual(self.get.call_count, 1)
		self.assertEqual(float(doc.latitude), 40.0379)
		self.assertEqual(
			json.loads(doc.location)["features"][0]["geometry"]["coordinates"], [-76.3055, 40.0379]
		)

		doc.reload()
		doc.address_title = "CIS Plus test, renamed"
		doc.save()
		self.assertEqual(self.get.call_count, 1, "an unchanged address is not looked up again")

		doc.address_line1 = "2 Penn Square"
		doc.save()
		self.assertEqual(self.get.call_count, 2)

	def test_an_address_without_coordinates_is_retried(self):
		self.get.return_value = nominatim_response([])
		doc = new_address().insert()
		doc.address_title = "CIS Plus test, retried"
		doc.save()
		self.assertEqual(self.get.call_count, 2)

	def test_a_failed_lookup_of_a_changed_address_clears_its_coordinates_and_retries(self):
		doc = new_address().insert()
		self.assertEqual(float(doc.latitude), 40.0379)

		self.get.side_effect = requests.Timeout("timed out")
		doc.address_line1 = "99 Other Road"
		doc.city = "Pittsburgh"
		with patch.object(frappe, "log_error"):
			doc.save()
		doc.reload()
		self.assertEqual(self.get.call_count, 2)
		self.assertFalse(doc.latitude)
		self.assertFalse(doc.longitude)
		self.assertFalse(doc.location)

		self.get.side_effect = None
		self.get.return_value = nominatim_response([dict(NOMINATIM_RESULT, lat="40.4406", lon="-79.9959")])
		doc.save()
		doc.reload()
		self.assertEqual(self.get.call_count, 3, "saving again retries the lookup")
		self.assertEqual(float(doc.latitude), 40.4406)
		self.assertEqual(float(doc.longitude), -79.9959)

	def test_a_changed_address_with_no_match_or_no_slot_loses_its_old_coordinates(self):
		for case in ("no match", "busy"):
			with self.subTest(case=case):
				self.get.return_value = nominatim_response([NOMINATIM_RESULT])
				self.slot.return_value = True
				doc = new_address().insert()
				self.assertEqual(float(doc.latitude), 40.0379)

				if case == "no match":
					self.get.return_value = nominatim_response([])
				else:
					self.slot.return_value = False
				doc.address_line1 = "99 Other Road"
				doc.save()
				doc.reload()
				self.assertFalse(doc.latitude)
				self.assertFalse(doc.location)

	def test_a_failed_lookup_keeps_coordinates_and_points_the_user_entered(self):
		"""Only coordinates looked up for an earlier version of the address are cleared."""
		outcomes = {
			"no match": lambda: setattr(self.get, "return_value", nominatim_response([])),
			"failed": lambda: setattr(self.get, "side_effect", requests.Timeout("timed out")),
			"busy": lambda: setattr(self.slot, "return_value", False),
		}
		for case, fail in outcomes.items():
			with self.subTest(case=case), patch.object(frappe, "log_error"):
				fail()

				# a new Address with coordinates (an import, the API)
				doc = new_address(latitude=40.0, longitude=-76.1).insert()
				doc.reload()
				self.assertEqual(float(doc.latitude), 40.0)
				self.assertEqual(float(doc.longitude), -76.1)
				self.assertEqual(
					json.loads(doc.location)["features"][0]["geometry"]["coordinates"], [-76.1, 40.0]
				)

				# a point drawn on the map of an Address without coordinates
				doc = new_address().insert()
				doc.location = DRAWN_POINT
				doc.save()
				doc.address_title = "CIS Plus test, drawn"
				doc.save()
				doc.reload()
				self.assertEqual(doc.location, DRAWN_POINT)

				# coordinates entered with the address change they belong to
				doc.address_line1 = "99 Farm Lane"
				doc.latitude = 40.1
				doc.longitude = -76.2
				doc.save()
				doc.reload()
				self.assertEqual(float(doc.latitude), 40.1)
				self.assertEqual(float(doc.longitude), -76.2)

				self.get.return_value = nominatim_response([NOMINATIM_RESULT])
				self.get.side_effect = None
				self.slot.return_value = True

	def test_an_address_saved_without_a_new_point_leaves_parties_alone(self):
		doc = new_address().insert()
		with patch.object(frappe.db, "set_value", wraps=frappe.db.set_value) as set_value:
			doc.address_line2 = "Suite 2"
			doc.save()
		self.assertNotIn("Customer", [call.args[0] for call in set_value.call_args_list])
