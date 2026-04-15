from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Count
from .forms import CiudadForm
from .services import (
    obtener_clima,
    obtener_pronostico,
    obtener_clima_por_coordenadas,
    obtener_pronostico_por_coordenadas,
)
from .models import ConsultaClima


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
    error = None
    fondo_clima = 'default'
    origen_geo = False

    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if lat and lon:
        clima = obtener_clima_por_coordenadas(lat, lon)

        if clima:
            pronostico = obtener_pronostico_por_coordenadas(lat, lon)
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

            if clima:
                pronostico = obtener_pronostico(ciudad)
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
                error = "No se encontró la ciudad o hubo un problema con la API."
    else:
        form = CiudadForm()

    if request.method != 'POST':
        form = CiudadForm()

    return render(request, 'clima/inicio.html', {
        'form': form,
        'clima': clima,
        'pronostico': pronostico,
        'error': error,
        'fondo_clima': fondo_clima,
        'origen_geo': origen_geo,
    })


def historial(request):
    busqueda = request.GET.get('q', '').strip()
    consultas = ConsultaClima.objects.all().order_by('-fecha_consulta')

    if busqueda:
        consultas = consultas.filter(ciudad__icontains=busqueda)

    return render(request, 'clima/historial.html', {
        'consultas': consultas,
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
    consulta = get_object_or_404(ConsultaClima, id=consulta_id)
    consulta.delete()
    return redirect('historial')


def vaciar_historial(request):
    ConsultaClima.objects.all().delete()
    return redirect('historial')


def toggle_favorita(request, consulta_id):
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

    return render(request, 'clima/estadisticas.html', {
        'consultas': consultas[:10],
        'total_consultas': total_consultas,
        'temperatura_promedio': temperatura_promedio,
        'ciudad_mas_buscada': ciudad_mas_buscada,
        'total_favoritas': total_favoritas,
        'fondo_clima': 'default'
    })