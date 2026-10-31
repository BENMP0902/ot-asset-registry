"""
Capa de servicios de OT-Asset-Registry.

Aquí vive la lógica de negocio que involucra VARIAS filas o la identidad del usuario:
- Autorización (permisos de negocio), verificada donde ocurre la acción, no en la UI.
- Atomicidad: el alta crea el Asset y su CHECK_IN juntos, o no crea nada.
- Reglas que una restricción CHECK no puede ver: "no mover un activo dado de baja".
- Consultas de estado derivado SIN el problema N+1.

Las vistas (Bloque 4b) solo traducen HTTP <-> llamadas a estas funciones.
Convención de errores:
- PermissionDenied -> el usuario no puede hacerlo   (Django lo convierte en HTTP 403)
- ValidationError  -> la operación viola una regla   (la vista lo muestra en el formulario)
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import OuterRef, Subquery

from .models import Asset, AssetMovement, MovementType


# -----------------------------------------------------------------------------
# Utilidades internas
# -----------------------------------------------------------------------------

def _require_perm(user, codename):
    """Autoriza o lanza PermissionDenied. Ocultar un botón NO es control de acceso."""
    # has_perm ya devuelve False para usuarios inactivos (is_active=False)
    if user is None or not user.is_authenticated or not user.has_perm(f"assets.{codename}"):
        raise PermissionDenied(f"No tienes permiso para esta operación ({codename}).")


def _lock_asset(asset):
    """
    Bloquea la fila del activo hasta que termine la transacción.
    En PostgreSQL emite SELECT ... FOR UPDATE: si dos usuarios mueven el MISMO activo
    a la vez, el segundo espera al primero y lee su movimiento (evita CWE-362, race condition).
    En SQLite se ignora: la propia BD serializa las escrituras.
    """
    return Asset.objects.select_for_update().get(pk=asset.pk)


def _last_movement_or_error(asset):
    """Último movimiento de un activo OPERATIVO. Regla de varias filas: un CHECK no la puede ver."""
    last = asset.last_movement()
    if last is None:
        raise ValidationError("El activo no tiene alta registrada (anomalía); no admite movimientos.")
    if last.movement_type == MovementType.DECOMMISSION:
        raise ValidationError("El activo está dado de baja; no admite más movimientos.")
    return last


# -----------------------------------------------------------------------------
# Comandos: cambian el estado (siempre dentro de una transacción)
# -----------------------------------------------------------------------------

def register_asset(*, user, tag, name, asset_type, zone, description="", note=""):
    """UC-04: alta = Asset + movimiento CHECK_IN, de forma ATÓMICA."""
    _require_perm(user, "register_checkin")
    if zone is None:
        raise ValidationError({"zone": "El alta requiere una zona inicial."})

    with transaction.atomic():                       # todo o nada: nunca queda un activo sin CHECK_IN
        asset = Asset(
            tag=tag.strip(),                         # normaliza: " VFD-001 " y "VFD-001" son el mismo
            name=name.strip(),
            asset_type=asset_type,
            description=description,
        )
        asset.full_clean()                           # valida longitudes, obligatorios y unicidad del tag
        try:
            asset.save()
        except IntegrityError as exc:                # carrera: otro usuario registró el mismo tag entre
            raise ValidationError(                   # full_clean() y save(). La BD tiene la última palabra.
                {"tag": "Ya existe un activo con esta etiqueta."}
            ) from exc
        AssetMovement.objects.create(
            asset=asset,
            movement_type=MovementType.CHECK_IN,
            to_zone=zone,
            performed_by=user,                       # la firma sale de la sesión, nunca del formulario
            note=note,
        )
    return asset


def relocate_asset(*, user, asset, to_zone, note=""):
    """UC-07: reubicación. El ORIGEN lo deriva el servidor; el cliente solo elige el destino."""
    _require_perm(user, "relocate_asset")
    if to_zone is None:
        raise ValidationError({"to_zone": "Selecciona la zona destino."})

    with transaction.atomic():
        asset = _lock_asset(asset)                   # relee el activo con la fila bloqueada
        last = _last_movement_or_error(asset)
        if last.to_zone_id == to_zone.pk:
            raise ValidationError({"to_zone": "El activo ya está en esa zona."})
        return AssetMovement.objects.create(
            asset=asset,
            movement_type=MovementType.RELOCATION,
            from_zone_id=last.to_zone_id,            # derivado del ledger: el usuario no puede mentir sobre el origen
            to_zone=to_zone,
            performed_by=user,
            note=note,
        )


def decommission_asset(*, user, asset, note):
    """UC-08: baja. Exclusiva del Administrador y SIEMPRE con motivo (trazabilidad)."""
    _require_perm(user, "decommission_asset")
    if not (note or "").strip():
        raise ValidationError({"note": "La baja requiere un motivo."})

    with transaction.atomic():
        asset = _lock_asset(asset)
        last = _last_movement_or_error(asset)
        return AssetMovement.objects.create(
            asset=asset,
            movement_type=MovementType.DECOMMISSION,
            from_zone_id=last.to_zone_id,            # de dónde salió de operación
            to_zone=None,                            # la restricción CHECK exige destino nulo
            performed_by=user,
            note=note.strip(),
        )


# -----------------------------------------------------------------------------
# Consultas: leen el estado derivado en UNA sola consulta
# -----------------------------------------------------------------------------

def assets_with_state():
    """
    Activos anotados con su estado derivado, resuelto por la BD en una sola consulta.

    current_zone() del modelo hace 1 consulta por activo (N+1). Aquí una subconsulta
    correlacionada (Subquery + OuterRef) obtiene "el último movimiento de cada activo"
    dentro del mismo SELECT.

    Nombres de anotación distintos a los métodos del modelo (current_zone, current_status)
    a propósito: una anotación con el mismo nombre taparía el método.
    """
    last = (
        AssetMovement.objects
        .filter(asset=OuterRef("pk"))                # correlación: "movimientos de ESTE activo"
        .order_by("-timestamp", "-id")               # el más reciente primero (aprovecha el índice)
    )
    return (
        Asset.objects
        .select_related("asset_type")                # el tipo viene en el mismo JOIN
        .annotate(
            last_movement_type=Subquery(last.values("movement_type")[:1]),
            zone_code=Subquery(last.values("to_zone__code")[:1]),
            zone_name=Subquery(last.values("to_zone__name")[:1]),
        )
    )


def anomaly_report():
    """
    RF-11: activos que requieren atención.

    "Activo operativo sin zona" no aparece porque es IMPOSIBLE por diseño: la restricción
    CHECK obliga a que todo CHECK_IN y RELOCATION tenga zona destino.
    """
    qs = assets_with_state()
    return {
        "sin_alta": qs.filter(last_movement_type__isnull=True),          # nunca tuvo CHECK_IN
        "dados_de_baja": qs.filter(last_movement_type=MovementType.DECOMMISSION),
    }
