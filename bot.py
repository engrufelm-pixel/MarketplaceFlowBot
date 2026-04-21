import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()
from config import BOT_TOKEN, ADMIN_CHAT_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class OrderFlow(StatesGroup):
    waiting_phone = State()
    choose_marketplace = State()
    ozon_order_number = State()
    wb_order_info = State()
    other_question = State()
    waiting_data = State()


def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def marketplace_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟣 Wildberries"), KeyboardButton(text="🔵 Ozon")],
            [KeyboardButton(text="❓ У меня другой вопрос")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def done_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Готово — отправить менеджеру")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Здравствуйте!\n\n"
        "Здесь вы можете передать информацию по своему заказу "
        "или связаться с менеджером.\n\n"
        "Для начала, пожалуйста, поделитесь своим номером телефона.",
        reply_markup=phone_kb()
    )
    await state.set_state(OrderFlow.waiting_phone)


@dp.message(OrderFlow.waiting_phone, F.contact)
async def got_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await message.answer(
        f"📞 Спасибо! Номер {phone} сохранён.\n\n"
        "Теперь выберите маркетплейс, где был оформлен заказ:",
        reply_markup=marketplace_kb()
    )
    await state.set_state(OrderFlow.choose_marketplace)


@dp.message(OrderFlow.waiting_phone, F.text)
async def got_phone_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    digits = "".join(c for c in text if c.isdigit())
    if len(digits) < 10:
        return await message.answer(
            "Пожалуйста, нажмите кнопку «📱 Поделиться номером» "
            "или введите номер вручную (не менее 10 цифр).",
            reply_markup=phone_kb()
        )
    await state.update_data(phone=text)
    await message.answer(
        f"📞 Спасибо! Номер {text} сохранён.\n\n"
        "Теперь выберите маркетплейс, где был оформлен заказ:",
        reply_markup=marketplace_kb()
    )
    await state.set_state(OrderFlow.choose_marketplace)


@dp.message(OrderFlow.choose_marketplace, F.text == "🔵 Ozon")
async def choose_ozon(message: types.Message, state: FSMContext):
    await state.update_data(marketplace="Ozon")
    await message.answer(
        "📦 Вы выбрали Ozon.\n\n"
        "Пожалуйста, укажите номер заказа:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderFlow.ozon_order_number)


@dp.message(OrderFlow.choose_marketplace, F.text == "🟣 Wildberries")
async def choose_wb(message: types.Message, state: FSMContext):
    await state.update_data(marketplace="Wildberries")
    await message.answer(
        "📦 Вы выбрали Wildberries.\n\n"
        "Пожалуйста, укажите номер сборочного задания, если знаете.\n\n"
        "Если не знаете номер — напишите время оформления заказа и город.\n\n"
        "Например: 10:43, Казань",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderFlow.wb_order_info)


@dp.message(OrderFlow.choose_marketplace, F.text == "❓ У меня другой вопрос")
async def choose_other(message: types.Message, state: FSMContext):
    await state.update_data(marketplace="Другой вопрос")
    await message.answer(
        "📝 Пожалуйста, опишите как можно подробнее, с чем связан ваш вопрос.\n\n"
        "Можно отправить текст, фото или файл — всё передадим менеджеру.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderFlow.other_question)


@dp.message(OrderFlow.choose_marketplace)
async def choose_unknown(message: types.Message):
    await message.answer(
        "Пожалуйста, выберите вариант кнопкой ниже.",
        reply_markup=marketplace_kb()
    )


@dp.message(OrderFlow.ozon_order_number, F.text)
async def ozon_got_order(message: types.Message, state: FSMContext):
    await state.update_data(order_info=message.text.strip(), files=[])
    await message.answer(
        "✅ Номер заказа принят.\n\n"
        "Теперь приложите данные для нанесения или другую информацию.\n\n"
        "Можно отправить фото, скриншоты, файлы или текст.\n\n"
        "Когда всё отправите — нажмите кнопку ниже.",
        reply_markup=done_kb()
    )
    await state.set_state(OrderFlow.waiting_data)


@dp.message(OrderFlow.wb_order_info, F.text)
async def wb_got_order_text(message: types.Message, state: FSMContext):
    await state.update_data(order_info=message.text.strip(), files=[])
    await message.answer(
        "✅ Информация по заказу принята.\n\n"
        "Теперь приложите данные для нанесения или другую информацию.\n\n"
        "Можно отправить фото, скриншоты, файлы или текст.\n\n"
        "Когда всё отправите — нажмите кнопку ниже.",
        reply_markup=done_kb()
    )
    await state.set_state(OrderFlow.waiting_data)


@dp.message(OrderFlow.wb_order_info, F.photo)
async def wb_got_order_photo(message: types.Message, state: FSMContext):
    files = [{
        "type": "photo",
        "file_id": message.photo[-1].file_id,
        "caption": message.caption or "Скриншот заказа WB"
    }]
    await state.update_data(
        order_info="Скриншот с данными заказа",
        files=files
    )
    await message.answer(
        "✅ Скриншот заказа принят.\n\n"
        "Теперь приложите данные для нанесения или другую информацию.\n\n"
        "Когда всё отправите — нажмите кнопку ниже.",
        reply_markup=done_kb()
    )
    await state.set_state(OrderFlow.waiting_data)


@dp.message(OrderFlow.other_question, F.text)
async def other_got_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone", "не указан")
    user = message.from_user
    full_name = user.full_name or "Без имени"
    username_display = f"@{user.username}" if user.username else f"ID: {user.id}"

    await bot.send_message(
        ADMIN_CHAT_ID,
        "❓ НОВЫЙ ВОПРОС\n\n"
        f"👤 Клиент: {full_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"💬 Никнейм: {username_display}\n"
        f"📱 Телефон: {phone}\n\n"
        f"📝 Вопрос:\n{message.text}"
    )
    await state.clear()
    await message.answer(
        "✅ Ваш вопрос отправлен менеджеру.\n\n"
        "Мы ответим вам в этом чате.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderFlow.other_question, F.photo)
async def other_got_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone", "не указан")
    user = message.from_user
    full_name = user.full_name or "Без имени"
    username_display = f"@{user.username}" if user.username else f"ID: {user.id}"

    await bot.send_photo(
        ADMIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=(
            "❓ НОВЫЙ ВОПРОС\n\n"
            f"👤 Клиент: {full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"💬 Никнейм: {username_display}\n"
            f"📱 Телефон: {phone}\n\n"
            f"📝 Комментарий:\n{message.caption or 'Фото без подписи'}"
        )
    )
    await state.clear()
    await message.answer(
        "✅ Ваш вопрос отправлен менеджеру.\n\n"
        "Мы ответим вам в этом чате.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderFlow.other_question, F.document)
async def other_got_document(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone", "не указан")
    user = message.from_user
    full_name = user.full_name or "Без имени"
    username_display = f"@{user.username}" if user.username else f"ID: {user.id}"

    await bot.send_document(
        ADMIN_CHAT_ID,
        document=message.document.file_id,
        caption=(
            "❓ НОВЫЙ ВОПРОС\n\n"
            f"👤 Клиент: {full_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"💬 Никнейм: {username_display}\n"
            f"📱 Телефон: {phone}\n\n"
            f"📝 Файл: {message.document.file_name or 'без имени'}"
        )
    )
    await state.clear()
    await message.answer(
        "✅ Ваш вопрос отправлен менеджеру.\n\n"
        "Мы ответим вам в этом чате.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderFlow.waiting_data, F.text == "✅ Готово — отправить менеджеру")
async def send_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    full_name = user.full_name or "Без имени"
    username_display = f"@{user.username}" if user.username else f"ID: {user.id}"
    phone = data.get("phone", "не указан")
    marketplace = data.get("marketplace", "—")
    order_info = data.get("order_info", "—")
    files = data.get("files", [])

    await bot.send_message(
        ADMIN_CHAT_ID,
        "📦 НОВЫЙ ЗАКАЗ\n\n"
        f"👤 Клиент: {full_name}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"💬 Никнейм: {username_display}\n"
        f"📱 Телефон: {phone}\n"
        f"🏪 Маркетплейс: {marketplace}\n"
        f"🔢 Заказ / сборочное: {order_info}\n"
        f"📎 Вложений: {len(files)}"
    )

    for item in files:
        if item["type"] == "photo":
            await bot.send_photo(
                ADMIN_CHAT_ID,
                photo=item["file_id"],
                caption=f"Фото от {full_name}\n{item.get('caption', '')}"
            )
        elif item["type"] == "document":
            await bot.send_document(
                ADMIN_CHAT_ID,
                document=item["file_id"],
                caption=f"Файл от {full_name}\n{item.get('caption', '')}"
            )
        elif item["type"] == "text":
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"Текст от {full_name}:\n\n{item['content']}"
            )

    await state.clear()
    await message.answer(
        "✅ Спасибо! Данные отправлены менеджеру.\n\n"
        "Если понадобится, мы свяжемся с вами в этом чате.",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(OrderFlow.waiting_data, F.photo)
async def data_got_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    files.append({
        "type": "photo",
        "file_id": message.photo[-1].file_id,
        "caption": message.caption or ""
    })
    await state.update_data(files=files)
    await message.answer(
        f"📸 Фото получено. Вложений: {len(files)}\n\n"
        "Можете отправить ещё или нажмите «✅ Готово — отправить менеджеру».",
        reply_markup=done_kb()
    )


@dp.message(OrderFlow.waiting_data, F.document)
async def data_got_document(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    files.append({
        "type": "document",
        "file_id": message.document.file_id,
        "caption": message.caption or message.document.file_name or ""
    })
    await state.update_data(files=files)
    await message.answer(
        f"📎 Файл получен. Вложений: {len(files)}\n\n"
        "Можете отправить ещё или нажмите «✅ Готово — отправить менеджеру».",
        reply_markup=done_kb()
    )


@dp.message(OrderFlow.waiting_data, F.text)
async def data_got_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    files.append({
        "type": "text",
        "content": message.text
    })
    await state.update_data(files=files)
    await message.answer(
        f"📝 Текст получен. Вложений: {len(files)}\n\n"
        "Можете отправить ещё или нажмите «✅ Готово — отправить менеджеру».",
        reply_markup=done_kb()
    )


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())