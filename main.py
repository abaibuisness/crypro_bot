import telebot
from telebot import types
from datetime import datetime, timedelta
import os
import requests
import base64

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(API_TOKEN)
subscriptions = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 Analyze Chart", "💰 Prices")
    markup.row("🔐 Buy Subscription", "📅 Check Access")
    bot.send_message(message.chat.id,
                     "Welcome to the CryptoAI Bot!\n\nI can analyze crypto charts from images and track top coin prices.\n\nChoose an option below:",
                     reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "📅 Check Access")
def check_access(message):
    user_id = message.chat.id
    if user_id in subscriptions and subscriptions[user_id] > datetime.now():
        remaining = subscriptions[user_id] - datetime.now()
        bot.send_message(user_id, f"✅ You have access for {remaining.days} more day(s).")
    else:
        bot.send_message(user_id, "❌ You don't have an active subscription.")

@bot.message_handler(func=lambda msg: msg.text == "📊 Analyze Chart")
def analyze_chart(message):
    user_id = message.chat.id
    if user_id not in subscriptions or subscriptions[user_id] < datetime.now():
        bot.send_message(user_id, "❌ You need a subscription to use this feature.\nUse '🔐 Buy Subscription'")
        return
    bot.send_message(user_id, "Please send a chart image for analysis.")

@bot.message_handler(func=lambda msg: msg.text == "💰 Prices")
def show_prices(message):
    bot.send_message(message.chat.id, "Type /price BTC or /price ETH to get current info.")

@bot.message_handler(func=lambda msg: msg.text == "🔐 Buy Subscription")
def buy_subscription(message):
    bot.send_message(message.chat.id,
                     "To buy a subscription, pay via @CryptoBot to this wallet:\n\nTON: EQ...XYZ\n\nThen send the transaction ID to the admin @your_admin_username.")

@bot.message_handler(commands=['price'])
def get_price(message):
    try:
        coin = message.text.split()[1].lower()
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        response = requests.get(url).json()
        if coin in response:
            price = response[coin]["usd"]
            bot.send_message(message.chat.id, f"Current {coin.upper()} price: ${price}")
        else:
            bot.send_message(message.chat.id, "Coin not found.")
    except:
        bot.send_message(message.chat.id, "Usage: /price BTC")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    if user_id not in subscriptions or subscriptions[user_id] < datetime.now():
        bot.send_message(user_id, "❌ You need an active subscription to analyze charts.")
        return
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open("received_chart.jpg", 'wb') as f:
        f.write(downloaded_file)

    with open("received_chart.jpg", "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        "You are an expert crypto market analyst. Analyze the chart in this image. "
        "Predict the next short-term price movement (UP, DOWN, SIDEWAYS), give a confidence level (in %), "
        "and explain your reasoning briefly."
    )

    payload = {
        "model": "mixtral-8x7b",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        result = r.json()["choices"][0]["message"]["content"]
        bot.send_message(user_id, f"AI Analysis Result:\n{result}")
    except Exception as e:
        bot.send_message(user_id, f"Error during AI analysis: {e}")

@bot.message_handler(commands=['activate'])
def activate_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    try:
        _, uid, days = message.text.split()
        uid = int(uid)
        days = int(days)
        subscriptions[uid] = datetime.now() + timedelta(days=days)
        bot.send_message(uid, f"✅ Access granted for {days} day(s)!")
        bot.send_message(message.chat.id, "Done.")
    except:
        bot.send_message(message.chat.id, "Use format: /activate <user_id> <days>")

bot.infinity_polling()
