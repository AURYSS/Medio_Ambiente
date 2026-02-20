from flask import Flask, render_template, request, redirect, url_for
import requests
import os
from datetime import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

days_es = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

app = Flask(__name__)

@app.context_processor
def inject_api_keys():
    return {
        'GOOGLE_MAPS_API_KEY': os.environ.get('GOOGLE_MAPS_API_KEY', '')
    }

@app.route('/')
def index():
    return render_template(
        'index.html',
        breadcrumb=["Inicio"]
    )

@app.route('/sistema-ambiental')
def sistema():
    return render_template(
        'sistema.html',
        breadcrumb=["Inicio", "Sistema de Gestión Ambiental"]
    )

@app.route('/futuro')
def futuro():
    return render_template(
        'futuro.html',
        breadcrumb=["Inicio", "Futuro del Planeta"]
    )

@app.route('/tres-r')
def tres_r():
    return render_template(
        'tres_r.html',
        breadcrumb=["Inicio", "Las 3 R"]
    )

@app.route('/clima', methods=['GET', 'POST'])
def clima():
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        return "Error: API key no configurada. Establece la variable de entorno OPENWEATHER_API_KEY."
    
    city = request.form.get('city') or request.args.get('city')
    if not city:
        return render_template('clima.html', breadcrumb=["Inicio", "Clima"])
    
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=es'
    response = requests.get(url)
    if response.status_code != 200:
        error_msg = f"Error al obtener datos del clima para {city}: {response.status_code}"
        return render_template('clima.html', breadcrumb=["Inicio", "Clima"], error=error_msg, city=city)
    
    data = response.json()
    weather_info = {
        'city': city,
        'temp': data['main']['temp'],
        'feels_like': data['main']['feels_like'],
        'description': data['weather'][0]['description'].capitalize(),
        'humidity': data['main']['humidity'],
        'pressure': data['main']['pressure'],
        'wind_speed': data['wind']['speed'],
        'visibility': data.get('visibility', 'N/A'),
        'icon': data['weather'][0]['icon'],
        'lat': data['coord']['lat'],
        'lon': data['coord']['lon']
    }
    
    # Obtener pronóstico de 5 días
    url_forecast = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=es'
    response_forecast = requests.get(url_forecast)
    forecast_list = []
    if response_forecast.status_code == 200:
        forecast_data = response_forecast.json()
        daily_forecast = {}
        for item in forecast_data['list']:
            date = item['dt_txt'].split(' ')[0]  # YYYY-MM-DD
            if date not in daily_forecast:
                daily_forecast[date] = {
                    'temps': [],
                    'descriptions': [],
                    'icons': []
                }
            daily_forecast[date]['temps'].append(item['main']['temp'])
            daily_forecast[date]['descriptions'].append(item['weather'][0]['description'])
            daily_forecast[date]['icons'].append(item['weather'][0]['icon'])
        
        # Procesar para obtener min/max y descripción principal
        for date, info in list(daily_forecast.items())[1:6]:  # Empezar desde mañana, 5 días
            min_temp = min(info['temps'])
            max_temp = max(info['temps'])
            # Tomar la descripción más común
            desc_count = {}
            for desc in info['descriptions']:
                desc_count[desc] = desc_count.get(desc, 0) + 1
            main_desc = max(desc_count, key=desc_count.get).capitalize()
            main_icon = info['icons'][0]  # Ícono del primer pronóstico del día
            dt = datetime.strptime(date, '%Y-%m-%d')
            day_name = days_es.get(dt.strftime('%A'), dt.strftime('%A'))
            date_short = dt.strftime('%d/%m')
            forecast_list.append({
                'day_name': day_name,
                'date_short': date_short,
                'min_temp': min_temp,
                'max_temp': max_temp,
                'description': main_desc,
                'icon': main_icon
            })
    
    return render_template('clima.html', breadcrumb=["Inicio", "Clima"], forecast=forecast_list, **weather_info)

@app.route('/calidad-aire', methods=['GET', 'POST'])
def calidad_aire():
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        return "Error: API key no configurada. Establece la variable de entorno OPENWEATHER_API_KEY."
    
    city = request.form.get('city') or request.args.get('city')
    if not city:
        return render_template('calidad_aire.html', breadcrumb=["Inicio", "Calidad del Aire"])
    
    # Primero obtener coordenadas de la ciudad
    url_weather = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=es'
    response_weather = requests.get(url_weather)
    if response_weather.status_code != 200:
        error_msg = f"Error al obtener coordenadas para {city}: {response_weather.status_code}"
        return render_template('calidad_aire.html', breadcrumb=["Inicio", "Calidad del Aire"], error=error_msg, city=city)
    
    weather_data = response_weather.json()
    lat = weather_data['coord']['lat']
    lon = weather_data['coord']['lon']
    
    # Obtener datos de calidad del aire
    url_air = f'http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}'
    response_air = requests.get(url_air)
    if response_air.status_code != 200:
        error_msg = f"Error al obtener datos de calidad del aire para {city}: {response_air.status_code}"
        return render_template('calidad_aire.html', breadcrumb=["Inicio", "Calidad del Aire"], error=error_msg, city=city)
    
    air_data = response_air.json()
    components = air_data['list'][0]['components']
    aqi = air_data['list'][0]['main']['aqi']
    
    # Interpretar el índice AQI
    aqi_descriptions = {
        1: {'level': 'Buena', 'color': 'success', 'description': 'La calidad del aire es satisfactoria y no representa riesgo para la salud.'},
        2: {'level': 'Aceptable', 'color': 'warning', 'description': 'La calidad del aire es aceptable. Sin embargo, puede haber un riesgo moderado para la salud de un número muy pequeño de personas.'},
        3: {'level': 'Moderada', 'color': 'warning', 'description': 'Miembros de grupos sensibles pueden experimentar efectos en la salud. El público en general no debería verse afectado.'},
        4: {'level': 'Mala', 'color': 'danger', 'description': 'Todos pueden comenzar a experimentar efectos en la salud; miembros de grupos sensibles pueden experimentar efectos más graves.'},
        5: {'level': 'Muy Mala', 'color': 'danger', 'description': 'Advertencia de salud: todos pueden experimentar efectos más graves en la salud.'}
    }
    
    aqi_info = aqi_descriptions.get(aqi, {'level': 'Desconocido', 'color': 'secondary', 'description': 'No se pudo determinar la calidad del aire.'})
    
    air_quality_info = {
        'city': city,
        'aqi': aqi,
        'aqi_level': aqi_info['level'],
        'aqi_color': aqi_info['color'],
        'aqi_description': aqi_info['description'],
        'co': components.get('co', 0),
        'no': components.get('no', 0),
        'no2': components.get('no2', 0),
        'o3': components.get('o3', 0),
        'so2': components.get('so2', 0),
        'pm2_5': components.get('pm2_5', 0),
        'pm10': components.get('pm10', 0),
        'nh3': components.get('nh3', 0),
        'lat': lat,
        'lon': lon
    }
    
    return render_template('calidad_aire.html', breadcrumb=["Inicio", "Calidad del Aire"], **air_quality_info)

@app.route('/videos')
def videos():
    api_key = os.environ.get('YOUTUBE_API_KEY')
    if not api_key:
        return "Error: API key de YouTube no configurada. Establece la variable de entorno YOUTUBE_API_KEY."
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.search().list(
        q='medio ambiente',
        part='snippet',
        type='video',
        maxResults=10
    )
    response = request.execute()
    videos_list = []
    for item in response['items']:
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        description = item['snippet']['description']
        thumbnail = item['snippet']['thumbnails']['default']['url']
        videos_list.append({
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail
        })
    return render_template('videos.html', breadcrumb=["Inicio", "Videos"], videos=videos_list)

@app.route('/noticias')
def noticias():
    categoria = request.args.get('categoria', 'medio ambiente')
    api_key = os.environ.get('NEWSDATA_API_KEY')
    if not api_key:
        return "Error: API key de NewsData no configurada. Establece la variable de entorno NEWSDATA_API_KEY."
    url = f'https://newsdata.io/api/1/news?apikey={api_key}&q={categoria}&language=es&size=10'
    response = requests.get(url)
    print(f"Status de la API de noticias: {response.status_code}")
    news_list = []
    if response.status_code == 200:
        data = response.json()
        print(f"Datos obtenidos: {len(data.get('results', []))} artículos")
        for article in data.get('results', []):
            news_list.append({
                'title': article.get('title') or 'Sin título',
                'description': article.get('description') or 'Sin descripción',
                'link': article.get('link') or '#',
                'image_url': article.get('image_url') or 'https://via.placeholder.com/300x200?text=Sin+Imagen',
                'pubDate': article.get('pubDate') or 'Fecha desconocida'
            })
    else:
        print(f"Error en la API: {response.text}")
    print(f"Total de noticias procesadas: {len(news_list)}")
    return render_template('noticias.html', breadcrumb=["Inicio", "Noticias"], news=news_list, categoria_actual=categoria)

@app.route('/calculadora', methods=['GET', 'POST'])
def calculadora():
    resultado = None
    if request.method == 'POST':
        try:
            # Factores de emisión aproximados (kg CO2 por unidad)
            electrico = float(request.form.get('electrico', 0)) * 0.5  # kWh * factor
            transporte = float(request.form.get('transporte', 0)) * 0.2  # km * factor
            carne = float(request.form.get('carne', 0)) * 50  # kg * factor
            vuelo = float(request.form.get('vuelo', 0)) * 0.25  # horas * factor
            
            resultado = electrico + transporte + carne + vuelo
        except ValueError:
            resultado = "Error: Ingresa valores numéricos válidos."
    
    return render_template('calculadora.html', breadcrumb=["Inicio", "Calculadora"], resultado=resultado)

@app.route('/eventos', methods=['GET'])
def eventos():
    # Temporalmente sin bbox para mostrar eventos globales y probar filtros
    url = 'https://eonet.gsfc.nasa.gov/api/v2.1/events?limit=50&days=60'
    try:
        response = requests.get(url, timeout=10)
        events_list = []
        all_categories = set()
        if response.status_code == 200:
            data = response.json()
            for event in data.get('events', []):
                # Obtener coordenadas (última geometría si hay múltiples)
                geometries = event.get('geometries', [])
                if geometries:
                    coords = geometries[-1]['coordinates']  # [lon, lat] para Point
                    lat, lon = coords[1], coords[0] if len(coords) == 2 else (None, None)
                else:
                    lat, lon = None, None
                
                category = event['categories'][0]['title'] if event['categories'] else 'Desconocido'
                all_categories.add(category)
                events_list.append({
                    'id': event['id'],
                    'title': event['title'],
                    'description': event.get('description', 'Sin descripción'),
                    'category': category,
                    'date': event.get('date', 'Fecha desconocida'),
                    'lat': lat,
                    'lon': lon
                })
        else:
            events_list = [{'error': f'Error de la API de NASA: Código {response.status_code}'}]
    except requests.RequestException as e:
        events_list = [{'error': f'Error de conexión a la API: {str(e)}'}]
    
    # Agregar categorías comunes si no hay suficientes eventos
    possible_categories = {'Volcanoes', 'Earthquakes', 'Storms', 'Wildfires', 'Floods', 'Droughts', 'Severe Storms', 'Landslides'}
    all_categories.update(possible_categories)
    
    # Filtrar por categoría si se especifica
    selected_category = request.args.get('category')
    if selected_category:
        events_list = [e for e in events_list if isinstance(e, dict) and e.get('category') == selected_category]
    
    # Si no hay eventos después de filtrar, mostrar mensaje
    if not events_list and 'error' not in (events_list[0] if events_list else {}):
        events_list = [{'no_results': 'No se encontraron eventos con los filtros aplicados. Intenta con otra categoría.'}]
    
    return render_template('eventos.html', breadcrumb=["Inicio", "Eventos Ambientales"], events=events_list, all_categories=sorted(all_categories), selected_category=selected_category)

if __name__ == '__main__':
    app.run(debug=True)
