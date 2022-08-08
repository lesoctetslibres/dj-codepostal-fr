from datetime import datetime
from django.core.cache import cache
from re import L
from unittest import mock
from dj_codepostal_fr.models import CodePostalCompletions

from dj_codepostal_fr.utils import (
    DatanovaThrottlingException,
    complete_and_suggest,
    postal_code_location,
    postal_codes_completion,
)
from django.test import TestCase
from pytz import UTC


class MockResponse:
    def __init__(self, status_code, json=None):
        self.status_code = status_code
        self._json = json

    def json(self):
        return self._json


class TestApiError(TestCase):
    @mock.patch("requests.get")
    def test_location(self, mock_call):
        mock_call.return_value = MockResponse(
            status_code=429, json={"reset_time": datetime.now(tz=UTC).isoformat()}
        )
        with self.assertRaises(DatanovaThrottlingException):
            postal_code_location("32100")

    @mock.patch("requests.get")
    def test_complete_and_suggest(self, mock_call):
        """
        Test that no results are returned, and error messages are displayed
        """
        mock_call.return_value = MockResponse(
            status_code=429, json={"reset_time": datetime.now(tz=UTC).isoformat()}
        )

        res = complete_and_suggest(["32100"], term="322")
        self.assertEqual(len(res), 2)
        for item in res:
            self.assertIn("text", item)
            self.assertIn("Impossible d'obtenir", item["text"])
            self.assertEqual(len(item.get("children", [])), 0)

    @mock.patch("requests.get")
    def test_complete_and_suggest_default(self, mock_call):
        """
        Test that no results are returned, and error messages are displayed
        """
        mock_call.return_value = MockResponse(
            status_code=429, json={"reset_time": datetime.now(tz=UTC).isoformat()}
        )

        res = complete_and_suggest(["32100"], term="32288")
        self.assertEqual(len(res), 2)
        found = False
        for item in res:
            self.assertIn("text", item)
            self.assertIn("Impossible d'obtenir", item["text"])
            if item["text"] == "Impossible d'obtenir les suggestions de codes postaux":
                found = True
                self.assertEqual(len(item["children"]), 1)
                self.assertEqual(item["children"][0]["id"], "32288")
            else:
                self.assertEqual(len(item.get("children", [])), 0)

        self.assertTrue(found)


class TestApiErrorWithDbValues(TestCase):
    def setUp(self):
        CodePostalCompletions.objects.bulk_create(
            [
                CodePostalCompletions(portion=p, endings=e)
                for p, e in [
                    ("321", "00,11,22,33"),
                    ("322", "01,12,23,34"),
                ]
            ]
        )

    @mock.patch("requests.get")
    def test_complete_and_suggest_stored(self, mock_call):
        """
        Test that no results are returned, and error messages are displayed
        """
        mock_call.return_value = MockResponse(
            status_code=429, json={"reset_time": datetime.now(tz=UTC).isoformat()}
        )

        res = complete_and_suggest(["32100"], term="322")
        self.assertEqual(len(res), 5)
        suggests = []
        messages = []
        for item in res:
            if "id" in item:
                suggests.append(item["id"])
            else:
                messages.append(item["text"])
        self.assertEqual(len(suggests), 4)
        (self.assertIn(code, suggests) for code in ["32201", "32212", "32223", "32234"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Impossible d'obtenir les suggestions à proximité", messages[0])

    @mock.patch("requests.get")
    def test_complete_and_suggest_stored_no_default(self, mock_call):
        """
        Test that no results are returned, and error messages are displayed
        """
        mock_call.return_value = MockResponse(
            status_code=429, json={"reset_time": datetime.now(tz=UTC).isoformat()}
        )

        res = complete_and_suggest(["32100"], term="32288")
        self.assertEqual(len(res), 2)
        suggests = []
        messages = []
        for item in res:
            self.assertNotIn("id", item)
            messages.append(item["text"])
            self.assertEqual(len(item["children"]), 0)
        self.assertEqual(len(suggests), 0)
        self.assertEqual(len(messages), 2)
        self.assertIn("Impossible d'obtenir les suggestions à proximité", messages)
        self.assertIn("Aucun code postal ne correspond", messages)


class TestCached(TestCase):
    def setUp(self):
        cache.clear()
        _cache_key_prefix = "codepostal.utils._AeL3zuay"
        nearby_key = _cache_key_prefix + "nearby" + f"10/None/None/32200"
        complete_key = _cache_key_prefix + "complete321"

        cache.set(nearby_key, ["33200", "01200", "87200"])
        cache.set(complete_key, ["32100", "32111", "32122"])

    def tearDown(self):
        super().tearDown()
        cache.clear()

    @mock.patch("dj_codepostal_fr.utils.postal_code_location")
    def test_nearby(self, mock_postal_code_location):
        res = complete_and_suggest(["32200"], "")
        self.assertEqual(len(res), 1)
        (
            self.assertIn(code, [item["id"] for item in res[0]])
            for code in ["33200", "01200", "87200"]
        )

        mock_postal_code_location.assert_not_called()

    @mock.patch("dj_codepostal_fr.utils._call")
    def test_complete(self, mock_call):
        res = complete_and_suggest([], "321")
        self.assertEqual(len(res), 3)
        (
            self.assertIn(code, [item["id"] for item in res])
            for code in ["32100", "32111", "32122"]
        )

        mock_call.assert_not_called()

    @mock.patch("dj_codepostal_fr.utils._call")
    def test_complete_4digits(self, mock_call):
        res = complete_and_suggest([], "3211")
        self.assertEqual(len(res), 1)
        (self.assertIn(code, [item["id"] for item in res]) for code in ["32111"])

        mock_call.assert_not_called()


class TestApiResults(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        super().tearDown()
        cache.clear()

    @mock.patch("requests.get")
    def test_completion(self, mock_get):
        mock_get.return_value = MockResponse(
            200,
            {
                "records": [
                    {"record": {"fields": {"code_postal": "32201"}}},
                    {"record": {"fields": {"code_postal": "32202"}}},
                    {"record": {"fields": {"code_postal": "32203"}}},
                ]
            },
        )

        res = complete_and_suggest([], "322")
        self.assertEqual(len(res), 3, res)

    @mock.patch("requests.get")
    def test_completion_nothing(self, mock_get):
        mock_get.return_value = MockResponse(
            200,
            {"records": []},
        )

        res = complete_and_suggest([], "322")
        self.assertEqual(len(res), 1, res)
        self.assertEqual(res[0]["text"], "Aucun code postal ne correspond")

    @mock.patch("requests.get")
    def test_nearby(self, mock_get):
        mock_get.return_value = MockResponse(
            200,
            {
                "total_count": 3,
                "records": [
                    {
                        "record": {
                            "fields": {"coordonnees_gps": {"lon": 42.00, "lat": 0}}
                        }
                    },
                    {
                        "record": {
                            "fields": {"coordonnees_gps": {"lon": 43.00, "lat": 1}}
                        }
                    },
                    {
                        "record": {
                            "fields": {"coordonnees_gps": {"lon": 41.00, "lat": -1}}
                        }
                    },
                ],
            },
        )

        pos = postal_code_location("00000")
        self.assertAlmostEqual(pos["lon"], 42)
        self.assertAlmostEqual(pos["lat"], 0)

    @mock.patch("requests.get")
    @mock.patch("dj_codepostal_fr.utils.postal_code_location")
    def test_complete_nearby(self, mock_location, mock_get):
        mock_location.return_value = {"lon": 42.0, "lat": 0.0}
        mock_get.return_value = MockResponse(
            200,
            {
                "records": [
                    {"record": {"fields": {"code_postal": "32100"}}},
                    {"record": {"fields": {"code_postal": "32300"}}},
                    {"record": {"fields": {"code_postal": "87010"}}},
                ]
            },
        )

        res = complete_and_suggest(["32000"], "")
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0]["children"]), 3)
        self.assertEqual(
            {item["id"] for item in res[0]["children"]}, {"32100", "32300", "87010"}
        )

    @mock.patch("requests.get")
    @mock.patch("dj_codepostal_fr.utils.postal_code_location")
    @mock.patch("dj_codepostal_fr.utils.postal_codes_completion")
    def test_complete_nearby_with_portion(self, mock_completion, mock_location, mock_get):
        mock_completion.return_value = ["32110", "32120"]
        mock_location.return_value = {"lon": 42.0, "lat": 0.0}
        mock_get.return_value = MockResponse(
            200,
            {
                "records": [
                    {"record": {"fields": {"code_postal": "32100"}}},
                    {"record": {"fields": {"code_postal": "32300"}}},
                    {"record": {"fields": {"code_postal": "87010"}}},
                ]
            },
        )

        res = complete_and_suggest(["32000"], "321")
        self.assertEqual(len(res), 3, res)
        completion = []
        nearby = []
        for item in res:
            if "À proximité" in item["text"]:
                nearby += [x["id"] for x in item["children"]]
            else:
                completion.append(item["id"])

        self.assertEqual(set(completion), {"32110", "32120"})
        self.assertEqual(set(nearby), {"32100"})
