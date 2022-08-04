from typing import List, Optional
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


class CodePostalCompletions(models.Model):

    portion = models.CharField(
        primary_key=True, max_length=3, help_text="3 first digits"
    )
    endings = models.CharField(max_length=300, help_text="only store last 2 digits")

    def get_completions(self, portion: Optional[str] = None) -> List[str]:
        if portion:
            if not portion.startswith(self.portion):
                # check portion arg is valid
                raise ValueError(
                    "portion argument must start with self.portion. %s does not start with %s"
                    % (portion, self.portion)
                )
            if len(portion) > 3:
                return [
                    self.portion + ending
                    for ending in self.endings.split(",")
                    if ending.startswith(portion[3:])
                ]
            # else, default case
        # default case
        return [self.portion + ending for ending in self.endings.split(",")]

    @classmethod
    def complete(cls, portion: str) -> List[str]:
        """
        may raise DoesNotExist
        """
        completion = cls.objects.get(portion=portion[:3])
        return completion.get_completions(portion)

    @classmethod
    def from_list(cls, portion: str, completions: List[str]):
        if len(portion) != 3:
            raise ValueError("portion parameter must have exactly 3 digits")
        endings = [code[3:] for code in completions if code.startswith(portion)]
        if len(endings) != len(completions):
            raise ValueError(
                "completions parameter contains codes that do not start with portion"
            )
        endings = set(endings)  # remove duplicates
        return cls(portion=portion, endings=",".join(endings))


class CodePostalLocation(models.Model):
    """
    Center of all communes with the same postal code
    """

    code = models.OneToOneField(
        to=CodePostal, primary_key=True, on_delete=models.CASCADE
    )
    longitude = models.FloatField(null=True)
    latitude = models.FloatField(null=True)
