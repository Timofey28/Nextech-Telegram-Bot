from data import TOKEN, db_dbname, db_host, db_user, db_password
from database import Database
import os
from typing import Optional, Tuple
from telegram import (
    Chat,
    ChatMember,
    ChatMemberUpdated,
    Update,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ChatMemberHandler,
    CallbackQueryHandler,
)
import logging
import pandas as pd


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.message.chat.type
    msg = update.message.text

    if chat_type == 'private':
        try:
            await context.bot.send_message(ADMIN_GROUP_ID, f'Мне тут {update.effective_user.full_name} что-то написал, не умею читать (')
            await context.bot.forward_message(ADMIN_GROUP_ID, update.effective_user.id, update.message.id)
        except:
            logging.error('не получилось переслать сообщение от клиента, так как ADMIN_GROUP_ID == 0; возможно, отсутствует файл "admin_group_id.txt"')
    elif chat_type == 'group':
        if DB_ADMIN_STATUS == Status_ENTERING_BUSINESS_DIRECTION:
            if db.business_direction_exists(msg):
                await context.bot.send_message(ADMIN_GROUP_ID, 'Такое направление уже существует. Придумай что-нибудь другое или нажми "отмена"')
            else:
                if msg.lower() == "отмена":
                    await context.bot.send_message(ADMIN_GROUP_ID, 'Отмена так отмена', reply_markup=ReplyKeyboardRemove())
                else:
                    db.add_business_direction(msg)
                    await context.bot.send_message(ADMIN_GROUP_ID, 'Добавил 👌', reply_markup=ReplyKeyboardRemove())
                set_group_status(Status_MAIN)

        elif DB_ADMIN_STATUS == Status_ENTERING_CLIENTS_DATA:
            if msg.lower() == "отмена":
                await context.bot.send_message(ADMIN_GROUP_ID, "Да пожалуйста", reply_markup=ReplyKeyboardRemove())
                set_group_status(Status_MAIN)
                return
            lines_entered = list(map(lambda x: x.strip(), msg.split('\n')))
            lines_entered = list(filter(lambda x: x != '', lines_entered))
            if len(lines_entered) != 8:
                ending = 'а' if len(lines_entered) == 1 else 'о'
                await context.bot.send_message(ADMIN_GROUP_ID, f'Неверный формат данных. Ожидалось 8 строк, был{ending} получен{ending}: {len(lines_entered)}. Так что даже проверять не буду что там 🙄')
                await context.bot.send_message(ADMIN_GROUP_ID, f'Повторяю для тупых. Надо ввести данные клиента в следующем формате:\n\n{EXPECTED_CLIENTS_DATA_FORMAT}\n\nЛибо нажать кнопку "отмена" под стандартной клавиатурой')
                return
            surname, name, patronymic, sex, tg_id, inn, phone_number, email = lines_entered
            if sex[0].lower() == 'м':
                sex = 'male'
            elif sex[0].lower() == 'ж':
                sex = 'female'
            else:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Неверный формат данных. У пола может быть только 2 значения: "м" и "ж". Жду корректного ввода или нажатия кнопки "отмена"')
                return
            if not tg_id.isdigit():
                if tg_id[0] == '-' and tg_id[1:].isdigit():
                    await context.bot.send_message(ADMIN_GROUP_ID, f'Неверный формат данных. У пользователя не может быть отрицательный id. Повтори попытку')
                else:
                    await context.bot.send_message(ADMIN_GROUP_ID, f'Неверный формат данных. id пользователя должен состоять только из цифр. Повтори попытку')
                return
            if len(tg_id) > 18:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Если у пользователя в телеге реально может быть такой длинный id, передай моему разрабу, что он долбоеб. Но скорей всего такого не может быть, так что уточни id клиента с помощью какого-нибудь бота типа @get_any_telegram_id_bot и повтори попытку)')
                return
            tg_id = int(tg_id)
            if len(inn) > 15:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Длина ИНН не может быть больше 15. Повтори попытку')
                return
            for char in phone_number:
                if not char.isdigit():
                    phone_number = phone_number.replace(char, '')
            if phone_number == '':
                await context.bot.send_message(ADMIN_GROUP_ID, f'Номер телефона должен состоять из цифр, если ты не знал. Повтори попытку')
                return
            if len(phone_number) > 11:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Номер телефона должен не может быть длиннее 11 цифр. Повтори попытку')
                return
            if phone_number[0] == '7':
                phone_number = '8' + phone_number[1:]
            business_direction_id = db.get_business_direction_id(CALLBACK_DATA['chosen_direction'])
            surname = surname.capitalize()
            name = name.capitalize()
            patronymic = patronymic.capitalize()
            inn = inn.strip()
            email = email.lower()
            assert len(surname) <= 30 and len(name) <= 30 and len(patronymic) <= 30 and len(email) <= 50
            if db.add_client(surname, name, patronymic, sex, tg_id, inn, business_direction_id, phone_number, email):
                await context.bot.send_message(ADMIN_GROUP_ID, f'Добавил клиента в базу {"🧑" if sex == "male" else "👩"}', reply_markup=ReplyKeyboardRemove())
                set_group_status(Status_MAIN)
                try:
                    await context.bot.send_message(tg_id, "Привет, друг! У меня хорошие новости: тебя только что добавили в базу и ты будешь получать обещанную рассылку!")
                except:
                    pass
            else:
                reply_msg = f'❌ Не получилось добавить. В базе уже существует клиент либо с таким же id, либо с таким же ИНН, либо с таким же номером телефона, либо с такой же почтой'
                await context.bot.send_message(ADMIN_GROUP_ID, reply_msg, reply_markup=ReplyKeyboardRemove())

    else:
        logging.warning(f'сообщение в чате непредвиденного типа: {chat_type}')

    print(f'User ({update.message.chat.id}) in {chat_type}: "{msg}"')


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CALLBACK_DATA
    assert len(CALLBACK_DATA) != 0
    query = update.callback_query

    if DB_ADMIN_STATUS == Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Как скажешь")
        else:
            chosen_direction = CALLBACK_DATA[query.data]
            result = db.delete_business_direction(chosen_direction)
            if result is True:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Удалил направление "{chosen_direction}" 👍')
            else:
                await context.bot.send_message(ADMIN_GROUP_ID, f'Не могу удалить направление бизнеса "{chosen_direction}", так как в нем находится как минимум один человек 😐')
        set_group_status(Status_MAIN)

    elif DB_ADMIN_STATUS == Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Да легко")
            set_group_status(Status_MAIN)
        else:
            set_group_status(Status_ENTERING_CLIENTS_DATA)
            CALLBACK_DATA['chosen_direction'] = CALLBACK_DATA[query.data]
            reply_msg = f'Было выбрано направление "{CALLBACK_DATA[query.data]}". Введи данные нового клиента в следующем формате (или нажми кнопку "отмена"):\n\n{EXPECTED_CLIENTS_DATA_FORMAT}'
            await context.bot.send_message(ADMIN_GROUP_ID, reply_msg, reply_markup=ReplyKeyboardMarkup(CANCEL_BUTTON))

    elif DB_ADMIN_STATUS == Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE:
        if query.data == "отмена":
            os.remove(CURRENT_FILE)
            await context.bot.send_message(ADMIN_GROUP_ID, "Ок")
            set_group_status(Status_MAIN)
        else:
            set_group_status(Status_PRESSING_CLIENT_TO_SEND_FILE)
            buttons = []
            clients = db.get_clients_from_business_direction(CALLBACK_DATA[query.data])
            CALLBACK_DATA.clear()
            for i in range(len(clients)):
                name, surname, tg_id, phone_number = clients[i]
                buttons.append([InlineKeyboardButton(f'{name} {surname}, {prettify_phone_number(phone_number)}', callback_data=f'{tg_id}')])
                CALLBACK_DATA[f'{tg_id}'] = f'{name} {surname}'
            buttons.append([InlineKeyboardButton("Никому, забей", callback_data="отмена")])
            await context.bot.send_message(ADMIN_GROUP_ID, 'Кому из них отправить?', reply_markup=InlineKeyboardMarkup(buttons))

    elif DB_ADMIN_STATUS == Status_PRESSING_CLIENT_TO_SEND_FILE:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Ну ок")
        else:
            assert CURRENT_FILE != ''
            try:
                sent_message = await context.bot.send_document(query.data, CURRENT_FILE)
                db.write_sent_message_info(int(query.data), sent_message.message_id)
                await context.bot.send_message(ADMIN_GROUP_ID, f'Скинул файл клиенту по имени {CALLBACK_DATA[query.data]} ✅')
            except:
                await context.bot.send_message(ADMIN_GROUP_ID, f'❌ Не удалось скинуть файл человеку по имени {CALLBACK_DATA[query.data]}')
        os.remove(CURRENT_FILE)
        set_group_status(Status_MAIN)

    elif DB_ADMIN_STATUS == Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Ладно, как скажешь 😉")
            set_group_status(Status_MAIN)
        else:
            set_group_status(Status_PRESSING_CLIENT_TO_DELETE_ONE)
            buttons = []
            clients = db.get_clients_from_business_direction(CALLBACK_DATA[query.data])
            CALLBACK_DATA.clear()
            for i in range(len(clients)):
                name, surname, tg_id, phone_number = clients[i]
                buttons.append([InlineKeyboardButton(f'{name} {surname}, {prettify_phone_number(phone_number)}', callback_data=f'{tg_id}')])
                CALLBACK_DATA[f'{tg_id}'] = f'{name} {surname}'
            buttons.append([InlineKeyboardButton("Никого не надо, забей", callback_data="отмена")])
            await context.bot.send_message(ADMIN_GROUP_ID, 'Кого из них удалить из базы?', reply_markup=InlineKeyboardMarkup(buttons))

    elif DB_ADMIN_STATUS == Status_PRESSING_CLIENT_TO_DELETE_ONE:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Хорошо 😉")
        else:
            db.delete_client(int(query.data))
            await context.bot.send_message(ADMIN_GROUP_ID, f'Удалил клиента по имени {CALLBACK_DATA[query.data]} ✅')
        set_group_status(Status_MAIN)

    elif DB_ADMIN_STATUS == Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE:
        if query.data == "отмена":
            await context.bot.send_message(ADMIN_GROUP_ID, "Не надо так не надо 😉")
        else:
            client_full_name = CALLBACK_DATA[query.data]
            chat_id, message_id = list(map(int, query.data.split(',')))
            try:
                await context.bot.delete_message(chat_id, message_id)
                db.delete_sent_message_info(chat_id, message_id)
                await context.bot.send_message(ADMIN_GROUP_ID, f'Удалил последнее сообщение клиенту по имени {client_full_name} ✅')
            except:
                await context.bot.send_message(ADMIN_GROUP_ID, f'❌ Не удалось удалить последнее сообщение клиенту по имени {client_full_name}')
        set_group_status(Status_MAIN)


def prettify_phone_number(phone_number: str) -> str:
    assert len(phone_number) >= 9
    phone_number = phone_number[:1] + ' (' + phone_number[1:4] + ') ' + phone_number[4:7] + '-' + phone_number[7:9] + '-' + phone_number[9:]
    return phone_number


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    business_directions = db.get_business_directions('non-empty')
    if business_directions is None:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Некому слать файл, в базе пока что никого нет')
        return
    global CURRENT_FILE
    file_id = update.message.document.file_id
    CURRENT_FILE = f'File/{update.message.document.file_name}'
    tgFileInstance = await context.bot.get_file(file_id)
    await tgFileInstance.download_to_drive(CURRENT_FILE)

    set_group_status(Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE)
    global CALLBACK_DATA
    CALLBACK_DATA.clear()
    buttons = []
    for i in range(len(business_directions)):
        buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
        CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
    buttons.append([InlineKeyboardButton("Никому, забей", callback_data="отмена")])
    await context.bot.send_message(ADMIN_GROUP_ID, 'Кому отправить этот файл? Выбери направление бизнеса', reply_markup=InlineKeyboardMarkup(buttons))


async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':  # если написал простой смертный
        tg_id = update.effective_chat.id
        if db.client_exists(tg_id):
            await update.message.reply_text('Приветствую! Твоя подписка подтверждена)')
            client_info = db.get_clients_data(update.effective_user.id)
            if client_info:
                surname, name, patronymic, sex, tg_id, inn, bd_name, phone_number, email = client_info
                msg = f'Хорошие новости! Наш клиент, {name} {surname} [{prettify_phone_number(phone_number)}], только что написал мне и теперь мы можем отправлять ему файлы 😃'
                await context.bot.send_message(ADMIN_GROUP_ID, msg)
        else:
            await update.message.reply_text('Приветствую! Если ты оформил подписку, то тебя пока не добавили в базу. Как только добавят, я сразу сообщу!')


async def command_add_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    business_directions = db.get_business_directions('all')
    if business_directions is None:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Нельзя добавить человека когда нет направлений бизнеса')
        return
    set_group_status(Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT)
    global CALLBACK_DATA
    CALLBACK_DATA.clear()
    buttons = []
    for i in range(len(business_directions)):
        buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
        CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
    buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
    await context.bot.send_message(ADMIN_GROUP_ID, 'Выбери направление бизнеса, в которое нужно добавить клиента или нажми "отмена"',
                                   reply_markup=InlineKeyboardMarkup(buttons))


async def command_delete_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    if not db.clients_exist():
        await context.bot.send_message(ADMIN_GROUP_ID, "Пока нет ни одного клиента")
        return
    business_directions = db.get_business_directions('non-empty')
    assert len(business_directions) <= 100
    set_group_status(Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT)
    global CALLBACK_DATA
    CALLBACK_DATA.clear()
    buttons = []
    for i in range(len(business_directions)):
        buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
        CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
    buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
    await context.bot.send_message(ADMIN_GROUP_ID, 'Выбери направление бизнеса, в котором находится клиент, которого нужно удалить или нажми "отмена"',
                                   reply_markup=InlineKeyboardMarkup(buttons))


async def command_get_clients_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    clients_data = db.get_clients_data()
    if clients_data is None:
        await context.bot.send_message(ADMIN_GROUP_ID, "Пока нет ни одного клиента")
        return
    df = pd.DataFrame(clients_data, columns=['Фамилия', 'Имя', 'Отчество', 'Пол', 'Телеграм id', 'ИНН', 'Направление бизнеса', 'Номер телефона', 'Почта'])
    file_path = f'File/clients_data.xlsx'
    df.to_excel(file_path, sheet_name='Клиенты', index=False)
    await context.bot.send_document(ADMIN_GROUP_ID, file_path)
    os.remove(file_path)


async def command_add_business_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    set_group_status(Status_ENTERING_BUSINESS_DIRECTION)
    await context.bot.send_message(ADMIN_GROUP_ID, 'Введите название нового направления бизнеса. Чтобы вернуться назад нажми кнопку "отмена" на клавиатуре',
                                   reply_markup=ReplyKeyboardMarkup(CANCEL_BUTTON))


async def command_delete_business_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    business_directions = db.get_business_directions('all')
    if business_directions is None:
        await context.bot.send_message(ADMIN_GROUP_ID, "Пока нет ни одного направления бизнеса")
        return
    assert len(business_directions) <= 100
    set_group_status(Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE)
    global CALLBACK_DATA
    CALLBACK_DATA.clear()
    buttons = []
    for i in range(len(business_directions)):
        buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
        CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
    buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
    await context.bot.send_message(ADMIN_GROUP_ID, 'Выбери направление бизнеса, которое нужно удалить или нажми "отмена"',
                                   reply_markup=InlineKeyboardMarkup(buttons))


async def command_show_business_directions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    business_directions = db.get_business_directions('all')
    if business_directions is None:
        await context.bot.send_message(ADMIN_GROUP_ID, "Пока нет ни одного направления бизнеса")
        return
    reply_msg = 'Текущие направления бизнеса:\n'
    for i in range(len(business_directions)):
        reply_msg += f"\n{i + 1}) {business_directions[i]}"
    await context.bot.send_message(ADMIN_GROUP_ID, reply_msg)


async def command_delete_sent_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        return
    if DB_ADMIN_STATUS != Status_MAIN:
        await context.bot.send_message(ADMIN_GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
        return

    last_sent_messages = db.get_last_sent_messages()
    if last_sent_messages is None:
        await context.bot.send_message(ADMIN_GROUP_ID, 'За последние 2 суток мы не отправляли сообщений клиентам. Сообщения, отправленные еще раньше уже невозможно удалить')
        return
    set_group_status(Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE)
    global CALLBACK_DATA
    CALLBACK_DATA.clear()
    buttons = []
    for i in range(len(last_sent_messages)):
        tg_id, message_id, name, surname, phone_number = last_sent_messages[i]
        buttons.append([InlineKeyboardButton(f'{name} {surname}, {prettify_phone_number(phone_number)}', callback_data=f'{tg_id},{message_id}')])
        CALLBACK_DATA[f'{tg_id},{message_id}'] = f'{name} {surname}'
    buttons.append([InlineKeyboardButton("Ни у кого не надо", callback_data="отмена")])
    await context.bot.send_message(ADMIN_GROUP_ID, 'У кого из них удалить последнее сообщение?', reply_markup=InlineKeyboardMarkup(buttons))


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(context.error)


def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global ADMIN_GROUP_ID
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    cause = update.effective_user
    chat = update.effective_chat
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logging.info(f"{cause.full_name} ({cause.id}) added the bot to the group \"{chat.title}\"")
            set_group_status(Status_MAIN)
            ADMIN_GROUP_ID = chat.id
            with open("admin_group_id.txt", "w") as f:
                f.write(str(ADMIN_GROUP_ID))
            await context.bot.set_my_commands(commands=bot_commands_group, scope=BotCommandScopeAllGroupChats())
            await context.bot.set_my_commands(commands=bot_commands_chats, scope=BotCommandScopeAllPrivateChats())
        elif was_member and not is_member:
            logging.info(f"{cause.full_name} ({cause.id}) removed the bot from the group \"{chat.title}\"")
            await context.bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())


def run_bot():
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', command_start))
    app.add_handler(CommandHandler('add_client', command_add_client))
    app.add_handler(CommandHandler('delete_client', command_delete_client))
    app.add_handler(CommandHandler('get_clients_data', command_get_clients_data))
    app.add_handler(CommandHandler('add_business_direction', command_add_business_direction))
    app.add_handler(CommandHandler('delete_business_direction', command_delete_business_direction))
    app.add_handler(CommandHandler('show_business_directions', command_show_business_directions))
    app.add_handler(CommandHandler('delete_sent_message', command_delete_sent_message))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Files
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_file))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Adding to group
    app.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))

    # Errors
    app.add_error_handler(error)

    # Pools the bot
    print('Polling...')
    app.run_polling(poll_interval=1)


def set_group_status(status: str):
    global DB_ADMIN_STATUS
    assert status == Status_MAIN or \
           status == Status_ENTERING_BUSINESS_DIRECTION or \
           status == Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE or \
           status == Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT or \
           status == Status_ENTERING_CLIENTS_DATA or \
           status == Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE or \
           status == Status_PRESSING_CLIENT_TO_SEND_FILE or \
           status == Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT or \
           status == Status_PRESSING_CLIENT_TO_DELETE_ONE or \
           status == Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE
    DB_ADMIN_STATUS = status


if __name__ == '__main__':
    # Настройка логов
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename='info.log',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Создание папки File для хранения отсылаемых файлов
    if not os.path.exists("File"):
        os.mkdir("File")
    else:
        for file_name in os.listdir("File"):
            os.remove(f"File/{file_name}")

    # Инициализация объекта базы данных
    db = Database(db_dbname=db_dbname,
                  db_host=db_host,
                  db_user=db_user,
                  db_password=db_password)
    # Статусы
    Status_MAIN = 'main'
    Status_ENTERING_BUSINESS_DIRECTION = 'entering_business_direction'
    Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE = 'pressing_business_direction'
    Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT = 'pressing_business_direction_to_add_new_client'
    Status_ENTERING_CLIENTS_DATA = 'entering_clients_data'
    Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE = 'pressing_business_direction_to_send_file'
    Status_PRESSING_CLIENT_TO_SEND_FILE = 'pressing_client_to_send_file'
    Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT = 'pressing_business_direction_to_delete_client'
    Status_PRESSING_CLIENT_TO_DELETE_ONE = 'pressing_client_to_delete_one'
    Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE = 'pressing_client_to_delete_last_message'

    # Глобальные переменные
    DB_ADMIN_STATUS = Status_MAIN
    ADMIN_GROUP_ID = 0
    if os.path.exists("admin_group_id.txt"):
        with open("admin_group_id.txt") as file:
            ADMIN_GROUP_ID = int(file.read())
    CALLBACK_DATA = {}
    CANCEL_BUTTON = [[KeyboardButton("отмена")]]
    EXPECTED_CLIENTS_DATA_FORMAT = '\n'.join([
        'Фамилия',
        'Имя',
        'Отчество',
        'пол (буква "м" или "ж")',
        'telegram id человека (именно циферки)',
        'ИНН',
        'номер телефона',
        'почта',
    ])
    CURRENT_FILE = ''

    bot_commands_group = [
        ('add_client', 'Добавить нового клиента в базу'),
        ('delete_client', 'Удалить клиента из базы'),
        ('get_clients_data', 'Получить клиентские данные'),
        ('add_business_direction', 'Добавить направление бизнеса'),
        ('delete_business_direction', 'Удалить направление бизнеса'),
        ('show_business_directions', 'Показать текущие направления бизнеса'),
        ('delete_sent_message', 'Удалить отправленное сообщение'),
    ]
    bot_commands_chats = [
        ('start', 'Начать монолог')
    ]
    run_bot()
