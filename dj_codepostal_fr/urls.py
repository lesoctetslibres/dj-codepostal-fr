from django.urls import path
from .views import area_view

urlpatterns = [
    path("codepostal/nearby/", area_view, name="codepostal-nearby-select2"),
]
