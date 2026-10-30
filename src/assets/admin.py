"""
Admin de OT-Asset-Registry.

El admin es otra "vista" del sistema y obedece las mismas reglas:
- El ledger es de SOLO LECTURA aquí, incluso para el superusuario.
- El alta de activos NO se hace aquí: requiere crear el Asset y su CHECK_IN
  de forma atómica, y eso es responsabilidad de la capa de servicios (Bloque 4).
"""

from django.contrib import admin

from .models import Asset, AssetMovement, AssetStatus, AssetType, Zone

admin.site.site_header = "OT-Asset-Registry"                 # encabezado de todas las páginas
admin.site.site_title = "OT-Asset-Registry"                  # <title> del navegador
admin.site.index_title = "Registro de activos industriales"  # título del índice


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


class AssetMovementInline(admin.TabularInline):
    """Historial del activo dentro de su ficha. Solo lectura."""

    model = AssetMovement
    fields = ("timestamp", "movement_type", "from_zone", "to_zone", "performed_by", "note")
    readonly_fields = fields                         # todos los campos de solo lectura
    extra = 0                                        # sin filas vacías para "agregar"
    can_delete = False                               # sin casilla de borrar
    ordering = ("-timestamp", "-id")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("tag", "name", "asset_type", "zona_actual", "estado")
    list_filter = ("asset_type",)
    search_fields = ("tag", "name")
    readonly_fields = ("created_at",)
    list_select_related = ("asset_type",)            # evita una consulta extra por fila para el tipo
    inlines = [AssetMovementInline]

    def has_add_permission(self, request):
        # Un activo sin CHECK_IN es una anomalía. El alta atómica vive en el servicio (Bloque 4).
        return False

    def has_delete_permission(self, request, obj=None):
        # Los activos no se borran: se dan de baja con un movimiento DECOMMISSION.
        return False

    @admin.display(description="zona actual")
    def zona_actual(self, obj):
        # Derivada del ledger: una consulta por fila (N+1). Aceptable a esta escala;
        # en las vistas del Bloque 4 se resuelve con una sola consulta.
        return obj.current_zone() or "—"

    @admin.display(description="estado")
    def estado(self, obj):
        status = obj.current_status()
        return AssetStatus(status).label if status else "Sin alta (anomalía)"


@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    """Ledger: consultar, filtrar y buscar. Nunca agregar, editar ni borrar desde aquí."""

    list_display = ("timestamp", "asset", "movement_type", "from_zone", "to_zone", "performed_by")
    list_filter = ("movement_type", "timestamp")
    search_fields = ("asset__tag", "performed_by__username")
    date_hierarchy = "timestamp"                     # navegación por año / mes / día
    list_select_related = ("asset", "from_zone", "to_zone", "performed_by")

    # Estos métodos se evalúan ANTES que los permisos del usuario, por eso aplican
    # también al superusuario. Con has_delete_permission en False, Django quita
    # automáticamente la acción masiva "Eliminar seleccionados".
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
