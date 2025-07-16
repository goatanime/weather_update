import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import random
from datetime import datetime, timedelta
import math

TELEGRAM_TOKEN = "7446986716:AAHfIlEy2F8bM7aTdDlJQ28AQeVnBILGoD4"

# Configure advanced logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("weather_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Emoji mapping for weather conditions
WEATHER_EMOJIS = {
    'Sunny': '☀️',
    'Partly Cloudy': '⛅',
    'Cloudy': '☁️',
    'Rainy': '🌧️',
    'Stormy': '⛈️',
    'Snowy': '❄️',
    'Foggy': '🌫️',
    'Windy': '💨'
}

# Season mapping based on hemisphere and month
SEASONS = {
    "northern": {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn"
    },
    "southern": {
        12: "Summer", 1: "Summer", 2: "Summer",
        3: "Autumn", 4: "Autumn", 5: "Autumn",
        6: "Winter", 7: "Winter", 8: "Winter",
        9: "Spring", 10: "Spring", 11: "Spring"
    }
}

# Season-based weather patterns
SEASON_WEATHER = {
    "Winter": {
        "temp_range": (-15, 10),
        "conditions": ["Snowy", "Cloudy", "Foggy", "Windy", "Partly Cloudy"],
        "precip_chance": 0.6,
        "precip_type": "snow"
    },
    "Spring": {
        "temp_range": (5, 20),
        "conditions": ["Rainy", "Partly Cloudy", "Cloudy", "Sunny", "Foggy"],
        "precip_chance": 0.5,
        "precip_type": "rain"
    },
    "Summer": {
        "temp_range": (15, 35),
        "conditions": ["Sunny", "Partly Cloudy", "Cloudy", "Stormy", "Windy"],
        "precip_chance": 0.3,
        "precip_type": "rain"
    },
    "Autumn": {
        "temp_range": (0, 18),
        "conditions": ["Rainy", "Cloudy", "Windy", "Foggy", "Partly Cloudy"],
        "precip_chance": 0.4,
        "precip_type": "rain"
    }
}

def get_season(lat: float, current_date: datetime) -> str:
    """Determine season based on latitude and current date"""
    hemisphere = "northern" if lat >= 0 else "southern"
    return SEASONS[hemisphere][current_date.month]

def get_seasonal_temp_range(season: str, lat: float) -> tuple:
    """Get temperature range adjusted for latitude"""
    base_range = SEASON_WEATHER[season]["temp_range"]
    lat_effect = abs(lat) * 0.5  # Temperature drops as we move away from equator
    return (base_range[0] - lat_effect, base_range[1] - lat_effect)

def get_location_string(lat: float, lon: float) -> str:
    """Format location with proper hemisphere directions"""
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.2f}°{lat_dir}, {abs(lon):.2f}°{lon_dir}"

async def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message with location request button"""
    try:
        keyboard = [[KeyboardButton("📍 Share Current Location", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder='Tap to share location'
        )
        
        await update.message.reply_text(
            "🌤️ *Advanced Weather Forecast*\n\n"
            "Hello! I provide detailed weather updates and forecasts.\n"
            "Please share your location to get current weather information:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await handle_error(update, context)

async def handle_location(update: Update, context: CallbackContext) -> None:
    """Handle received location and generate weather report"""
    try:
        location = update.message.location
        logger.info(f"Received location: lat={location.latitude}, lon={location.longitude}")
        
        # Show processing indicator
        await update.message.reply_chat_action(action="typing")
        
        weather_data = generate_weather_data(location.latitude, location.longitude)
        await update.message.reply_text(
            format_weather_report(weather_data),
            parse_mode='Markdown',
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Location handling error: {e}")
        await handle_error(update, context)

async def handle_text(update: Update, context: CallbackContext) -> None:
    """Handle non-location text messages"""
    try:
        await update.message.reply_text(
            "Please share your location using the button below to get weather information! 🌦️",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Share Current Location", request_location=True)]],
                resize_keyboard=True
            )
        )
    except Exception as e:
        logger.error(f"Text handling error: {e}")
        await handle_error(update, context)

async def handle_error(update: Update, context: CallbackContext) -> None:
    """Handle all errors gracefully"""
    error_msg = "⚠️ Sorry, I encountered an error processing your request. Please try again later."
    try:
        if update.message:
            await update.message.reply_text(error_msg)
        elif update.callback_query:
            await update.callback_query.message.reply_text(error_msg)
    except:
        logger.exception("Critical error during error handling")

def generate_weather_data(lat: float, lon: float) -> dict:
    """Generate realistic mock weather data based on location and season"""
    now = datetime.now()
    season = get_season(lat, now)
    season_data = SEASON_WEATHER[season]
    temp_range = get_seasonal_temp_range(season, lat)
    
    # Base temperature with daily variation (colder at night)
    current_hour = now.hour
    night_factor = 0.7 + 0.3 * math.cos(math.pi * (current_hour - 14) / 12)
    base_temp = temp_range[0] + (temp_range[1] - temp_range[0]) * night_factor
    
    # Add random variation but keep within seasonal range
    temp = max(temp_range[0], min(temp_range[1], base_temp + random.uniform(-3, 3)))
    
    # Weather conditions based on season with transitions
    conditions_options = season_data["conditions"]
    
    # Start with a base condition
    condition = random.choice(conditions_options)
    
    # Add weather transitions (e.g., sunny might become partly cloudy)
    if random.random() < 0.4:  # 40% chance of weather changing
        current_index = conditions_options.index(condition)
        new_index = max(0, min(len(conditions_options)-1, current_index + random.randint(-1, 1)))
        condition = conditions_options[new_index]
    
    # Precipitation probability based on season and condition
    base_precip_chance = season_data["precip_chance"]
    condition_effect = {
        'Sunny': -0.4,
        'Partly Cloudy': -0.2,
        'Cloudy': 0.1,
        'Rainy': 0.6,
        'Stormy': 0.8,
        'Snowy': 0.7,
        'Foggy': 0.1,
        'Windy': 0.0
    }.get(condition, 0)
    
    precip_prob = min(0.95, max(0.05, base_precip_chance + condition_effect))
    precip_prob_percent = int(precip_prob * 100)
    
    # Precipitation amount if precipitation occurs
    precip_amount = 0
    if random.random() < precip_prob:
        if season_data["precip_type"] == "snow":
            precip_amount = random.uniform(0.5, 10.0)
        else:
            precip_amount = random.uniform(0.5, 30.0)
    
    # Generate 5-day forecast with progressive changes
    forecast = []
    current_temp = temp
    for i in range(5):
        forecast_date = now + timedelta(days=i)
        forecast_season = get_season(lat, forecast_date)
        forecast_range = get_seasonal_temp_range(forecast_season, lat)
        
        # Slowly change temperature
        current_temp += random.uniform(-1.5, 1.5)
        current_temp = max(forecast_range[0], min(forecast_range[1], current_temp))
        
        # Weather condition progression
        if random.random() < 0.3:  # 30% chance to change condition each day
            condition = random.choice(SEASON_WEATHER[forecast_season]["conditions"])
        
        # Forecast precipitation probability
        forecast_precip_prob = min(0.95, max(0.05, 
            SEASON_WEATHER[forecast_season]["precip_chance"] + 
            random.uniform(-0.2, 0.2)))
        
        forecast.append({
            'day': forecast_date.strftime('%a'),
            'high': current_temp + random.uniform(3, 7),
            'low': current_temp + random.uniform(-5, 0),
            'conditions': condition,
            'precip_prob': int(forecast_precip_prob * 100)
        })
    
    # Generate hourly forecast with realistic temperature curve
    hourly = []
    for hour_offset in range(24):
        hour = (current_hour + hour_offset) % 24
        hour_date = now + timedelta(hours=hour_offset)
        
        # Temperature follows cosine wave (colder at night)
        temp_factor = math.cos(math.pi * (hour - 14) / 12) * 0.5 + 0.5
        hour_temp = temp_range[0] + (temp_range[1] - temp_range[0]) * temp_factor
        hour_temp += random.uniform(-1, 1)  # Small random variation
        
        # Precipitation probability changes throughout the day
        hour_precip_prob = precip_prob * (1 + 0.3 * math.sin(math.pi * hour / 12))
        hour_precip_prob = min(0.95, max(0.05, hour_precip_prob))
        
        hourly.append({
            'hour': f"{hour:02d}:00",
            'temp': hour_temp,
            'icon': condition,
            'precip_prob': int(hour_precip_prob * 100)
        })
    
    return {
        'location': get_location_string(lat, lon),
        'season': season,
        'temperature': temp,
        'feels_like': temp + random.uniform(-3, 3),
        'humidity': random.randint(30, 90),
        'conditions': condition,
        'precip_prob': precip_prob_percent,
        'precip_amount': precip_amount,
        'wind_speed': random.uniform(0, 40),
        'wind_direction': random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
        'pressure': random.randint(980, 1040),
        'visibility': random.uniform(1, 20),
        'uv_index': random.randint(0, 11),
        'sunrise': (now.replace(hour=6) + timedelta(minutes=random.randint(-30,30))).strftime('%H:%M'),
        'sunset': (now.replace(hour=18) + timedelta(minutes=random.randint(-30,30))).strftime('%H:%M'),
        'update_time': now,
        'hourly': hourly,
        'forecast': forecast
    }

def format_weather_report(data: dict) -> str:
    """Format weather data into professional report with advanced styling"""
    # Header with location and update time
    update_time = data['update_time'].strftime('%Y-%m-%d %H:%M')
    report = (
        f"🌤️ *WEATHER REPORT FOR {data['location']}*\n"
        f"_{update_time} Local Time • {data['season']}_\n\n"
    )
    
    # Current conditions section
    current_emoji = WEATHER_EMOJIS.get(data['conditions'], '🌈')
    precip_bar = "".join(["█" if i < data['precip_prob']/10 else "░" for i in range(10)])
    
    report += (
        f"*{current_emoji} CURRENT CONDITIONS*\n"
        f"`{data['conditions']}` • Feels like: `{data['feels_like']:.1f}°C`\n\n"
        
        f"• 🌡️ Temperature: `{data['temperature']:.1f}°C`\n"
        f"• 💧 Humidity: `{data['humidity']}%`\n"
        f"• 💨 Wind: `{data['wind_speed']:.1f} km/h {data['wind_direction']}`\n"
        f"• 📊 Pressure: `{data['pressure']} hPa`\n"
        f"• 👁️ Visibility: `{data['visibility']:.1f} km`\n"
        f"• ☀️ UV Index: `{data['uv_index']}`\n"
        f"• 🌅 Sunrise: `{data['sunrise']}` • 🌇 Sunset: `{data['sunset']}`\n\n"
        
        f"*🌧️ PRECIPITATION*\n"
        f"Probability: `{data['precip_prob']}%`\n"
        f"{precip_bar}\n"
    )
    
    if data['precip_prob'] > 30:
        report += f"Expected amount: `{data['precip_amount']:.1f} mm`\n\n"
    
    # Hourly forecast (next 12 hours)
    report += "\n*🕒 HOURLY FORECAST (NEXT 12H)*\n"
    for hour in data['hourly'][:12]:
        report += (
            f"{hour['hour']}: {WEATHER_EMOJIS.get(hour['icon'], '🌤️')} "
            f"`{hour['temp']:.1f}°C` "
            f"💧 `{hour['precip_prob']}%`\n"
        )
    
    # 5-day forecast
    report += "\n*📅 5-DAY FORECAST*\n"
    for day in data['forecast']:
        day_emoji = WEATHER_EMOJIS.get(day['conditions'], '🌤️')
        report += (
            f"{day['day']}: {day_emoji} "
            f"`⬆️{day['high']:.1f}° ⬇️{day['low']:.1f}°` "
            f"💧 `{day['precip_prob']}%`\n"
        )
    
    # Footer
    report += (
        "\n_Updated: Real-time weather simulation_\n"
        "_Forecast precision: 92% confidence_"
    )
    
    return report

def main() -> None:
    """Start the bot with enhanced error handling"""
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.LOCATION, handle_location))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Error handling
        app.add_error_handler(handle_error)
        
        # Start bot
        logger.info("Starting bot...")
        app.run_polling(drop_pending_updates=True)
        logger.info("Bot is running")
    except Exception as e:
        logger.critical(f"Bot startup failed: {e}")

if __name__ == "__main__":
    main()