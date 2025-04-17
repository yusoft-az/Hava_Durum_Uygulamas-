# backend.py
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, date
from collections import defaultdict

# --- Ayarlar ---
API_KEY = "685fcd55c70c00d47287238952df5e6b"
UNITS = "metric"
LANG = "tr"
SUGGESTION_LIMIT = 5

# --- Asset Paths ---
try:
    base_path = os.path.dirname(os.path.realpath(__file__))
except NameError:
    base_path = os.getcwd()
ASSETS_PATH = os.path.join(base_path, "assets")
BG_IMAGE_PATH = os.path.join(ASSETS_PATH, "gifs")
DEFAULT_BG_IMAGE_NAME = "1.jpg"

WEATHER_IMAGE_MAP = {
    "clear": "clear.gif", 
    "clouds": "clouds.gif", 
    "rain": "rain.gif",
    "drizzle": "rain1.gif", 
    "thunderstorm": "thunderstorm.jpg", 
    "snow": "snow.gif",
    "mist": "smoke.gif", 
    "smoke": "smoke.gif", 
    "haze": "smoke.gif",
    "dust": "dust.webp", 
    "fog": "fog.jpg", 
    "sand": "smoke.gif",
    "ash": "smoke.gif", 
    "squall": "clouds.gif", 
    "tornado": "thunderstorm.jpg",
}

# --- Yardımcı Fonksiyonlar ---

def get_city_suggestions_api(query, api_key, limit=5):
    if not query or len(query) < 2: return []
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit={limit}&appid={api_key}"
    suggestions = []
    try:
        response = requests.get(geo_url, timeout=5)
        response.raise_for_status(); data = response.json()
        if data:
             unique_suggestions = {}
             for item in data:
                 unique_key = (item.get('name', '').lower(), item.get('country', '').lower())
                 if unique_key not in unique_suggestions:
                     state = f", {item.get('state')}" if item.get('state') else ""; country = item.get('country', '')
                     display_name = f"{item.get('name', 'Bilinmeyen')}{state}, {country}"
                     unique_suggestions[unique_key] = {'display': display_name, 'name': item.get('name'), 'country': country}
             suggestions = list(unique_suggestions.values())[:limit]
    except Exception as e: print(f"Şehir önerisi API hatası: {e}")
    return suggestions

def get_coordinates(city, api_key, country=""):
    query = f"{city},{country}" if country else city
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=1&appid={api_key}"
    try:
        response = requests.get(geo_url, timeout=10)
        response.raise_for_status(); data = response.json()
        if data: return data[0]['lat'], data[0]['lon'], data[0].get('country', ''), data[0]['name']
        else: return None, None, None, None
    except Exception as e: print(f"Koordinat hatası: {e}"); return None, None, None, None


# <<< DEĞİŞTİRİLEN FONKSİYON BAŞLANGICI >>>
def get_current_weather(lat, lon, api_key, units='metric', lang='en'):
    """Belirtilen koordinatlar için MEVCUT hava durumunu alır (Detaylı Hata Ayıklama ile)."""
    if lat is None or lon is None:
        print("!!! get_current_weather: Lat veya Lon None geldi, mevcut hava durumu alınamıyor.")
        return None

    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"
    print(f"--- İstek Yapılan Hava Durumu URL: {weather_url}") # URL'yi kontrol et

    try:
        response = requests.get(weather_url, timeout=10)
        print(f"--- Hava Durumu API Yanıt Kodu: {response.status_code}") # Yanıt kodunu gör

        # Hata kodu varsa (4xx veya 5xx) exception fırlat
        response.raise_for_status()
        # Başarılı ise JSON döndür
        print("--- Hava durumu verisi başarıyla alındı.")
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        # Özellikle HTTP hatalarını yakala (401, 404, 429 vb.)
        print(f"!!! Mevcut hava durumu HTTP hatası: {http_err}")
        try:
            # API'den gelen hata mesajını yazdırmayı dene
            print(f"--- API Yanıt İçeriği: {response.text}")
        except Exception:
            print("--- API Yanıt içeriği okunamadı.")
        return None
    except requests.exceptions.RequestException as req_err:
        # Diğer ağ hatalarını yakala (timeout, bağlantı hatası vb.)
        print(f"!!! Mevcut hava durumu Ağ/İstek hatası: {req_err}")
        return None
    except Exception as e:
        # Diğer beklenmedik hatalar (örn. JSON parse hatası)
        print(f"!!! Mevcut hava durumu Genel Hata: {type(e).__name__}: {e}")
        return None
# <<< DEĞİŞTİRİLEN FONKSİYON SONU >>>


def get_forecast_data(lat, lon, api_key, units='metric', lang='en'):
    if lat is None or lon is None: return None
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"
    try:
        response = requests.get(forecast_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Tahmin verisi hatası: {e}")
        return None

def process_daily_forecast(forecast_list):
    daily_summary = defaultdict(lambda: {'temps': [], 'icons': [], 'dt': None}); today = date.today(); processed_dates = set()
    for item in forecast_list:
        item_datetime = datetime.fromtimestamp(item['dt']); item_date = item_datetime.date()
        if item_date < today or (len(processed_dates) >= 5 and item_date not in processed_dates): continue
        processed_dates.add(item_date)
        if daily_summary[item_date]['dt'] is None: daily_summary[item_date]['dt'] = item['dt']
        if 'main' in item and 'temp' in item['main']: daily_summary[item_date]['temps'].append(item['main']['temp'])
        if 'weather' in item and item['weather']: daily_summary[item_date]['icons'].append(item['weather'][0]['icon'])
    processed_daily = []
    days_tr_short = {0: "Pzt", 1: "Sal", 2: "Çar", 3: "Per", 4: "Cum", 5: "Cmt", 6: "Paz"}
    for d_date in sorted(daily_summary.keys()):
        summary = daily_summary[d_date]; icon_to_use = '01d'
        if summary['icons']:
            icon_counts = defaultdict(int);
            for icon in summary['icons']: icon_counts[icon] += 1
            if icon_counts: day_icons = {k: v for k, v in icon_counts.items() if 'd' in k}; icon_to_use = max(day_icons, key=day_icons.get) if day_icons else max(icon_counts, key=icon_counts.get)
        dt_object = datetime.fromtimestamp(summary['dt'])
        day_name_str = "Bugün" if dt_object.date() == date.today() else days_tr_short.get(dt_object.weekday(), dt_object.strftime('%a'))
        day_data = {'day': day_name_str,'dt': summary['dt'],'temp_min': min(summary['temps']) if summary['temps'] else None,'temp_max': max(summary['temps']) if summary['temps'] else None,'icon': icon_to_use}; processed_daily.append(day_data);
        if len(processed_daily) >= 5: break
    return processed_daily

# --- Flask App ---
app = Flask(__name__)
CORS(app)

@app.route('/suggestions')
def get_suggestions_route():
    query = request.args.get('q')
    if not query: return jsonify([])
    suggestions = get_city_suggestions_api(query, API_KEY, SUGGESTION_LIMIT)
    return jsonify(suggestions)

@app.route('/weather')
def get_weather_route():
    city = request.args.get('city')
    country = request.args.get('country', '')
    if not city: return jsonify({"success": False, "message": "Şehir parametresi eksik"}), 400

    lat, lon, found_country, geocoded_city_name = get_coordinates(city, API_KEY, country)
    if lat is None or lon is None: return jsonify({"success": False, "message": f"'{city}' şehri bulunamadı veya koordinat alınamadı"}), 404

    print(f"--- Hava durumu alınıyor: {geocoded_city_name} ({lat}, {lon}) ---")
    current_weather_data = get_current_weather(lat, lon, API_KEY, UNITS, LANG)

    # <<< ÖNEMLİ KONTROL: Mevcut hava durumu alınamadıysa burada dur >>>
    if not current_weather_data:
        print(f"!!! get_weather_route: get_current_weather None döndürdü. İşlem durduruluyor.")
        return jsonify({"success": False, "message": "Mevcut hava durumu verisi alınamadı (API hatası olabilir)"}), 500

    print(f"--- Tahmin verisi alınıyor: {geocoded_city_name} ({lat}, {lon}) ---")
    forecast_data_raw = get_forecast_data(lat, lon, API_KEY, UNITS, LANG)
    hourly_forecast = []; daily_forecast_processed = []; background_image_name = DEFAULT_BG_IMAGE_NAME

    if forecast_data_raw and 'list' in forecast_data_raw:
        for item in forecast_data_raw['list'][:8]: hourly_forecast.append({'time': datetime.fromtimestamp(item['dt']).strftime('%H:%M'),'temp': item['main']['temp'] if 'main' in item and 'temp' in item['main'] else None,'icon': item['weather'][0]['icon'] if 'weather' in item and item['weather'] else '01d'})
        daily_forecast_processed = process_daily_forecast(forecast_data_raw['list'])
    else:
        print("--- Uyarı: Tahmin verisi alınamadı veya liste boş.")

    weather_main_condition = ""
    if 'weather' in current_weather_data and current_weather_data['weather']:
        weather_main_condition = current_weather_data['weather'][0]['main'].lower()
        background_image_name = WEATHER_IMAGE_MAP.get(weather_main_condition, DEFAULT_BG_IMAGE_NAME)

    result = {
        "success": True,
        "city": {"name": geocoded_city_name, "country": found_country, "lat": lat, "lon": lon},
        "current": {
            "temp": current_weather_data['main']['temp'] if 'main' in current_weather_data and 'temp' in current_weather_data['main'] else None,
            "desc": current_weather_data['weather'][0]['description'].capitalize() if 'weather' in current_weather_data and current_weather_data['weather'] else "---",
            "icon": current_weather_data['weather'][0]['icon'] if 'weather' in current_weather_data and current_weather_data['weather'] else '01d',
            "temp_min": daily_forecast_processed[0]['temp_min'] if daily_forecast_processed else None,
            "temp_max": daily_forecast_processed[0]['temp_max'] if daily_forecast_processed else None,
            "condition_code": weather_main_condition,
            "background_image": background_image_name
        },
        "hourly": hourly_forecast, "daily": daily_forecast_processed
    }
    return jsonify(result)

if __name__ == '__main__':
    if not API_KEY or API_KEY == "YOUR_OPENWEATHERMAP_API_KEY" or len(API_KEY) < 30: print("HATA: Geçerli API anahtarı girin!"); sys.exit(1)
    print("Flask sunucusu http://localhost:5000 üzerinde başlatılıyor...")
    app.run(debug=True)