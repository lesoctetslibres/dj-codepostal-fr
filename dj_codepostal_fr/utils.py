from collections import defaultdict
from datetime import datetime
import logging
from pytz import UTC
import re
import requests
from typing import Any, Dict, List, Optional, Union

from django.core.cache import cache
from django.utils.dateparse import parse_datetime

from dj_codepostal_fr.models import (
    CodePostal,
    CodePostalCompletions,
    CodePostalLocation,
)

logger = logging.getLogger("codepostal.utils")

# some meaningfull text and a random string
_cache_key_prefix = "codepostal.utils._AeL3zuay"


def _handle_api_errors(
    response: requests.Response, cache_key: str
) -> Union[bool, requests.Response]:
    if response.status_code == 200:
        return response

    if response.status_code == 429:
        # too many requests / throttling:
        # store False with timeout matching the throttling reset time
        reset_time = parse_datetime(response.json().get("reset_time", ""))
        timeout = reset_time - datetime.now(UTC)
        cache.set(cache_key, False, timeout=timeout.seconds + 1)
        return False

    # default
    logger.error(
        "%s: error %s: %s", response.url, response.status_code, response.json()
    )
    cache.set(cache_key, False)  # use default timeout, store False
    return False


def postal_codes_nearby(
    dist_km: int = 10,
    lon: Optional[float] = None,
    lat: Optional[float] = None,
    postal_code: Optional[str] = None,
):
    assert (lon is None) == (lat is None)
    assert (lon is not None) == (postal_code is None)
    cache_key = _cache_key_prefix + "nearby" + f"{dist_km}/{lon}/{lat}/{postal_code}"

    cached = cache.get(cache_key)
    if cached is not None:
        if not cached:
            return None
        return cached

    if postal_code is not None:
        coords = postal_code_location(postal_code)
        if not coords:
            return None
        lon = coords["lon"]
        lat = coords["lat"]

    response = _handle_api_errors(
        requests.get(
            "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
            params={
                "where": f'distance(coordonnees_gps,geom\'{{"type": "Point","coordinates":[{lon},{lat}]}}\',{dist_km}km)',
                "group_by": "code_postal",
                "limit": 30,
                "offset": 0,
                "timezone": "UTC",
            },
        ),
        cache_key,
    )
    if not response:
        return None
    else:
        result = [
            record["record"]["fields"]["code_postal"]
            for record in response.json()["records"]
        ]
        cache.set(cache_key, result, timeout=None)
        return result


def fetch_postal_code_locations():

    missing_locations = CodePostal.objects.filter(
        codepostallocation__isnull=True
    ).values_list("code", flat=True)
    if not missing_locations.exists():
        return 0

    cache_key = _cache_key_prefix + "multiple_locations"
    response = _handle_api_errors(
        requests.get(
            "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
            params={
                "select": "coordonnees_gps,code_postal",
                "where": " or ".join(
                    [f"code_postal={code}" for code in missing_locations]
                ),
                "limit": 30,
                "offset": 0,
                "timezone": "UTC",
            },
        ),
        cache_key,
    )
    if not response:
        return None

    json = response.json()
    if json["total_count"] > 0:
        coordinates = defaultdict(list)
        for record in json["records"]:
            coordinates[record["record"]["fields"]["code_postal"]].append(
                record["record"]["fields"]["coordonnees_gps"]
            )

        for postal_code, code_coord in coordinates.items():
            cache_key = _cache_key_prefix + "location" + postal_code
            lon = sum([coord["lon"] for coord in code_coord]) / len(code_coord)
            lat = sum([coord["lat"] for coord in code_coord]) / len(code_coord)
            result = {"lon": lon, "lat": lat}
            CodePostalLocation.objects.update_or_create(
                code=CodePostal.objects.get_or_create(code=postal_code)[0],
                defaults={"longitude": lon, "latitude": lat},
            )
            cache.set(cache_key, result, timeout=None)
        return len(coordinates.keys())

    return None


def postal_code_location(postal_code: Any) -> Union[None, Dict[str, float]]:
    """
    Renvoie le milieu des coordonnées des communes correspondant au code postal
    """
    # ensure the postal code is converted to string
    if not postal_code:
        return None

    postal_code = str(postal_code)
    cache_key = _cache_key_prefix + "location" + postal_code

    # 1. reading from cache
    cached = cache.get(cache_key)
    if cached is not None:
        if not cached:
            # see below, case where the API returns no records
            return None
        return cached

    # 2. reading from DB
    try:
        location = CodePostalLocation.objects.get(code=postal_code)
        if location.longitude is None or location.latitude is None:
            cache.set(cache_key, False, timeout=None)
            return None
        result = {"lon": location.longitude, "lat": location.latitude}
        cache.set(cache_key, result, timeout=None)
        return result
    except CodePostalLocation.DoesNotExist:
        # pass to reading from API
        pass

    # 3. reading from API
    response = _handle_api_errors(
        requests.get(
            "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
            params={
                "select": "coordonnees_gps",
                "where": f"code_postal={postal_code}",
                "limit": 30,
                "offset": 0,
                "timezone": "UTC",
            },
        ),
        cache_key,
    )

    if not response:
        return None
    else:
        json = response.json()
        if json["total_count"] > 0:
            coordinates = [
                record["record"]["fields"]["coordonnees_gps"]
                for record in json["records"]
            ]
            lon = sum([coord["lon"] for coord in coordinates]) / len(coordinates)
            lat = sum([coord["lat"] for coord in coordinates]) / len(coordinates)
            result = {"lon": lon, "lat": lat}
            CodePostalLocation.objects.update_or_create(
                code=CodePostal.objects.get_or_create(code=postal_code)[0],
                defaults={"longitude": lon, "latitude": lat},
            )
            cache.set(cache_key, result, timeout=None)
            return result
        else:
            # cache anyway
            CodePostalLocation.objects.update_or_create(
                code=CodePostal.objects.get_or_create(code=postal_code)[0],
                defaults={"longitude": None, "latitude": None},
            )
            cache.set(cache_key, False, timeout=None)
            return None


class _PostalCodesCompletion:

    regex = re.compile(r"[0-9]{3,5}")

    def _check_portion(self, code_portion):
        if not code_portion:
            return False
        if not self.regex.match(code_portion):
            logger.error(
                "code postal portion does not match pattern (%s)", code_portion
            )
            return False

        return True

    def _refine_results(self, code_portion, codes):
        if len(code_portion) > 3:
            # results are cached by 3 first digits only, need to refine
            return [code for code in codes if code.startswith(code_portion)]
        else:
            return codes

    def __call__(self, code_portion: str) -> List[str]:
        if not self._check_portion(code_portion):
            # FIXME: should raise ?
            return None

        code_portion_key = code_portion[:3]
        # cache by 3 first digits
        cache_key = _cache_key_prefix + "complete" + code_portion_key

        # 1. reading from Cache
        cached = cache.get(cache_key)
        if cached is not None:
            if not cached:
                return cached
            return self._refine_results(code_portion, cached)

        # 2. reading from DB
        try:
            result = CodePostalCompletions.complete(code_portion)
            cache.set(cache_key, result, timeout=None)
            return result
        except CodePostalCompletions.DoesNotExist:
            pass

        # 3. reading from API
        response = _handle_api_errors(
            requests.get(
                "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
                params={
                    "group_by": "code_postal",
                    "where": f"search(code_postal,'{code_portion_key}')",
                    "limit": 100,
                    "offset": 0,
                    "timezone": "UTC",
                },
            ),
            cache_key,
        )
        if not response:
            return None
        else:
            result = [
                record["record"]["fields"]["code_postal"]
                for record in response.json()["records"]
            ]
            CodePostalCompletions.from_list(code_portion_key, result).save()
            cache.set(cache_key, result, timeout=None)
            return self._refine_results(code_portion, result)


postal_codes_completion = _PostalCodesCompletion()

_postal_code_regex = re.compile(r"[0-9]{5}")


def is_candidate_postal_code(code):
    return bool(_postal_code_regex.match(code))
