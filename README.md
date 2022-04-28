# dj-codepostal-fr

`dj-codepostal-fr` is a Django app to manage French zip-codes that uses [La Poste open API (datanova)](https://datanova.laposte.fr/explore/).

The project is in alpha, more features are required. But it is used in production projects.


## Quickstart

1. Install with pip:

    ```shell
    pip install "dj_codepostal_fr @ git+https://github.com/lesoctetslibres/dj-codepostal-fr.git@master"
    ```

2. Add `dj_codepostal_fr` to `INSTALLED_APPS`:

    ```py
    INSTALLED_APPS = [
            ...
            'dj_codepostal_fr',
        ]
    ```

3. Include the dj_codepostal_fr URLconf in your project urls.py like this:

    ```py
    urlpatterns += [
        path("utils/", include('dj_codepostal_fr.urls')),
    ]
    ```

4. Add a `CodePostalMany` field in one of your model:

   ```py
   from dj_codepostal_fr.models import CodePostalMany

   class MyModel(models.Model):
       postal_codes = CodePostalMany()
    ```

5. Create a form using the `MultiplePostalCodesField`:

    ```py
    from dj_codepostal_fr.fields import MultiplePostalCodesField

    class MyForm(forms.ModelForm):
        postal_codes = MultiplePostalCodesField()

    ```

6. Run `python manage.py migrate` to create the models
7. Run your server and test.

## Features

* Widgets: auto-complete (with select2) with existing zip-codes, and zip-codes near already selected ones ("nearby" suggestions);
* Form Fields: validate against the La Poste API for official zip-codes;
* Model Fiels: drop-in many-to-many field to postal codes;
* Model: model representing postal codes;
* cache: use cache to reduce the number of calls to La Poste API and improve performance.

### Desired features

* work with commune names and INSEE codes;
* configurable nearby search (distance,...);
* visualization tools (maps);
* interface with official address geocoding from [adresse.data.gouv.fr](https://adresse.data.gouv.fr/api-doc/adresse)
* and many more...
