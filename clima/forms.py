from django import forms


class CiudadForm(forms.Form):
    ciudad = forms.CharField(
        label='Ciudad',
        max_length=100,
        required=False,
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