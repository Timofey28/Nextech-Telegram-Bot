import os
import pandas as pd
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes
from global_vars import GlobalVars
from database import Database


class Clients:
    def __init__(self, globalVars: GlobalVars, database: Database):
        self.gv = globalVars
        self.db = database
        self.EXPECTED_CLIENTS_DATA_FORMAT_TO_ADD = '\n'.join([
            'Фамилия',
            'Имя',
            'Отчество',
            'Пол (буква "м" или "ж")',
            'Telegram id (именно циферки)',
            'ИНН',
            'Номер телефона',
            'Почта',
        ])
        self.EXPECTED_CLIENTS_DATA_FORMAT_TO_EDIT = '\n'.join([
            'Фамилия',
            'Имя',
            'Отчество',
            'Пол',
            'ИНН',
            'Номер телефона',
            'Почта',
        ])

    async def add_business_direction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CLIENTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав на одну из кнопок')
            return

        self.gv.set_group_status('accountant', self.gv.Status_ENTERING_BUSINESS_DIRECTION)
        await context.bot.send_message(GROUP_ID, 'Введите название нового направления бизнеса. Чтобы вернуться назад нажми кнопку "отмена" на клавиатуре',
                                       reply_markup=ReplyKeyboardMarkup(self.gv.CANCEL_BUTTON))

    async def enter_business_direction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        msg = update.message.text
        if self.db.business_direction_exists(msg):
            await context.bot.send_message(GROUP_ID, 'Такое направление уже существует. Придумай что-нибудь другое или нажми "отмена"')
        else:
            if msg.lower() == "отмена":
                await context.bot.send_message(GROUP_ID, 'Отмена так отмена', reply_markup=ReplyKeyboardRemove())
            else:
                self.db.add_business_direction(msg)
                await context.bot.send_message(GROUP_ID, 'Добавил 👌', reply_markup=ReplyKeyboardRemove())
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CLIENTS)

    async def add_client(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CLIENTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions('all')
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, 'Нельзя добавить человека когда нет направлений бизнеса')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса, в которое нужно добавить клиента или нажми "отмена"',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def enter_client_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        msg = update.message.text
        if msg.lower() == "отмена":
            await context.bot.send_message(GROUP_ID, "Да пожалуйста", reply_markup=ReplyKeyboardRemove())
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CLIENTS)
            return
        lines_entered = list(map(lambda x: x.strip(), msg.split('\n')))
        lines_entered = list(filter(lambda x: x != '', lines_entered))
        if len(lines_entered) != 8:
            ending = 'а' if len(lines_entered) == 1 else 'о'
            await context.bot.send_message(GROUP_ID, f'Неверный формат данных. Ожидалось 8 строк, был{ending} получен{ending}: {len(lines_entered)}')
            await context.bot.send_message(GROUP_ID, f'Повторяю для тупых. Надо ввести данные клиента в следующем формате:\n\n{self.EXPECTED_CLIENTS_DATA_FORMAT_TO_ADD}\n\nЛибо нажать кнопку "отмена" под стандартной клавиатурой')
            return
        surname, name, patronymic, sex, tg_id, inn, phone_number, email = lines_entered
        if sex[0].lower() == 'м':
            sex = 'male'
        elif sex[0].lower() == 'ж':
            sex = 'female'
        else:
            await context.bot.send_message(GROUP_ID, f'Неверный формат данных. У пола может быть только 2 значения: "м" и "ж". Жду корректного ввода или нажатия кнопки "отмена"')
            return
        if not tg_id.isdigit():
            if tg_id[0] == '-' and tg_id[1:].isdigit():
                await context.bot.send_message(GROUP_ID, f'Неверный формат данных. У пользователя не может быть отрицательный id. Повтори попытку')
            else:
                await context.bot.send_message(GROUP_ID, f'Неверный формат данных. id пользователя должен состоять только из цифр. Повтори попытку')
            return
        if len(tg_id) > 18:
            await context.bot.send_message(GROUP_ID, f'Если у пользователя в телеге реально может быть такой длинный id, передай моему разрабу, что он долбоеб. Но скорей всего такого не может быть, так что уточни id клиента с помощью какого-нибудь бота типа @get_any_telegram_id_bot и повтори попытку)')
            return
        tg_id = int(tg_id)
        if len(inn) > 15:
            await context.bot.send_message(GROUP_ID, f'Длина ИНН не может быть больше 15. Повтори попытку')
            return
        for char in phone_number:
            if not char.isdigit():
                phone_number = phone_number.replace(char, '')
        if phone_number == '':
            await context.bot.send_message(GROUP_ID, f'Номер телефона должен состоять из цифр, если ты не знал. Повтори попытку')
            return
        if len(phone_number) > 11:
            await context.bot.send_message(GROUP_ID, f'Номер телефона должен не может быть длиннее 11 цифр. Повтори попытку')
            return
        if phone_number[0] == '7':
            phone_number = '8' + phone_number[1:]
        business_direction_id = self.db.get_business_direction_id(self.gv.CALLBACK_DATA['chosen_direction'])
        surname = surname.capitalize()
        name = name.capitalize()
        patronymic = patronymic.capitalize()
        inn = inn.strip()
        email = email.lower()
        assert len(surname) <= 30 and len(name) <= 30 and len(patronymic) <= 30 and len(email) <= 50
        if self.db.add_client(surname, name, patronymic, sex, tg_id, inn, business_direction_id, phone_number, email):
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CLIENTS)
            await context.bot.send_message(GROUP_ID, f'Добавил клиента в базу {"🧑" if sex == "male" else "👩"}', reply_markup=ReplyKeyboardRemove())
            try:
                await context.bot.send_message(tg_id, "Привет, друг! У меня хорошие новости: тебя только что добавили в базу и ты будешь получать обещанную рассылку!")
            except:
                pass
        else:
            reply_msg = f'❌ Не получилось добавить. В базе уже существует клиент либо с таким же id, либо с таким же ИНН, либо с таким же номером телефона, либо с такой же почтой'
            await context.bot.send_message(GROUP_ID, reply_msg, reply_markup=ReplyKeyboardRemove())

    async def get_clients_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return

        clients_data = self.db.get_clients_data()
        if clients_data is None:
            await context.bot.send_message(GROUP_ID, "Пока нет ни одного клиента")
            return
        df = pd.DataFrame(clients_data, columns=['Фамилия', 'Имя', 'Отчество', 'Пол', 'Телеграм id', 'ИНН', 'Направление бизнеса', 'Номер телефона', 'Почта'])
        df.loc[df['Пол'] == 'male', 'Пол'] = 'м'
        df.loc[df['Пол'] == 'female', 'Пол'] = 'ж'
        file_path = f'File/clients_data.xlsx'
        df.to_excel(file_path, sheet_name='Клиенты', index=False)
        await context.bot.send_document(GROUP_ID, file_path)
        os.remove(file_path)

    async def edit_client_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CLIENTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions('all')
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, 'Пока нет ни одного клиента')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CLIENT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена ❌", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса, в котором нужно отредактировать клиента',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def delete_client(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CLIENTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        if not self.db.clients_exist():
            await context.bot.send_message(GROUP_ID, "Пока нет ни одного клиента")
            return
        business_directions = self.db.get_business_directions('non-empty')
        assert len(business_directions) <= 100
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса, в котором находится клиент, которого нужно удалить или нажми "отмена"',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def delete_business_direction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CLIENTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions('all')
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, "Пока нет ни одного направления бизнеса")
            return
        assert len(business_directions) <= 100
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса, которое нужно удалить или нажми "отмена"',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def show_business_directions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return

        business_directions = self.db.get_business_directions('all')
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, "Пока нет ни одного направления бизнеса")
            return
        reply_msg = 'Текущие направления бизнеса:\n'
        for i in range(len(business_directions)):
            reply_msg += f"\n{i + 1}) {business_directions[i]}"
        await context.bot.send_message(GROUP_ID, reply_msg)

    def check_entered_client_data_and_update(self, message: str, client_id: int):
        lines_entered = list(map(lambda x: x.strip(), message.split('\n')))
        lines_entered = list(filter(lambda x: x != '', lines_entered))
        if len(lines_entered) != 7:
            ending = 'а' if len(lines_entered) == 1 else 'о'
            answer = f'Неверный формат данных. Ожидалось 7 строк, был{ending} получен{ending}: {len(lines_entered)}. '
            answer += f'Введи данные клиента в следующем формате:\n\n{self.EXPECTED_CLIENTS_DATA_FORMAT_TO_EDIT}\n\nили нажми "отмена"'
            return answer
        surname, name, patronymic, sex, inn, phone_number, email = lines_entered
        if surname.startswith('Фамилия: '):
            surname = surname[surname.find(' ') + 1:]
        if name.startswith('Имя: '):
            name = name[name.find(' ') + 1:]
        if patronymic.startswith('Отчество: '):
            patronymic = patronymic[patronymic.find(' ') + 1:]
        if sex.startswith('Пол: '):
            sex = sex[sex.find(' ') + 1:]
        if inn.startswith('ИНН: '):
            inn = inn[inn.find(' ') + 1:]
        if phone_number.startswith('Номер телефона: '):
            phone_number = phone_number[16:]
        if email.startswith('Почта: '):
            email = email[email.find(' ') + 1:]

        if sex[0].lower() == 'м':
            sex = 'male'
        elif sex[0].lower() == 'ж':
            sex = 'female'
        else:
            return f'Неверный формат данных. У пола может быть только 2 значения: "м" и "ж". Жду корректного ввода или нажатия кнопки "отмена"'
        if len(inn) > 15:
            return f'Длина ИНН не может быть больше 15. Повтори попытку'
        for char in phone_number:
            if not char.isdigit():
                phone_number = phone_number.replace(char, '')
        if phone_number == '':
            return f'Номер телефона должен состоять из цифр, если ты не знал. Повтори попытку'
        if len(phone_number) > 11:
            return f'Номер телефона должен не может быть длиннее 11 цифр. Повтори попытку'
        if phone_number[0] == '7':
            phone_number = '8' + phone_number[1:]
        surname = surname.capitalize()
        name = name.capitalize()
        patronymic = patronymic.capitalize()
        inn = inn.strip()
        email = email.lower()
        assert len(surname) <= 30 and len(name) <= 30 and len(patronymic) <= 30 and len(email) <= 50
        return self.db.update_client(client_id, surname, name, patronymic, sex, inn, phone_number, email)