import requests
from decouple import config
from datetime import datetime
from django.core.cache import cache

API_KEY = config('OPENWEATHER_API_KEY', default='')
BASE_URL_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
BASE_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
BASE_URL_GEO = "http://api.openweathermap.org/geo/1.0/direct"
BASE_URL_AIR = "http://api.openweathermap.org/data/2.5/air_pollution"
BASE_URL_UV  = "http://api.openweathermap.org/data/2.5/uvi"

ERROR_CIUDAD_NO_ENCONTRADA = 'ciudad_no_encontrada'
ERROR_API_KEY = 'api_key_invalida'
ERROR_LIMITE = 'limite_superado'
ERROR_TIMEOUT = 'tiempo_agotado'
ERROR_CONEXION = 'sin_conexion'
ERROR_SERVIDOR = 'error_servidor'


def _codigo_error(status_code):
    if status_code == 404:
        return ERROR_CIUDAD_NO_ENCONTRADA
    if status_code == 401:
        return ERROR_API_KEY
    if status_code == 429:
        return ERROR_LIMITE
    return ERROR_SERVIDOR


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
    cache_key = f"clima_ciudad_{ciudad.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        'q': ciudad,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    try:
        response = requests.get(BASE_URL_CURRENT, params=params, timeout=10)
    except requests.Timeout:
        return ERROR_TIMEOUT
    except requests.ConnectionError:
        return ERROR_CONEXION

    if response.status_code == 200:
        resultado = _mapear_clima_actual(response.json())
        cache.set(cache_key, resultado)
        return resultado

    return _codigo_error(response.status_code)


def obtener_clima_por_coordenadas(lat, lon):
    cache_key = f"clima_coords_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    try:
        response = requests.get(BASE_URL_CURRENT, params=params, timeout=10)
    except requests.Timeout:
        return ERROR_TIMEOUT
    except requests.ConnectionError:
        return ERROR_CONEXION

    if response.status_code == 200:
        resultado = _mapear_clima_actual(response.json())
        cache.set(cache_key, resultado)
        return resultado

    return _codigo_error(response.status_code)


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
                'lluvia_prob': round(item.get('pop', 0) * 100),
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
        probs = [x.get('pop', 0) for x in items]

        pronostico_dias.append({
            'dia': fecha_obj.strftime('%A').capitalize(),
            'fecha': fecha_obj.strftime('%d/%m'),
            'temp_min': round(min(temperaturas), 1),
            'temp_max': round(max(temperaturas), 1),
            'descripcion': item_medio_dia['weather'][0]['description'],
            'icono': item_medio_dia['weather'][0]['icon'],
            'lluvia_prob': round(max(probs) * 100),
        })

    return {
        'horas': pronostico_horas,
        'dias': pronostico_dias[:5]
    }


def obtener_pronostico(ciudad):
    cache_key = f"pronostico_ciudad_{ciudad.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        'q': ciudad,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    try:
        response = requests.get(BASE_URL_FORECAST, params=params, timeout=10)
    except (requests.Timeout, requests.ConnectionError):
        return {'horas': [], 'dias': []}

    if response.status_code == 200:
        resultado = _mapear_pronostico(response.json())
        cache.set(cache_key, resultado)
        return resultado

    return {'horas': [], 'dias': []}


def obtener_sugerencias_ciudades(query):
    cache_key = f"sugerencias_{query.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        'q': query,
        'limit': 5,
        'appid': API_KEY,
    }

    try:
        response = requests.get(BASE_URL_GEO, params=params, timeout=5)
    except (requests.Timeout, requests.ConnectionError):
        return []

    if response.status_code != 200:
        return []

    sugerencias = []
    for item in response.json():
        nombre = item.get('name', '')
        pais = item.get('country', '')
        estado = item.get('state', '')
        etiqueta = f"{nombre}, {estado}, {pais}" if estado else f"{nombre}, {pais}"
        sugerencias.append({'nombre': nombre, 'etiqueta': etiqueta})

    cache.set(cache_key, sugerencias, 300)
    return sugerencias


def obtener_pronostico_por_coordenadas(lat, lon):
    cache_key = f"pronostico_coords_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'es'
    }

    try:
        response = requests.get(BASE_URL_FORECAST, params=params, timeout=10)
    except (requests.Timeout, requests.ConnectionError):
        return {'horas': [], 'dias': []}

    if response.status_code == 200:
        resultado = _mapear_pronostico(response.json())
        cache.set(cache_key, resultado)
        return resultado

    return {'horas': [], 'dias': []}


def obtener_calidad_aire(lat, lon):
    cache_key = f"aqi_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {'lat': lat, 'lon': lon, 'appid': API_KEY}
    try:
        response = requests.get(BASE_URL_AIR, params=params, timeout=8)
    except (requests.Timeout, requests.ConnectionError):
        return None

    if response.status_code != 200:
        return None

    items = response.json().get('list', [])
    if not items:
        return None

    item = items[0]
    aqi = item['main']['aqi']
    comp = item['components']

    LABELS = {1: 'Buena', 2: 'Aceptable', 3: 'Moderada', 4: 'Mala', 5: 'Muy mala'}
    COLORS = {1: '#22c55e', 2: '#84cc16', 3: '#f59e0b', 4: '#f97316', 5: '#ef4444'}

    resultado = {
        'aqi': aqi,
        'label': LABELS.get(aqi, 'Desconocida'),
        'color': COLORS.get(aqi, '#94a3b8'),
        'pm25': round(comp.get('pm2_5', 0), 1),
        'pm10': round(comp.get('pm10', 0), 1),
        'o3': round(comp.get('o3', 0), 1),
        'no2': round(comp.get('no2', 0), 1),
    }
    cache.set(cache_key, resultado, 600)
    return resultado


def obtener_uv(lat, lon):
    cache_key = f"uv_{lat}_{lon}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = {'lat': lat, 'lon': lon, 'appid': API_KEY}
    try:
        response = requests.get(BASE_URL_UV, params=params, timeout=8)
    except (requests.Timeout, requests.ConnectionError):
        return None

    if response.status_code != 200:
        return None

    valor = round(response.json().get('value', 0), 1)

    if valor <= 2:
        riesgo, color = 'Bajo', '#22c55e'
    elif valor <= 5:
        riesgo, color = 'Moderado', '#f59e0b'
    elif valor <= 7:
        riesgo, color = 'Alto', '#f97316'
    elif valor <= 10:
        riesgo, color = 'Muy alto', '#ef4444'
    else:
        riesgo, color = 'Extremo', '#a855f7'

    resultado = {'valor': valor, 'riesgo': riesgo, 'color': color, 'percent': min(100, round(valor / 11 * 100))}
    cache.set(cache_key, resultado, 600)
    return resultado