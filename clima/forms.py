from django import forms
from django.core.validators import RegexValidator


class CiudadForm(forms.Form):
    ciudad = forms.CharField(
        label='Ciudad',
        max_length=100,
        required=False,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZÀ-ÿñÑ\s,.\'\-]+$',
                message='El nombre solo puede contener letras, espacios y guiones.',
                code='ciudad_invalida'
            )
        ],
        widget=forms.TextInput(attrs={
            'placeholder': 'Ingrese una ciudad, por ejemplo: Asuncion',
            'autocomplete': 'off',
            'id': 'id_ciudad'
        })
    )

    latitud = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_latitud'})
    )

    longitud = forms.FloatField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_longitud'})
    )