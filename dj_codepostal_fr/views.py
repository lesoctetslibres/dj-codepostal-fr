from django.http import JsonResponse, HttpRequest

from .utils import postal_codes_nearby, postal_codes_completion


def area_view(request: HttpRequest):

    postal_codes = request.GET.getlist("postal_codes[]", [])
    term = request.GET.get("term", "")
    completion = []

    if len(term) >= 3:
        completion += postal_codes_completion(term)

        completion = [{
            "id": value,
            "text": value
        } for value in completion if value not in postal_codes]

    res = []

    neighbors = []

    if postal_codes:
        neighbors = set([
            near for code in postal_codes
            for near in (postal_codes_nearby(postal_code=code) or [])
            if not term or near.startswith(term)
        ])
        # convert to list of dict and remove already selected items
        neighbors = [{"id": str(near), "text":str(near)} for near in neighbors if near not in postal_codes]

    if neighbors:
        res.append({"text": "À proximité", "children": neighbors})
    if completion:
        res += completion

    return JsonResponse({"err": "nil", "results": res})
