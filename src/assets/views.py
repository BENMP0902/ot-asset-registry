"""
Vistas de OT-Asset-Registry: traducen HTTP <-> servicios. Vistas DELGADAS (thin views).

Autorización en dos capas (defensa en profundidad):
1. Decorador @permission_required: responde 403 rápido, antes de procesar nada.
2. El servicio vuelve a verificar: es la frontera de confianza real. Si mañana
   alguien escribe otra vista y olvida el decorador, el servicio sigue protegiendo.

Orden de decoradores: @login_required va ARRIBA. Así un anónimo se redirige al login,
y un usuario autenticado sin permiso recibe 403.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .forms import AssetRegisterForm, DecommissionForm, RelocateForm
from .models import MovementType


@login_required
@permission_required("assets.view_asset", raise_exception=True)
@require_http_methods(["GET"])
def asset_list(request):
    """RF-04: listado con búsqueda y filtro por estado. Una sola consulta para el estado."""
    assets = services.assets_with_state()

    q = request.GET.get("q", "").strip()[:100]          # acota la longitud de la entrada
    if q:
        # icontains genera SQL parametrizado: el texto del usuario nunca se concatena al SQL
        assets = assets.filter(Q(tag__icontains=q) | Q(name__icontains=q))

    estado = request.GET.get("estado", "")
    if estado == "activos":
        assets = assets.filter(last_movement_type__in=[MovementType.CHECK_IN, MovementType.RELOCATION])
    elif estado == "baja":
        assets = assets.filter(last_movement_type=MovementType.DECOMMISSION)
    # Cualquier otro valor de "estado" se ignora: lista blanca, no lista negra.

    return render(request, "assets/asset_list.html", {"assets": assets, "q": q, "estado": estado})


@login_required
@permission_required("assets.view_asset", raise_exception=True)
@require_http_methods(["GET"])
def asset_detail(request, pk):
    """Ficha del activo con su historial completo (ledger)."""
    asset = get_object_or_404(services.assets_with_state(), pk=pk)    # 404 si no existe
    movements = asset.movements.select_related("from_zone", "to_zone", "performed_by")
    return render(request, "assets/asset_detail.html", {"asset": asset, "movements": movements})


@login_required
@permission_required("assets.register_checkin", raise_exception=True)
@require_http_methods(["GET", "POST"])
def asset_register(request):
    """UC-04: alta atómica (Asset + CHECK_IN) vía servicio."""
    if request.method == "POST":
        form = AssetRegisterForm(request.POST)
        if form.is_valid():                              # 1) valida la ENTRADA
            try:
                asset = services.register_asset(user=request.user, **form.cleaned_data)  # 2) reglas de negocio
            except ValidationError as exc:
                form.add_error(None, exc)                # errores del servicio -> formulario
            else:
                messages.success(request, f"Activo {asset.tag} dado de alta.")
                return redirect("assets:detail", pk=asset.pk)   # patrón Post/Redirect/Get
    else:
        form = AssetRegisterForm()
    return render(request, "assets/asset_form.html", {"form": form, "title": "Alta de activo"})


@login_required
@permission_required("assets.relocate_asset", raise_exception=True)
@require_http_methods(["GET", "POST"])
def asset_relocate(request, pk):
    """UC-07: reubicación. El formulario solo pide destino y nota."""
    asset = get_object_or_404(services.assets_with_state(), pk=pk)
    if request.method == "POST":
        form = RelocateForm(request.POST)
        if form.is_valid():
            try:
                services.relocate_asset(user=request.user, asset=asset, **form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, f"Activo {asset.tag} reubicado.")
                return redirect("assets:detail", pk=asset.pk)
    else:
        form = RelocateForm()
    return render(request, "assets/movement_form.html",
                  {"form": form, "asset": asset, "title": "Reubicar activo", "danger": False})


@login_required
@permission_required("assets.decommission_asset", raise_exception=True)
@require_http_methods(["GET", "POST"])
def asset_decommission(request, pk):
    """UC-08: baja con motivo obligatorio. Exclusiva del Administrador."""
    asset = get_object_or_404(services.assets_with_state(), pk=pk)
    if request.method == "POST":
        form = DecommissionForm(request.POST)
        if form.is_valid():
            try:
                services.decommission_asset(user=request.user, asset=asset, **form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.warning(request, f"Activo {asset.tag} dado de baja.")
                return redirect("assets:detail", pk=asset.pk)
    else:
        form = DecommissionForm()
    return render(request, "assets/movement_form.html",
                  {"form": form, "asset": asset, "title": "Dar de baja", "danger": True})


@login_required
@permission_required("assets.view_asset", raise_exception=True)
@require_http_methods(["GET"])
def anomalies(request):
    """RF-11: activos sin alta y dados de baja."""
    return render(request, "assets/anomaly_report.html", {"report": services.anomaly_report()})
