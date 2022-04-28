from django import forms
import re

from .widgets import MultiplePostalCodesWithSuggest

class MultiplePostalCodesField(forms.MultipleChoiceField):
    widget = MultiplePostalCodesWithSuggest

    match_regex = re.compile(r"[0-9]{5}")

    def valid_value(self, value: str) -> bool:
        return len(value) == 5 and self.match_regex.match(value)
