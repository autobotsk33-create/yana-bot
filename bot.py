import asyncio
import os
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.environ["BOT_TOKEN"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SYSTEM_PROMPT = """Ты — контент-помощник мастера перманентного макияжа Яны Романенко.
Твоя задача — генерировать тексты для постов и сторис в стиле Яны.

СТИЛЬ ЯНЫ:
- Обращение строго на «вы», тепло и с заботой
- Эмодзи активно, но уместно (😍 ✨ 🔥 ❤️‍🔥 🥰 ⭐ 💌 👇 😛 👌)
- Тон: экспертный, но мягкий — как совет близкой подруги-профессионала
- Акцент на: природную красоту клиента, индивидуальный подход, авторские техники
- Структура поста: заголовок с эмодзи → боль/мечта клиента → решение → список преимуществ (через ◾) → итог → призыв записаться → вовлекающий вопрос
- В конце поста — хэштеги по теме
- Аудитория: женщины 14–70 лет
- Услуги: перманентный макияж бровей, губ, межресничка, стрелки, авторские техники (Омбрэ, акварельные губы и др.)

ЗАПРЕЩЕНО:
- Обращение на «ты»
- Грубые или агрессивные слова
- Преувеличения типа «лучший в мире»
- Медицинские обещания

Всегда пиши готовый текст, который можно сразу скопировать и опубликовать."""

# ── Клавиатуры ──────────────────────────────────────────────────────────────

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Пост для соцсетей"), KeyboardButton(text="📱 Идеи для сторис")],
            [KeyboardButton(text="🎬 Идеи для Reels"), KeyboardButton(text="❓ Частые вопросы клиентов")],
            [KeyboardButton(text="📊 Опрос для подписчиков"), KeyboardButton(text="🔥 Трендовая тема")],
        ],
        resize_keyboard=True
    )

def service_keyboard(callback_prefix: str):
    services = [
        ("Брови (Омбрэ)", "brovi_ombre"),
        ("Акварельные губы", "gubы_akv"),
        ("Межресничка", "mejresn"),
        ("Стрелочка", "strelka"),
        ("Брови + межресничка", "brovi_mejr"),
        ("Любая услуга", "any"),
    ]
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"{callback_prefix}:{key}")]
        for name, key in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

SERVICE_NAMES = {
    "brovi_ombre": "перманентный макияж бровей в технике Омбрэ",
    "gubы_akv": "акварельные губы (перманентный макияж)",
    "mejresn": "бархатная межресничка (перманентный макияж)",
    "strelka": "стрелочка (перманентный макияж)",
    "brovi_mejr": "перманентный макияж бровей и межресничка",
    "any": "перманентный макияж (услуга на выбор мастера)",
}

# ── Состояния ────────────────────────────────────────────────────────────────

class Gen(StatesGroup):
    waiting_post_service = State()
    waiting_stories_service = State()
    waiting_reels_service = State()
    waiting_faq_service = State()
    waiting_poll_service = State()
    waiting_trend_input = State()

# ── GPT-запрос ───────────────────────────────────────────────────────────────

async def ask_gpt(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
        max_tokens=1200,
    )
    return response.choices[0].message.content.strip()

# ── Хэндлеры ─────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помогу Яне создавать контент для соцсетей.\n\n"
        "Выберите, что нужно сгенерировать 👇",
        reply_markup=main_keyboard()
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📌 <b>Что я умею:</b>\n\n"
        "✍️ <b>Пост</b> — готовый текст для TG, VK, Instagram\n"
        "📱 <b>Сторис</b> — 3–5 идей со сценарием\n"
        "🎬 <b>Reels</b> — концепция и текст для видео\n"
        "❓ <b>Частые вопросы</b> — пост в формате вопрос/ответ\n"
        "📊 <b>Опрос</b> — вовлекающий опрос для подписчиков\n"
        "🔥 <b>Тренд</b> — пост на актуальную тему\n\n"
        "Просто нажмите нужную кнопку ниже 👇",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )

# ─── ПОСТ ───

@dp.message(F.text == "✍️ Пост для соцсетей")
async def post_choose_service(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_post_service)
    await message.answer("По какой услуге написать пост?", reply_markup=service_keyboard("post"))

@dp.callback_query(Gen.waiting_post_service, F.data.startswith("post:"))
async def post_generate(call: CallbackQuery, state: FSMContext):
    service_key = call.data.split(":")[1]
    service = SERVICE_NAMES[service_key]
    await state.clear()
    await call.message.edit_text(f"⏳ Генерирую пост про «{service}»...")
    text = await ask_gpt(
        f"Напиши готовый пост для Instagram/VK/Telegram про услугу: {service}. "
        "Строго в стиле Яны: заголовок с эмодзи, мечта клиента, список преимуществ через ◾, "
        "призыв записаться, вовлекающий вопрос в конце, хэштеги."
    )
    await call.message.answer(text)
    await call.message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ─── СТОРИС ───

@dp.message(F.text == "📱 Идеи для сторис")
async def stories_choose(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_stories_service)
    await message.answer("По какой услуге придумать сторис?", reply_markup=service_keyboard("stories"))

@dp.callback_query(Gen.waiting_stories_service, F.data.startswith("stories:"))
async def stories_generate(call: CallbackQuery, state: FSMContext):
    service_key = call.data.split(":")[1]
    service = SERVICE_NAMES[service_key]
    await state.clear()
    await call.message.edit_text(f"⏳ Придумываю идеи сторис про «{service}»...")
    text = await ask_gpt(
        f"Придумай 4 идеи для сторис в Instagram/Telegram про услугу: {service}. "
        "Для каждой сторис укажи: 1) заголовок, 2) краткий сценарий (что показать/написать), "
        "3) текст для слайда с эмодзи. Стиль Яны: тепло, на «вы», с заботой о клиенте."
    )
    await call.message.answer(text)
    await call.message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ─── REELS ───

@dp.message(F.text == "🎬 Идеи для Reels")
async def reels_choose(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_reels_service)
    await message.answer("По какой услуге сделать идею Reels?", reply_markup=service_keyboard("reels"))

@dp.callback_query(Gen.waiting_reels_service, F.data.startswith("reels:"))
async def reels_generate(call: CallbackQuery, state: FSMContext):
    service_key = call.data.split(":")[1]
    service = SERVICE_NAMES[service_key]
    await state.clear()
    await call.message.edit_text(f"⏳ Создаю концепцию Reels про «{service}»...")
    text = await ask_gpt(
        f"Придумай концепцию короткого видео (Reels/TikTok) про услугу: {service}. "
        "Укажи: 1) цепляющий первый кадр, 2) структуру видео по секундам (до 30 сек), "
        "3) текст для подписи к видео в стиле Яны с эмодзи и хэштегами, "
        "4) идею для обложки. Стиль Яны: тепло, на «вы», экспертно."
    )
    await call.message.answer(text)
    await call.message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ─── ЧАСТЫЕ ВОПРОСЫ ───

@dp.message(F.text == "❓ Частые вопросы клиентов")
async def faq_choose(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_faq_service)
    await message.answer("По какой услуге написать пост с вопросами?", reply_markup=service_keyboard("faq"))

@dp.callback_query(Gen.waiting_faq_service, F.data.startswith("faq:"))
async def faq_generate(call: CallbackQuery, state: FSMContext):
    service_key = call.data.split(":")[1]
    service = SERVICE_NAMES[service_key]
    await state.clear()
    await call.message.edit_text(f"⏳ Генерирую вопросы-ответы про «{service}»...")
    text = await ask_gpt(
        f"Напиши пост в формате «Вопрос — Ответ» про услугу: {service}. "
        "5 самых частых вопросов клиентов с подробными ответами. "
        "Стиль Яны: тепло, на «вы», экспертно, с эмодзи. "
        "В конце — призыв записаться на консультацию."
    )
    await call.message.answer(text)
    await call.message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ─── ОПРОС ───

@dp.message(F.text == "📊 Опрос для подписчиков")
async def poll_choose(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_poll_service)
    await message.answer("По какой теме сделать опрос?", reply_markup=service_keyboard("poll"))

@dp.callback_query(Gen.waiting_poll_service, F.data.startswith("poll:"))
async def poll_generate(call: CallbackQuery, state: FSMContext):
    service_key = call.data.split(":")[1]
    service = SERVICE_NAMES[service_key]
    await state.clear()
    await call.message.edit_text(f"⏳ Придумываю опрос про «{service}»...")
    text = await ask_gpt(
        f"Придумай 3 варианта вовлекающего опроса для подписчиков на тему: {service}. "
        "Для каждого укажи: 1) вопрос для опроса, 2) варианты ответов (3–4 штуки), "
        "3) короткий текст-подводку с эмодзи в стиле Яны. "
        "Опросы должны быть интересными, побуждать к взаимодействию."
    )
    await call.message.answer(text)
    await call.message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ─── ТРЕНД ───

@dp.message(F.text == "🔥 Трендовая тема")
async def trend_ask(message: Message, state: FSMContext):
    await state.set_state(Gen.waiting_trend_input)
    await message.answer(
        "Напишите тренд или тему, которую хотите обыграть.\n\n"
        "Например: «натуральный макияж», «уход за кожей после лета», «осенние оттенки» 👇"
    )

@dp.message(Gen.waiting_trend_input)
async def trend_generate(message: Message, state: FSMContext):
    trend = message.text
    await state.clear()
    await message.answer(f"⏳ Создаю пост на тему «{trend}»...")
    text = await ask_gpt(
        f"Напиши трендовый пост для Instagram/VK/Telegram на тему: «{trend}», "
        "связав её с перманентным макияжем и услугами Яны Романенко. "
        "Стиль Яны: заголовок с эмодзи, тепло на «вы», список преимуществ через ◾, "
        "призыв записаться, хэштеги в конце."
    )
    await message.answer(text)
    await message.answer("Выберите следующее действие 👇", reply_markup=main_keyboard())

# ── Запуск ───────────────────────────────────────────────────────────────────

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
