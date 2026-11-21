import telebot
import requests

BOT_TOKEN = "9174067829:AAGo2ALwNx1-2R-N5zg9ukHU_LaQJwMhuK4"
DEEPSEEK_KEY = "sk-96929f8dae9441b594fc8ab611e60402"

bot = telebot.TeleBot(BOT_TOKEN)

PROMPT = "You are a content assistant for Yana Romanenko, a permanent makeup master. Write posts in Russian, addressing clients as 'vy' (formal). Use emojis, warm tone, expert style. Structure: headline with emoji, client dream, benefits list with diamond bullet, call to action, engaging question, hashtags."

SERVICES = {
    "b1": "permanentnyy makiyazh brovey v tekhnike Ombre",
    "b2": "akvarel'nyye guby (permanentnyy makiyazh)",
    "b3": "barkhatnaya mezhresniczka (permanentnyy makiyazh)",
    "b4": "strelochka (permanentnyy makiyazh)",
    "b5": "permanentnyy makiyazh brovey i mezhresniczka",
}

SERVICE_NAMES = {
    "b1": "Brovi Ombre",
    "b2": "Akvarel'nyye guby",
    "b3": "Mezhresniczka",
    "b4": "Strelochka",
    "b5": "Brovi + mezhresniczka",
}

def ask(text):
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + DEEPSEEK_KEY, "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}], "max_tokens": 800},
            timeout=60
        )
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return "Oshibka: " + str(data)
    except Exception as e:
        return "Oshibka: " + str(e)

def main_kb():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Post", "Storis")
    kb.row("Reels", "Voprosy")
    kb.row("Opros", "Trend")
    return kb

def service_kb(prefix):
    kb = telebot.types.InlineKeyboardMarkup()
    for key, name in SERVICE_NAMES.items():
        kb.add(telebot.types.InlineKeyboardButton(name, callback_data=prefix + ":" + key))
    return kb

user_mode = {}

@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "Privet! Vyberi chto nuzhno:", reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text in ["Post", "Storis", "Reels", "Voprosy", "Opros"])
def choose(m):
    user_mode[m.chat.id] = m.text
    bot.send_message(m.chat.id, "Po kakoy usluge?", reply_markup=service_kb(m.text))

@bot.message_handler(func=lambda m: m.text == "Trend")
def trend(m):
    user_mode[m.chat.id] = "Trend"
    bot.send_message(m.chat.id, "Napishite temu:")

@bot.message_handler(func=lambda m: user_mode.get(m.chat.id) == "Trend" and m.text != "Trend")
def trend_gen(m):
    user_mode.pop(m.chat.id, None)
    bot.send_message(m.chat.id, "Generiruyu...")
    result = ask("Napishi post pro trend: " + m.text + " svyazav s permanentnym makiyazhem Yany Romanenko.")
    bot.send_message(m.chat.id, result, reply_markup=main_kb())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    parts = c.data.split(":")
    action = parts[0]
    key = parts[1]
    service = SERVICES.get(key, "permanentnyy makiyazh")
    bot.edit_message_text("Generiruyu...", c.message.chat.id, c.message.message_id)
    if action == "Post":
        p = "Napishi post dlya Instagram/VK/Telegram pro: " + service
    elif action == "Storis":
        p = "Придумай 4 идеи для сторис про: " + service
    elif action == "Reels":
        p = "Придумай концепцию Reels про: " + service
    elif action == "Voprosy":
        p = "Napishi post vopros-otvet pro: " + service + " 5 voprosov."
    else:
        p = "Придумай 3 варианта опроса для подписчиков про: " + service
    result = ask(p)
    bot.send_message(c.message.chat.id, result, reply_markup=main_kb())

bot.polling(none_stop=True)
