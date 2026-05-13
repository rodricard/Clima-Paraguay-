from django.urls import path
from .views import (
    inicio,
    historial,
    detalle,
    eliminar_consulta,
    vaciar_historial,
    toggle_favorita,
    favoritos,
    estadisticas,
    autocomplete_ciudades,
)

urlpatterns = [
    path('', inicio, name='inicio'),
    path('historial/', historial, name='historial'),
    path('detalle/<int:consulta_id>/', detalle, name='detalle'),
    path('eliminar/<int:consulta_id>/', eliminar_consulta, name='eliminar_consulta'),
    path('vaciar/', vaciar_historial, name='vaciar_historial'),
    path('favorita/<int:consulta_id>/', toggle_favorita, name='toggle_favorita'),
    path('favoritos/', favoritos, name='favoritos'),
    path('estadisticas/', estadisticas, name='estadisticas'),
    path('autocomplete/', autocomplete_ciudades, name='autocomplete_ciudades'),
]