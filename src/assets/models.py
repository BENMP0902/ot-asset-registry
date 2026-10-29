"""
Modelos de dominio de OT-Asset-Registry.

Traducción del diagrama de clases (docs/03-diseno/02-diagrama-clases.md):
- AssetType, Zone, Asset, AssetMovement -> tablas.
- MovementType, AssetStatus             -> TextChoices (valores cerrados, no tablas).
- current_zone()/current_status()       -> MÉTODOS derivados del ledger, no columnas.

Reparto de responsabilidades:
- Aquí viven las invariantes de UNA fila (restricciones CHECK, unicidad, append-only).
- Las reglas que involucran VARIAS filas (p. ej. "no reubicar un activo dado de baja",
  "toda alta crea su CHECK_IN") viven en la capa de servicios (Bloque 4).
"""

from django.conf import settings                    # para referenciar AUTH_USER_MODEL sin acoplarse a auth.User
from django.core.exceptions import PermissionDenied # en vistas se traduce automáticamente a HTTP 403
from django.db import models                        # ORM de Django
from django.db.models import F, Q                   # expresiones para restricciones a nivel de BD


# -----------------------------------------------------------------------------
# Enumeraciones (TextChoices): conjuntos cerrados de valores
# -----------------------------------------------------------------------------

class MovementType(models.TextChoices):
    """Tipos de movimiento del ledger. Valor guardado en BD | etiqueta visible."""
    CHECK_IN = "CHECK_IN", "Alta"                   # entra al inventario (sin zona de origen)
    RELOCATION = "RELOCATION", "Reubicación"        # cambia de zona (origen y destino)
    DECOMMISSION = "DECOMMISSION", "Baja"           # sale de operación (sin zona destino)


class AssetStatus(models.TextChoices):
    """Estado DERIVADO de un activo. Nunca se guarda: se calcula del último movimiento."""
    ACTIVE = "ACTIVE", "Activo"
    DECOMMISSIONED = "DECOMMISSIONED", "Dado de baja"


# -----------------------------------------------------------------------------
# Catálogos
# -----------------------------------------------------------------------------

class AssetType(models.Model):
    """Catálogo extensible de tipos de equipo (Open/Closed: se amplía con datos, no con código)."""

    name = models.CharField("nombre", max_length=100, unique=True)   # unique: evita duplicados "VFD" / "VFD"
    description = models.TextField("descripción", blank=True)        # blank=True: opcional en formularios

    class Meta:
        verbose_name = "tipo de activo"             # nombre legible en el admin
        verbose_name_plural = "tipos de activo"
        ordering = ["name"]                         # orden por defecto en consultas

    def __str__(self):
        return self.name                            # representación en admin, shell y selects


class Zone(models.Model):
    """Ubicación física: línea de producción, cuarto eléctrico, tablero."""

    code = models.CharField("código", max_length=20, unique=True)    # identificador corto, p. ej. "Z-A1"
    name = models.CharField("nombre", max_length=100)
    description = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "zona"
        verbose_name_plural = "zonas"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


# -----------------------------------------------------------------------------
# Entidad central
# -----------------------------------------------------------------------------

class Asset(models.Model):
    """
    Activo físico. Guarda solo datos descriptivos.
    Zona y estado NO son columnas: se derivan del ledger (única fuente de verdad).
    """

    tag = models.CharField("etiqueta", max_length=50, unique=True)   # etiqueta física / número de inventario
    name = models.CharField("nombre", max_length=150)                # marca, modelo, capacidad
    asset_type = models.ForeignKey(
        AssetType,
        on_delete=models.PROTECT,                   # no se puede borrar un tipo que tenga activos
        related_name="assets",                      # acceso inverso: tipo.assets.all()
        verbose_name="tipo de activo",
    )
    description = models.TextField("descripción", blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)    # lo fija el servidor, no el usuario

    class Meta:
        verbose_name = "activo"
        verbose_name_plural = "activos"
        ordering = ["tag"]

    def __str__(self):
        return f"{self.tag} — {self.name}"

    # --- Estado derivado del ledger ---

    def last_movement(self):
        """Último movimiento del activo, o None si no tiene ninguno (anomalía)."""
        # "-id" desempata si dos movimientos comparten timestamp
        return self.movements.order_by("-timestamp", "-id").first()

    def current_zone(self):
        """Zona actual = destino del último movimiento. None si está de baja o sin movimientos."""
        last = self.last_movement()
        return last.to_zone if last else None

    def current_status(self):
        """ACTIVE / DECOMMISSIONED según el último movimiento. None si no hay movimientos (anomalía)."""
        last = self.last_movement()
        if last is None:
            return None                             # activo sin CHECK_IN: lo reportará RF-11
        if last.movement_type == MovementType.DECOMMISSION:
            return AssetStatus.DECOMMISSIONED
        return AssetStatus.ACTIVE


# -----------------------------------------------------------------------------
# Ledger append-only
# -----------------------------------------------------------------------------

class AppendOnlyQuerySet(models.QuerySet):
    """Bloquea las operaciones masivas del ORM, que NO pasan por save()/delete() del modelo."""

    def update(self, **kwargs):
        raise PermissionDenied("Ledger append-only: los movimientos no se pueden modificar.")

    def delete(self):
        raise PermissionDenied("Ledger append-only: los movimientos no se pueden eliminar.")


class AssetMovement(models.Model):
    """
    Registro inmutable de alta, reubicación y baja.
    Cada fila responde quién (performed_by), qué (movement_type) y cuándo (timestamp).
    """

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,                   # un activo con historial no se puede borrar
        related_name="movements",                   # activo.movements.all()
        verbose_name="activo",
    )
    movement_type = models.CharField(
        "tipo de movimiento",
        max_length=20,
        choices=MovementType.choices,               # valida contra el conjunto cerrado
    )
    from_zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        null=True, blank=True,                      # nulo en CHECK_IN
        related_name="movements_out",               # OBLIGATORIO distinto: hay 2 FK al mismo modelo
        verbose_name="zona origen",
    )
    to_zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        null=True, blank=True,                      # nulo en DECOMMISSION
        related_name="movements_in",
        verbose_name="zona destino",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,                   # buena práctica: no importar auth.User directamente
        on_delete=models.PROTECT,                   # no se borra a quien firmó movimientos: se desactiva
        related_name="asset_movements",
        verbose_name="ejecutado por",
    )
    timestamp = models.DateTimeField("fecha y hora", auto_now_add=True)  # sello del servidor: no falsificable
    note = models.TextField("nota", blank=True)

    objects = AppendOnlyQuerySet.as_manager()       # el manager por defecto bloquea update()/delete() masivos

    class Meta:
        verbose_name = "movimiento"
        verbose_name_plural = "movimientos"
        ordering = ["-timestamp", "-id"]            # más reciente primero
        indexes = [
            # acelera last_movement(): filtra por activo y ordena por fecha
            models.Index(fields=["asset", "-timestamp"], name="movement_asset_ts_idx"),
        ]
        constraints = [
            # Invariante de UNA fila, aplicada por la propia base de datos (CHECK constraint)
            models.CheckConstraint(
                condition=(                         # Django 5.1+: 'condition' (antes 'check', retirado en 6.0)
                    Q(movement_type=MovementType.CHECK_IN,
                      from_zone__isnull=True, to_zone__isnull=False)
                    | Q(~Q(from_zone=F("to_zone")),            # reubicar a la misma zona no tiene sentido
                        movement_type=MovementType.RELOCATION,
                        from_zone__isnull=False, to_zone__isnull=False)
                    | Q(movement_type=MovementType.DECOMMISSION,
                        to_zone__isnull=True)
                ),
                name="movement_zones_match_type",
                violation_error_message=(
                    "Zonas inválidas para el tipo de movimiento: "
                    "Alta requiere solo destino; Reubicación, origen y destino distintos; "
                    "Baja, sin destino."
                ),
            ),
        ]

    def __str__(self):
        # Defensivo: antes de guardarse no hay timestamp, y puede no haber activo asignado.
        # Sin estas guardas, imprimir un movimiento inválido en un formulario lanzaría TypeError.
        tag = self.asset.tag if self.asset_id else "¿activo?"
        when = f"{self.timestamp:%Y-%m-%d %H:%M}" if self.timestamp else "sin guardar"
        return f"{self.get_movement_type_display()} · {tag} · {when}"

    def save(self, *args, **kwargs):
        # _state.adding es True solo antes del primer INSERT. Si es False, sería un UPDATE.
        if not self._state.adding:
            raise PermissionDenied("Ledger append-only: los movimientos no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Ledger append-only: los movimientos no se pueden eliminar.")
