from django.db import models

class CodePostal(models.Model):
    code = models.CharField(primary_key=True, max_length=5)
    

    def __str__(self):
        return self.code

class CodePostalMany(models.ManyToManyField):

    def __init__(self, *args, **kwargs):
        super().__init__(to="dj_codepostal_fr.CodePostal", *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["to"]
        return name, path, args, kwargs
