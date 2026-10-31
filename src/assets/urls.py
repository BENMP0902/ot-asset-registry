"""Rutas de la app assets. Con app_name, las URLs se nombran 'assets:list', 'assets:detail', etc."""

from django.urls import path

from . import views

app_name = "assets"                              # espacio de nombres: evita choques con otras apps

urlpatterns = [
    path("", views.asset_list, name="list"),
    path("activos/nuevo/", views.asset_register, name="register"),
    path("activos/<int:pk>/", views.asset_detail, name="detail"),          # <int:...> rechaza lo que no sea entero
    path("activos/<int:pk>/reubicar/", views.asset_relocate, name="relocate"),
    path("activos/<int:pk>/baja/", views.asset_decommission, name="decommission"),
    path("anomalias/", views.anomalies, name="anomalies"),
]
