import requests
from decouple import config
from datetime import datetime

API_KEY = config('OPENWEATHER_API_KEY', default='')
BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
BASE_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"


def _mapear_clima_actual(data):
    amanecer = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
    atardecer = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')

    return {
        'ciudad': data['name'],
        'pais': data['sys']['country'],
        'temperatura': round(data['main']['temp'], 1),
        'sensacion_termica': round(data['main']['feels_like'], 1),
        'temp_min': round(data['main']['temp_min'], 1),
        'temp_max': round(data['main']['temp_max'], 1),
        'descripcion': data['weather'][0]['description'],
        'humedad': data['main']['humidity'],
        'presion': data['main']['pressure'],
        'visibilidad': round(data.get('visibility', 0) / 1000, 1),
        'viento_velocidad': round(data['wind']['speed'], 1),
        'viento_direccion': data['wind'].get('deg', 0),
        'latitud': data['coord']['lat'],
        'longitud': data['coord']['lon'],
        'icono': data['weather'][0]['icon'],
        'amanecer': amanecer,
        'atardecer': atardecer,
    }


def obtener_clima(ciudad):
    params = {
        'q': ciudad,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    response = requests.get(BASE_URL_CURRENT, params=params, timeout=10)

    if response.status_code == 200:
        return _mapear_clima_actual(response.json())

    return None


def obtener_clima_por_coordenadas(lat, lon):
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    response = requests.get(BASE_URL_CURRENT, params=params, timeout=10)

    if response.status_code == 200:
        return _mapear_clima_actual(response.json())

    return None


def _mapear_pronostico(data):
    lista = data.get('list', [])

    # Ordenar por fecha por seguridad
    lista = sorted(lista, key=lambda x: x['dt'])

    # ✅ Tomar solo próximas horas futuras
    now = datetime.now()
    pronostico_horas = []

    for item in lista:
        fecha_hora = datetime.fromtimestamp(item['dt'])

        if fecha_hora > now:
            pronostico_horas.append({
                'hora': fecha_hora.strftime('%H:%M'),
                'fecha': fecha_hora.strftime('%d/%m'),
                'temperatura': round(item['main']['temp'], 1),
                'descripcion': item['weather'][0]['description'],
                'icono': item['weather'][0]['icon'],
            })

        # Solo próximas 24h (8 bloques de 3 horas)
        if len(pronostico_horas) == 8:
            break

    # ✅ Agrupar días correctamente
    dias_dict = {}
    for item in lista:
        fecha_obj = datetime.fromtimestamp(item['dt'])
        fecha_clave = fecha_obj.strftime('%Y-%m-%d')
        dias_dict.setdefault(fecha_clave, []).append(item)

    pronostico_dias = []
    for _, items in dias_dict.items():
        item_medio_dia = None

        for item in items:
            hora = datetime.fromtimestamp(item['dt']).strftime('%H:%M')
            if hora == '12:00':
                item_medio_dia = item
                break

        if item_medio_dia is None:
            item_medio_dia = items[0]

        fecha_obj = datetime.fromtimestamp(item_medio_dia['dt'])
        temperaturas = [x['main']['temp'] for x in items]

        pronostico_dias.append({
            'dia': fecha_obj.strftime('%A').capitalize(),
            'fecha': fecha_obj.strftime('%d/%m'),
            'temp_min': round(min(temperaturas), 1),
            'temp_max': round(max(temperaturas), 1),
            'descripcion': item_medio_dia['weather'][0]['description'],
            'icono': item_medio_dia['weather'][0]['icon'],
        })

    return {
        'horas': pronostico_horas,
        'dias': pronostico_dias[:5]
    }


def obtener_pronostico(ciudad):
    params = {
        'q': ciudad,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    response = requests.get(BASE_URL_FORECAST, params=params, timeout=10)

    if response.status_code == 200:
        return _mapear_pronostico(response.json())

    return {'horas': [], 'dias': []}


def obtener_pronostico_por_coordenadas(lat, lon):
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    response = requests.get(BASE_URL_FORECAST, params=params, timeout=10)

    if response.status_code == 200:
        return _mapear_pronostico(response.json())

    return {'horas': [], 'dias': []}