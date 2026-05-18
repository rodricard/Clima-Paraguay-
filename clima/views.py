from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Avg, Count
from django.core.paginator import Paginator
from .forms import CiudadForm
from django.core.cache import cache
from .services import (
    obtener_clima,
    obtener_pronostico,
    obtener_clima_por_coordenadas,
    obtener_pronostico_por_coordenadas,
    obtener_sugerencias_ciudades,
    obtener_calidad_aire,
    obtener_uv,
    API_KEY as OW_API_KEY,
    ERROR_CIUDAD_NO_ENCONTRADA,
    ERROR_API_KEY,
    ERROR_LIMITE,
    ERROR_TIMEOUT,
    ERROR_CONEXION,
    ERROR_SERVIDOR,
)
from .models import ConsultaClima


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')

MENSAJES_ERROR = {
    ERROR_CIUDAD_NO_ENCONTRADA: 'No encontramos esa ciudad. Verificá el nombre e intentá de nuevo.',
    ERROR_API_KEY: 'La clave de API no es válida. Contactá al administrador.',
    ERROR_LIMITE: 'Se superó el límite de consultas a la API. Intentá en unos minutos.',
    ERROR_TIMEOUT: 'La consulta tardó demasiado. Verificá tu conexión e intentá de nuevo.',
    ERROR_CONEXION: 'No se pudo conectar al servidor de clima. Verificá tu conexión a internet.',
    ERROR_SERVIDOR: 'El servidor de clima no está disponible en este momento. Intentá más tarde.',
}


def _es_error(resultado):
    return isinstance(resultado, str)


def obtener_fondo_por_clima(descripcion):
    desc = descripcion.lower()

    if 'torment' in desc:
        return 'storm'
    elif 'lluv' in desc:
        return 'rainy'
    elif 'nube' in desc:
        return 'cloudy'
    elif 'niebla' in desc or 'neblina' in desc:
        return 'mist'
    elif 'despejado' in desc or 'soleado' in desc:
        return 'sunny'
    else:
        return 'default'


def inicio(request):
    clima = None
    pronostico = {'horas': [], 'dias': []}
    calidad_aire = None
    uv = None
    error = None
    fondo_clima = 'default'
    origen_geo = False

    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if lat and lon:
        clima = obtener_clima_por_coordenadas(lat, lon)

        if _es_error(clima):
            error = MENSAJES_ERROR.get(clima, MENSAJES_ERROR[ERROR_SERVIDOR])
            clima = None
        elif clima:
            pronostico = obtener_pronostico_por_coordenadas(lat, lon)
            calidad_aire = obtener_calidad_aire(clima['latitud'], clima['longitud'])
            uv = obtener_uv(clima['latitud'], clima['longitud'])
            fondo_clima = obtener_fondo_por_clima(clima['descripcion'])
            origen_geo = True

            ConsultaClima.objects.create(
                ciudad=clima['ciudad'],
                pais=clima['pais'],
                temperatura=clima['temperatura'],
                descripcion=clima['descripcion'],
                humedad=clima['humedad'],
                latitud=clima['latitud'],
                longitud=clima['longitud'],
                icono=clima['icono']
            )
        else:
            error = "No se pudo obtener el clima de tu ubicación."

    elif request.method == 'POST':
        form = CiudadForm(request.POST)
        if form.is_valid():
            ciudad = form.cleaned_data['ciudad'].strip()
            clima = obtener_clima(ciudad)

            if _es_error(clima):
                error = MENSAJES_ERROR.get(clima, MENSAJES_ERROR[ERROR_SERVIDOR])
                clima = None
            elif clima:
                pronostico = obtener_pronostico(ciudad)
                calidad_aire = obtener_calidad_aire(clima['latitud'], clima['longitud'])
                uv = obtener_uv(clima['latitud'], clima['longitud'])
                fondo_clima = obtener_fondo_por_clima(clima['descripcion'])

                ConsultaClima.objects.create(
                    ciudad=clima['ciudad'],
                    pais=clima['pais'],
                    temperatura=clima['temperatura'],
                    descripcion=clima['descripcion'],
                    humedad=clima['humedad'],
                    latitud=clima['latitud'],
                    longitud=clima['longitud'],
                    icono=clima['icono']
                )
            else:
                error = MENSAJES_ERROR[ERROR_CIUDAD_NO_ENCONTRADA]
    else:
        form = CiudadForm()

    if request.method != 'POST':
        form = CiudadForm()

    return render(request, 'clima/inicio.html', {
        'form': form,
        'clima': clima,
        'pronostico': pronostico,
        'calidad_aire': calidad_aire,
        'uv': uv,
        'error': error,
        'fondo_clima': fondo_clima,
        'origen_geo': origen_geo,
        'ow_api_key': OW_API_KEY,
    })


def historial(request):
    busqueda = request.GET.get('q', '').strip()
    qs = ConsultaClima.objects.all().order_by('-fecha_consulta')

    if busqueda:
        qs = qs.filter(ciudad__icontains=busqueda)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'clima/historial.html', {
        'consultas': page_obj,
        'page_obj': page_obj,
        'busqueda': busqueda,
        'fondo_clima': 'default'
    })


def detalle(request, consulta_id):
    consulta = get_object_or_404(ConsultaClima, id=consulta_id)
    fondo_clima = obtener_fondo_por_clima(consulta.descripcion)

    return render(request, 'clima/detalle.html', {
        'consulta': consulta,
        'fondo_clima': fondo_clima
    })


def eliminar_consulta(request, consulta_id):
    if request.method == 'POST':
        consulta = get_object_or_404(ConsultaClima, id=consulta_id)
        consulta.delete()
    return redirect('historial')


def vaciar_historial(request):
    if request.method == 'POST':
        ConsultaClima.objects.all().delete()
    return redirect('historial')


def toggle_favorita(request, consulta_id):
    if request.method == 'POST':
        consulta = get_object_or_404(ConsultaClima, id=consulta_id)
        consulta.favorita = not consulta.favorita
        consulta.save()
    return redirect('historial')


def favoritos(request):
    consultas = ConsultaClima.objects.filter(favorita=True).order_by('-fecha_consulta')

    return render(request, 'clima/favoritos.html', {
        'consultas': consultas,
        'fondo_clima': 'default'
    })


def estadisticas(request):
    consultas = ConsultaClima.objects.all().order_by('-fecha_consulta')

    total_consultas = consultas.count()
    temperatura_promedio = consultas.aggregate(promedio=Avg('temperatura'))['promedio']
    total_favoritas = consultas.filter(favorita=True).count()

    ciudad_mas_buscada = (
        consultas.values('ciudad')
        .annotate(total=Count('ciudad'))
        .order_by('-total')
        .first()
    )

    top_ciudades = (
        consultas.values('ciudad')
        .annotate(total=Count('ciudad'), temp_promedio=Avg('temperatura'))
        .order_by('-total')[:6]
    )

    ultimas_consultas = list(consultas[:15])

    return render(request, 'clima/estadisticas.html', {
        'consultas': consultas[:10],
        'total_consultas': total_consultas,
        'temperatura_promedio': temperatura_promedio,
        'ciudad_mas_buscada': ciudad_mas_buscada,
        'total_favoritas': total_favoritas,
        'top_ciudades': top_ciudades,
        'ultimas_consultas': ultimas_consultas,
        'fondo_clima': 'default'
    })


def autocomplete_ciudades(request):
    ip = _get_client_ip(request)
    rl_key = f"rl_ac_{ip}"
    count = cache.get(rl_key, 0)
    if count >= 30:
        return JsonResponse([], safe=False)
    cache.set(rl_key, count + 1, 60)

    query = request.GET.get('q', '').strip()[:100]
    if len(query) < 2:
        return JsonResponse([], safe=False)
    sugerencias = obtener_sugerencias_ciudades(query)
    return JsonResponse(sugerencias, safe=False)


def comparar(request):
    ciudad1 = request.GET.get('ciudad1', '').strip()
    ciudad2 = request.GET.get('ciudad2', '').strip()
    clima1 = clima2 = None
    error1 = error2 = None

    if ciudad1:
        r = obtener_clima(ciudad1)
        if _es_error(r):
            error1 = MENSAJES_ERROR.get(r, MENSAJES_ERROR[ERROR_SERVIDOR])
        else:
            clima1 = r

    if ciudad2:
        r = obtener_clima(ciudad2)
        if _es_error(r):
            error2 = MENSAJES_ERROR.get(r, MENSAJES_ERROR[ERROR_SERVIDOR])
        else:
            clima2 = r

    return render(request, 'clima/comparar.html', {
        'ciudad1': ciudad1,
        'ciudad2': ciudad2,
        'clima1': clima1,
        'clima2': clima2,
        'error1': error1,
        'error2': error2,
        'fondo_clima': 'default',
    })