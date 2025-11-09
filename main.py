import asyncio
import random
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8596365784:AAHWjAqTtZyDLByoEcQOsJzQ4m0pRuTmVI4"
CRYPTO_PAY_API = "485218:AAjb3wYNaWZ9oWKLXNo8GtbKyY8NLwgMWpn"
ADMINS = [5843160521, 5532984989]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# простое хранение кошельков в памяти
wallets = {
    "USDT": "—",
    "BTC": "—",
    "ETH": "—",
    "TON": "—",
    "BNB": "—",
    "TRX": "—",
    "SOL": "—",
}


# ========== СОСТОЯНИЯ ==========
class TopUpState(StatesGroup):
    waiting_for_amount = State()       # для CryptoBot
    waiting_for_crypto_amount = State()  # для ручной крипты (с конвертацией)
    waiting_for_crypto_choice = State()  # выбор валюты


class BuyCustomState(StatesGroup):
    waiting_for_quantity = State()


class AdminState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_wallet = State()


# ========== КЛАВЫ ==========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить аккаунты", callback_data="buy")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balance")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])


def pay_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить с баланса", callback_data="pay_balance")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")],
    ])


def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉ Связаться с поддержкой", url="https://t.me/fbaccsupport")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")],
    ])


def balance_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="crypto_bot")],
        [InlineKeyboardButton(text="💎 Криптовалюты", callback_data="manual_crypto")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")],
    ])


# ========== /start и назад ==========
@dp.message(CommandStart())
async def start(message: Message):
    await send_main_menu(message)


@dp.callback_query(F.data == "back")
async def back(callback_query: CallbackQuery):
    await send_main_menu(callback_query.message)
    await callback_query.answer()


async def send_main_menu(msg):
    text = (
        "<b>Добро пожаловать в Stripe Seller Bot ✨</b>\n\n"
        "Качественные Stripe-аккаунты с балансом 💰\n"
        "Выбирай действие ниже 👇"
    )
    photo = FSInputFile("welcome.jpg")
    await msg.answer_photo(photo=photo, caption=text, reply_markup=main_menu())


# ========== КУПИТЬ АККАУНТЫ ==========
@dp.callback_query(F.data == "buy")
async def buy_accounts(callback_query: CallbackQuery):
    text = (
        "🛒 <b>Шаг 1 из 3 — выбор количества</b>\n\n"
        "💎 Прайс-лист:\n"
        "✨ 1–20 шт → 10 $/акк\n"
        "🚀 21–50 шт → 9 $/акк\n"
        "💎 51–100 шт → 8 $/акк\n\n"
        "🎯 Выбери пак или своё количество 👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Lite (1 акк — 10 $)", callback_data="pack_1")],
        [InlineKeyboardButton(text="🚀 Starter (3 акка — 30 $)", callback_data="pack_3")],
        [InlineKeyboardButton(text="💡 Smart (5 акков — 50 $)", callback_data="pack_5")],
        [InlineKeyboardButton(text="🔥 Pro (10 акков — 100 $)", callback_data="pack_10")],
        [InlineKeyboardButton(text="💎 Premium (20 акков — 200 $)", callback_data="pack_20")],
        [InlineKeyboardButton(text="⚡ Ultimate (30 акков — 270 $)", callback_data="pack_30")],
        [InlineKeyboardButton(text="🎯 Своё количество", callback_data="custom_pack")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")],
    ])
    photo = FSInputFile("buy.jpg")
    await callback_query.message.answer_photo(photo=photo, caption=text, reply_markup=kb)
    await callback_query.answer()


@dp.callback_query(F.data.startswith("pack_"))
async def handle_pack(callback_query: CallbackQuery):
    pack_prices = {
        "pack_1": (1, 10),
        "pack_3": (3, 30),
        "pack_5": (5, 50),
        "pack_10": (10, 100),
        "pack_20": (20, 200),
        "pack_30": (30, 270),
    }
    qty, total = pack_prices[callback_query.data]
    await send_pay_screen(callback_query.message, qty, total)
    await callback_query.answer()


@dp.callback_query(F.data == "custom_pack")
async def custom_pack(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🔢 Введи количество аккаунтов (1–100):")
    await state.set_state(BuyCustomState.waiting_for_quantity)
    await callback_query.answer()


@dp.message(BuyCustomState.waiting_for_quantity)
async def process_custom_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty < 1 or qty > 100:
            await message.answer("⚠ Укажи число от 1 до 100.")
            return

        if qty <= 20:
            price_per = 10
        elif qty <= 50:
            price_per = 9
        else:
            price_per = 8

        total = qty * price_per
        await send_pay_screen(message, qty, total)
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи число, например 25")


async def send_pay_screen(msg, quantity: int, total: int):
    deal_id = f"#{random.randint(8000, 12000)}"
    caption = (
        "🧾 <b>Шаг 2 из 3 — оплата товара</b>\n\n"
        f"✅ Товар: Stripe Accounts\n"
        f"✅ Количество: {quantity} шт\n"
        f"✅ Сумма: {total}$\n"
        f"✅ Номер сделки: {deal_id}\n\n"
        "🟡 Выбери способ оплаты ниже 👇"
    )
    photo = FSInputFile("pay.jpg")
    await msg.answer_photo(photo=photo, caption=caption, reply_markup=pay_menu())


# ========== ПОДДЕРЖКА ==========
@dp.callback_query(F.data == "support")
async def support(callback_query: CallbackQuery):
    await callback_query.message.answer("💬 Поддержка и помощь:", reply_markup=support_menu())
    await callback_query.answer()


# ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
@dp.callback_query(F.data == "balance")
async def balance(callback_query: CallbackQuery):
    await callback_query.message.answer("💵 Выбери способ пополнения:", reply_markup=balance_menu())
    await callback_query.answer()


# --- CryptoBot пополнение ---
@dp.callback_query(F.data == "crypto_bot")
async def crypto_bot_topup(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("💵 Введи сумму пополнения в $ (например 10):")
    await state.set_state(TopUpState.waiting_for_amount)
    await callback_query.answer()


@dp.message(TopUpState.waiting_for_amount)
async def create_crypto_invoice(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        async with aiohttp.ClientSession() as session:
            headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_API}
            payload = {
                "asset": "USDT",
                "amount": amount,
                "description": f"Пополнение баланса на {amount}$ через CryptoBot",
            }
            async with session.post("https://pay.crypt.bot/api/createInvoice", headers=headers, data=payload) as resp:
                result = await resp.json()

        if result.get("ok"):
            invoice_url = result["result"]["pay_url"]
            await message.answer(
                f"✅ Счёт создан!\n\nСумма: <b>{amount}$</b>\nВалюта: <b>USDT</b>\n\n"
                f"👉 <a href='{invoice_url}'>Оплатить через CryptoBot</a>",
                disable_web_page_preview=True
            )
        else:
            await message.answer("❌ Ошибка при создании счёта. Проверь API-токен.")
        await state.clear()

    except ValueError:
        await message.answer("❌ Введи число, например 10")


# --- Пополнение через криптовалюты (ручное) ---
@dp.callback_query(F.data == "manual_crypto")
async def manual_crypto_start(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("💵 Введи сумму пополнения в $ (например 15):")
    await state.set_state(TopUpState.waiting_for_crypto_amount)
    await callback_query.answer()


@dp.message(TopUpState.waiting_for_crypto_amount)
async def manual_crypto_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        await state.update_data(amount=amount)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="USDT", callback_data="cur_USDT"),
             InlineKeyboardButton(text="BTC", callback_data="cur_BTC"),
             InlineKeyboardButton(text="ETH", callback_data="cur_ETH")],
            [InlineKeyboardButton(text="TON", callback_data="cur_TON"),
             InlineKeyboardButton(text="BNB", callback_data="cur_BNB"),
             InlineKeyboardButton(text="TRX", callback_data="cur_TRX")],
            [InlineKeyboardButton(text="SOL", callback_data="cur_SOL")],
        ])
        await message.answer("💰 Выбери криптовалюту:", reply_markup=kb)
        await state.set_state(TopUpState.waiting_for_crypto_choice)
    except ValueError:
        await message.answer("❌ Введи число, например 12")


@dp.callback_query(F.data.startswith("cur_"))
async def manual_crypto(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_usd = data.get("amount")

    if not amount_usd:
        await callback_query.message.answer("⚠ Сначала введи сумму в долларах.")
        await state.set_state(TopUpState.waiting_for_crypto_amount)
        await callback_query.answer()
        return

    currency = callback_query.data.split("_")[1]
    wallet = wallets.get(currency, "—")

    # карта id для CoinGecko
    crypto_id_map = {
        "USDT": "tether",
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "TRX": "tron",
        "BNB": "binancecoin",
        "TON": "the-open-network",
        "SOL": "solana",
    }

    # по умолчанию 1 (для USDT)
    rate = 1
    if currency != "USDT":
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id_map[currency]}&vs_currencies=usd"
                async with session.get(url) as resp:
                    j = await resp.json()
                    rate = j[crypto_id_map[currency]]["usd"]
        except Exception:
            rate = 1

    if not rate:
        rate = 1

    amount_crypto = round(float(amount_usd) / rate, 6)
    # добавляем копейки, чтобы платеж был уникальным
    cents = round(random.uniform(0.000001, 0.000009), 6)
    total_crypto = amount_crypto + cents

    deal_id = f"#{random.randint(8000, 12000)}"

    text = (
        f"✅ <b>Номер сделки:</b> <code>{deal_id}</code>\n"
        f"💵 Сумма в USD: <b>{amount_usd}$</b>\n"
        f"💰 К оплате: <b>{total_crypto} {currency}</b>\n"
        f"🏦 Кошелёк:\n<code>{wallet}</code>\n\n"
        "⏱ Оплата действует 30 минут.\n"
        "После перевода нажми кнопку ниже 👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{deal_id}")]
    ])
    msg = await callback_query.message.answer(text, reply_markup=kb)

    # ставим таймер на отмену
    asyncio.create_task(cancel_order_later(msg, deal_id))

    await state.clear()
    await callback_query.answer()


# ========== КНОПКА "ОПЛАТИТЬ С БАЛАНСА" ==========
@dp.callback_query(F.data == "pay_balance")
async def pay_balance(callback_query: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="balance")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back")],
    ])
    await callback_query.message.answer(
        "❌ <b>Недостаточно средств на балансе!</b>\n\n"
        "Пополните баланс и попробуйте снова.",
        reply_markup=kb
    )
    await callback_query.answer()


# ========== ТАЙМЕР ОТМЕНЫ ==========
async def cancel_order_later(message: Message, deal_id: str):
    await asyncio.sleep(1800)  # 30 минут
    try:
        await message.edit_text(f"⛔ Сделка {deal_id} отменена — время ожидания истекло.")
    except Exception:
        pass


# ========== /admin ==========
@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("🚫 У тебя нет прав администратора.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="USDT", callback_data="adm_USDT"),
         InlineKeyboardButton(text="BTC", callback_data="adm_BTC"),
         InlineKeyboardButton(text="ETH", callback_data="adm_ETH")],
        [InlineKeyboardButton(text="TON", callback_data="adm_TON"),
         InlineKeyboardButton(text="BNB", callback_data="adm_BNB"),
         InlineKeyboardButton(text="TRX", callback_data="adm_TRX")],
        [InlineKeyboardButton(text="SOL", callback_data="adm_SOL")],
    ])
    await message.answer("🛠 Выбери валюту для изменения кошелька:", reply_markup=kb)


@dp.callback_query(F.data.startswith("adm_"))
async def admin_choose_currency(callback_query: CallbackQuery, state: FSMContext):
    cur = callback_query.data.split("_")[1]
    await state.set_state(AdminState.waiting_for_wallet)
    await state.update_data(currency=cur)
    await callback_query.message.answer(f"💼 Введи новый кошелёк для <b>{cur}</b>:")
    await callback_query.answer()


@dp.message(AdminState.waiting_for_wallet)
async def admin_set_wallet(message: Message, state: FSMContext):
    data = await state.get_data()
    cur = data.get("currency")
    wallets[cur] = message.text.strip()
    await message.answer(f"✅ Кошелёк для {cur} обновлён!")
    await state.clear()


# ========== ЗАПУСК ==========
async def main():
    print("✅ Бот запущен…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
