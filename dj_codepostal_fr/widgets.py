from django_select2.forms import HeavySelect2MultipleWidget


class MultiplePostalCodesWithSuggest(HeavySelect2MultipleWidget):
    # dependent_fields={"postal_codes": "postal_codes"}

    def __init__(self, *args, **kwargs):
        if "data_view" not in kwargs:
            kwargs["data_view"] = "codepostal-nearby-select2"
        super().__init__(*args, **kwargs)

    def render(self, *args, **kwargs):
        self.dependent_fields[kwargs["name"]]="postal_codes"
        # the "_":"_" is a hack of django-select2 for inhibiting reset of postal_codes on postal_codes change
        self.dependent_fields["_"]="_"
        return super().render(*args, **kwargs)

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        attrs["data-minimum-input-length"] = 0
        return attrs
