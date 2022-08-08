from django.http import JsonResponse, HttpRequest

from .utils import complete_and_suggest


def area_view(request: HttpRequest):
    postal_codes = request.GET.getlist("postal_codes[]", [])
    term = request.GET.get("term", "")

    res = complete_and_suggest(postal_codes, term)
    return JsonResponse({"err": "nil", "results": res})
