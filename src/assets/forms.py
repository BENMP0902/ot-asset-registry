"""
Formularios de OT-Asset-Registry.

Son formularios simples (forms.Form), NO ModelForm: no guardan nada. Solo validan
la ENTRADA (tipos, obligatorios, longitudes) y entregan cleaned_data a los servicios,
que son los dueños de la lógica de negocio.

Los nombres de campo coinciden con los parámetros de los servicios y con las llaves
de sus ValidationError. Así, form.add_error(None, exc) coloca cada error del servicio
junto al campo correcto.
"""

from django import forms

from .models import AssetType, Zone


class AssetRegisterForm(forms.Form):
    """UC-04: alta de activo con su zona inicial."""

    tag = forms.CharField(label="Etiqueta", max_length=50)
    name = forms.CharField(label="Nombre", max_length=150)
    asset_type = forms.ModelChoiceField(        # solo acepta IDs que existen en la BD
        label="Tipo de activo", queryset=AssetType.objects.all(),
    )
    zone = forms.ModelChoiceField(label="Zona inicial", queryset=Zone.objects.all())
    description = forms.CharField(
        label="Descripción", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    note = forms.CharField(label="Nota del alta", required=False, max_length=500)


class RelocateForm(forms.Form):
    """UC-07: el usuario elige SOLO el destino. El origen lo deriva el servidor."""

    to_zone = forms.ModelChoiceField(label="Zona destino", queryset=Zone.objects.all())
    note = forms.CharField(
        label="Nota", required=False, max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class DecommissionForm(forms.Form):
    """UC-08: la baja exige motivo."""

    note = forms.CharField(                     # strip=True (por defecto): "   " cuenta como vacío
        label="Motivo de la baja", max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
