from django.http import JsonResponse, HttpRequest

from .utils import (
    postal_codes_nearby,
    postal_codes_completion,
    is_candidate_postal_code,
)


def area_view(request: HttpRequest):
    postal_codes = request.GET.getlist("postal_codes[]", [])
    term = request.GET.get("term", "")
    completion = []

    if len(term) >= 3:
        term_completion = postal_codes_completion(term)
        if term_completion is None:
            # error upstream
            if is_candidate_postal_code(term):
                # allow to force a postal code that match the postal code regex
                term_completion = [{"id": term, "text": term}]
            else:
                term_completion = []
            completion.append(
                {
                    "text": "Erreur de connexion au serveur LaPoste",
                    "children": term_completion,
                }
            )
        else:
            completion += [
                {"id": value, "text": value}
                for value in term_completion
                if value not in postal_codes
            ]

    res = []

    neighbors = []

    if postal_codes:
        # get neighbors of the last 5 postal_codes only
        # for performance and because of LaPoste API rate limitations
        neighbors = set(
            [
                near
                for code in postal_codes[-5:]
                for near in (postal_codes_nearby(postal_code=code) or [])
                if not term or near.startswith(term)
            ]
        )
        # convert to list of dict and remove already selected items
        neighbors = [
            {"id": str(near), "text": str(near)}
            for near in neighbors
            if near not in postal_codes
        ]

    if neighbors:
        res.append({"text": "À proximité", "children": neighbors})
    if completion:
        res += completion

    return JsonResponse({"err": "nil", "results": res})
