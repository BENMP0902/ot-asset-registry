"""Fábricas de datos compartidas por la suite. La BD de pruebas ya trae los grupos (migración 0003)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from assets.models import AssetType, Zone


def make_user(username, group=None, **extra):
    """Crea un usuario (sin contraseña: no puede iniciar sesión real) y lo agrega a un grupo."""
    user = get_user_model().objects.create_user(username, **extra)
    if group:
        user.groups.add(Group.objects.get(name=group))   # antes de cualquier has_perm: no hay caché sucia
    return user


def make_catalog():
    """Un tipo de activo y dos zonas, suficientes para todos los flujos."""
    asset_type = AssetType.objects.create(name="Variador de frecuencia (VFD)")
    z1 = Zone.objects.create(code="Z-A1", name="Línea de ensamble 1")
    z2 = Zone.objects.create(code="Z-CE", name="Cuarto eléctrico")
    return asset_type, z1, z2
