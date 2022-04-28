import logging
from math import fabs
import re
import requests
from typing import Any, Dict, List, Optional, Union

from django.core.cache import cache

logger = logging.getLogger("codepostal.utils")

# some meaningfull text and a random string
_cache_key_prefix = "codepostal.utils._AeL3zuay"


def postal_codes_nearby(dist_km: int = 10,
                        lon: Optional[float] = None,
                        lat: Optional[float] = None,
                        postal_code: Optional[str] = None):
    assert (lon is None) == (lat is None)
    assert (lon is not None) == (postal_code is None)
    cache_key = _cache_key_prefix+"nearby"+f"{dist_km}/{lon}/{lat}/{postal_code}"

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

    response = requests.get(
        "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
        params={
            "where":
            f"distance(coordonnees_gps,geom'{{\"type\": \"Point\",\"coordinates\":[{lon},{lat}]}}',{dist_km}km)",
            "group_by": "code_postal",
            "limit": 30,
            "offset": 0,
            "timezone": "UTC"
        })
    if response.status_code == 200:
        result = [
            record["record"]["fields"]["code_postal"]
            for record in response.json()["records"]
        ]
        cache.set(cache_key, result, timeout=None)
        return result

    cache.set(cache_key, False) # use default timeout, store False
    logger.error("postal_codes_nearby: datanova.laposte.fr error %s: %s",
                 response.status_code, response.json())


def postal_code_location(postal_code: Any) -> Union[None, Dict[str, float]]:
    """
    Renvoie le milieu des coordonnées des communes correspondant au code postal
    """
    # ensure the postal code is converted to string
    if not postal_code:
        return None

    postal_code = str(postal_code)
    cache_key = _cache_key_prefix + "location"+postal_code

    cached = cache.get(cache_key)
    if cached is not None:
        if not cached:
            # see below, case where the API returns no records
            return None
        return cached

    response = requests.get(
        "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
        params={
            "select": "coordonnees_gps",
            "where": f"code_postal={postal_code}",
            "limit": 30,
            "offset": 0,
            "timezone": "UTC"
        })

    if response.status_code == 200:
        json = response.json()
        if json["total_count"] > 0:
            coordinates = [
                record["record"]["fields"]["coordonnees_gps"]
                for record in json["records"]
            ]
            lon = sum([coord["lon"]
                       for coord in coordinates]) / len(coordinates)
            lat = sum([coord["lat"]
                       for coord in coordinates]) / len(coordinates)
            result = {"lon": lon, "lat": lat}
            cache.set(cache_key, result, timeout=None)
            return result
        else:
            # cache anyway
            cache.set(cache_key, False, timeout=None)

    logger.error("postal_code_location: datanova.laposte.fr error %s: %s",
                 response.status_code, response.json())

    cache.set(cache_key, False) # use default timeout
    return None

class _PostalCodesCompletion:

    regex = re.compile(r"[0-9]{1,5}")

    def _check_portion(self, code_portion):
        if not code_portion:
            return False
        if not self.regex.match(code_portion):
            logger.error("code postal portion does not match pattern (%s)", code_portion)
            return False

        return True


    def __call__(self, code_portion: str) -> List[str]:
        if not self._check_portion(code_portion):
            return []

        postal_code = str(code_portion)
        cache_key = _cache_key_prefix + "complete" + code_portion

        cached = cache.get(cache_key)
        if cached is not None:
            return cached


        response = requests.get(
            "https://datanova.laposte.fr/api/v2/catalog/datasets/laposte_hexasmal/records",
            params={
                "group_by": "code_postal",
                "where": f"search(code_postal,'{code_portion}')",
                "limit": 30,
                "offset": 0,
                "timezone": "UTC"
            })
        if response.status_code == 200:
            result = [
                record["record"]["fields"]["code_postal"]
                for record in response.json()["records"]
            ]
            cache.set(cache_key, result, timeout=None)
            return result

        cache.set(cache_key, []) # use default timeout, store empty result
        logger.error(
            "postal_codes_completion: datanova.laposte.fr error %s: %s",
            response.status_code, response.json())
        return []


postal_codes_completion = _PostalCodesCompletion()