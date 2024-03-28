import logging
import os
from datetime import datetime, date
import re
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


class Contracts:
    def __init__(self, globalVars: GlobalVars, database: Database):
        self.gv = globalVars
        self.db = database
        self.CONTRACT_EDITING_OPTIONS = [[InlineKeyboardButton('Даты и суммы платежей', callback_data='payment_schedule')],
                                         [InlineKeyboardButton('Заменить сам документ', callback_data='change_document_itself')],
                                         [InlineKeyboardButton('Закрыть договор', callback_data='close_contract')],
                                         [InlineKeyboardButton('ничего ❌', callback_data='отмена')]]

    async def send_contract_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        template_names = os.listdir(self.gv.PATH_CONCTRACT_TEMPLATES)
        if not template_names:
            await context.bot.send_message(self.gv.ACCOUNTANT_GROUP_ID, 'На сервере пока нет шаблонов договоров')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_CONTRACT_TEMPLATE_TO_SEND_ONE)
        buttons = []
        counter = 1
        for template_name in template_names:
            buttons.append([InlineKeyboardButton(template_name[:template_name.rfind('.')], callback_data=f'{counter}')])
            self.gv.CALLBACK_DATA[f'{counter}'] = template_name
            counter += 1
        buttons.append([InlineKeyboardButton('никакой, уже не надо ❌', callback_data='отмена')])
        await context.bot.send_message(GROUP_ID, 'Какой из шаблонов скинуть?', reply_markup=InlineKeyboardMarkup(buttons))

    async def add_contract(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions('all')
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, 'Нельзя добавить договор если нет клиентов')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CONTRACT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Клиенту из какого направления бизнеса нужно добавить договор?',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def enter_contract_data_stage_1(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        msg = update.message.text
        if msg.lower() == "отмена":
            await context.bot.send_message(GROUP_ID, '🆗', reply_markup=ReplyKeyboardRemove())
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CONTRACTS)
            return
        lines_entered = list(map(lambda x: x.strip(), msg.split('\n')))
        lines_entered = list(filter(lambda x: x != '', lines_entered))
        if len(lines_entered) != 3:
            ending = 'а' if len(lines_entered) == 1 else 'о'
            ans = f'Неверный формат данных. Ожидалось 3 строки, был{ending} получен{ending}: {len(lines_entered)}. '
            ans += 'Введи следующие данные\n\n1) Компания клиента\n2) Дата заключения договора в формате "дд.мм.гг"'
            ans += '\n3) Полная сумма платежа (либо ежемесячная сумма платежа, если договор регулярный)'
            ans += '\n\nлибо нажми "отмена"'
            await context.bot.send_message(GROUP_ID, ans)
            return
        company_name = lines_entered[0]
        if len(company_name) > 100:
            await context.bot.send_message(GROUP_ID, 'Слишком длинное название компании. Повтори попытку')
            return
        try:
            date_of_conclusion = datetime.strptime(lines_entered[1], "%d.%m.%y").date()
        except ValueError:
            ans = 'Не получилось считать дату заключения договора. '
            s = lines_entered[1]
            if len(s) == 8 and s[:2].isdigit() and s[3:5].isdigit() and s[6:].isdigit() and s[2] == s[5] == '.':
                ans += 'Она должна существовать. '
            else:
                ans += 'Она должна быть в формате "дд.мм.гг". '
            ans += 'Повтори попытку или нажми "отмена"'
            await context.bot.send_message(GROUP_ID, ans)
            return
        try:
            amount = int(lines_entered[2])
        except:
            ans = 'Не получилось считать полную сумму платежа. Должно быть просто число без каких-либо других символов. '
            ans += 'Повтори попытку или нажми "отмена"'
            await context.bot.send_message(GROUP_ID, ans)
            return
        self.gv.CALLBACK_DATA['client_company'] = company_name
        self.gv.CALLBACK_DATA['date_of_conclusion'] = date_of_conclusion
        self.gv.CALLBACK_DATA['full_payment_amount'] = amount
        self.gv.set_group_status('accountant', self.gv.Status_ENTERING_CONTRACT_INFO_STAGE_2)
        msg = 'Этап 2️⃣. Скинь подписанный договор. Название файла должно быть подобно следующему: "Договор А1 от 03.04.2024г."'
        await context.bot.send_message(GROUP_ID, msg)

    async def enter_contract_data_stage_3(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        date_of_conclusion = self.gv.CALLBACK_DATA['date_of_conclusion']
        msg = update.message.text
        if msg.lower() == "отмена":
            os.remove(self.gv.CURRENT_FILE)
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CONTRACTS)
            await context.bot.send_message(GROUP_ID, '🆗', reply_markup=ReplyKeyboardRemove())
            return
        error_msg = 'Данные должны быть в следующем формате:\n\n'
        if self.gv.CALLBACK_DATA['contract_type'] == 'regular':
            error_msg += 'Число месяца от 1 до 28 - сумма платежа'
        else:
            error_msg += 'Дата в формате "дд.мм.гг" - сумма платежа'
        error_msg += '\n\nСтрого по одному платежу в строке. Повтори попытку или нажми "отмена"'

        lines_entered = list(map(lambda x: x.strip(), msg.split('\n')))
        lines_entered = list(filter(lambda x: x != '', lines_entered))
        scheduled_payments: list[[date, int]] = []
        full_payment_amount = 0
        for line in lines_entered:
            if line.count('-') != 1:
                await context.bot.send_message(GROUP_ID, error_msg)
                return
            day = line[:line.find('-')].strip()
            payment_amount = line[line.find('-') + 1:].strip()
            try:
                if self.gv.CALLBACK_DATA['contract_type'] == 'regular':
                    day = int(day)
                    if not 1 <= day <= 28:
                        raise ValueError
                    day = date(date.today().year, date.today().month, day)
                else:
                    day = datetime.strptime(day, "%d.%m.%y").date()
                    if day < date_of_conclusion:
                        msg = f'Дата платежа ({day.strftime("%d.%m.%y")}) не может быть раньше даты заключения договора'
                        msg += f' ({date_of_conclusion.strftime("%d.%m.%y")}). Повтори попытку или нажми "отмена"'
                        await context.bot.send_message(GROUP_ID, msg)
                        return
                payment_amount = int(payment_amount)
            except ValueError:
                await context.bot.send_message(GROUP_ID, error_msg)
                return
            scheduled_payments.append([day, payment_amount])
            full_payment_amount += payment_amount
        if full_payment_amount != self.gv.CALLBACK_DATA['full_payment_amount']:
            ans = f"Полные суммы платежей не совпадают\n\nОжидалось: {self.gv.CALLBACK_DATA['full_payment_amount']:,} ₽"
            ans += f'\nБыло введено: {full_payment_amount:,} ₽'
            ans += '\n\nПовтори попытку или нажми "отмена"'
            await context.bot.send_message(GROUP_ID, ans)
            return

        self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CONTRACTS)
        os.replace(self.gv.CURRENT_FILE, f"{self.gv.PATH_CONTRACTS}/{self.gv.CALLBACK_DATA['file_name']}")
        contract_id = self.db.add_contract(self.gv.CALLBACK_DATA['file_name'],
                                           self.gv.CALLBACK_DATA['contract_code'],
                                           self.gv.CALLBACK_DATA['contract_type'],
                                           self.gv.CALLBACK_DATA['client_id'],
                                           self.gv.CALLBACK_DATA['client_company'],
                                           self.gv.CALLBACK_DATA['date_of_conclusion'])
        self.db.add_payment_dates_and_amounts(contract_id, scheduled_payments)
        await context.bot.send_message(GROUP_ID, 'Договор успешно добавлен ✅', reply_markup=ReplyKeyboardRemove())

    async def edit_contract(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions_containing_active_contracts()
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, 'На сервере пока нет ни одного договора')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CONTRACT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса человека, договор с которым нужно отредактировать',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def edit_contract_payment_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        contract_id = self.gv.CALLBACK_DATA['contract_id']
        contract_name = self.gv.CALLBACK_DATA['contract_file_name']
        contract_name = contract_name[:contract_name.rfind('.')]
        contract_type = self.gv.CALLBACK_DATA['contract_type']
        current_payment_info = self.db.get_scheduled_payment_dates_and_amounts(contract_id)
        if current_payment_info is None:
            logging.error("contract can't have no scheduled payment info (dates and amounts)")
            exit(0)
        self.gv.set_group_status('accountant', self.gv.Status_ENTERING_UPDATED_CONTRACT_PAYMENT_SCHEDULE)
        msg = f'Текущий график платежей договора "{contract_name}":\n'
        full_payment_amount = 0
        for dat, amount in current_payment_info:
            full_payment_amount += amount
            if contract_type == 'regular':
                msg += f'\n{dat.day} - {amount:,} ₽'
            else:
                msg += f'\n{dat.strftime("%d.%m.%y")} - {amount:,} ₽'
        self.gv.CALLBACK_DATA['full_payment_amount'] = full_payment_amount
        msg += f'\n\nСуммарный платеж: {full_payment_amount:,} ₽'
        if contract_type == 'regular':
            msg += '/мес.'
        await context.bot.send_message(GROUP_ID, msg)
        msg = 'Введи новый график платежей в следующем формате:\n\n'
        if contract_type == 'regular':
            msg += 'Число месяца от 1 до 28 - сумма платежа'
        else:
            msg += 'Дата в формате "дд.мм.гг" - сумма платежа'
        await context.bot.send_message(GROUP_ID, msg, reply_markup=ReplyKeyboardMarkup(self.gv.CANCEL_BUTTON))

    async def enter_updated_contract_payment_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        msg = update.message.text
        if msg == "отмена":
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CONTRACTS)
            await context.bot.send_message(GROUP_ID, '🆗', reply_markup=ReplyKeyboardRemove())
        else:
            error_msg = 'Данные должны быть в следующем формате:\n\n'
            if self.gv.CALLBACK_DATA['contract_type'] == 'regular':
                error_msg += 'Число месяца от 1 до 28 - сумма платежа'
            else:
                error_msg += 'Дата в формате "дд.мм.гг" - сумма платежа'
            error_msg += '\n\nСтрого по одному платежу в строке. Повтори попытку или нажми "отмена"'

            lines_entered = list(map(lambda x: x.strip(), msg.split('\n')))
            lines_entered = list(filter(lambda x: x != '', lines_entered))
            scheduled_payments: list[[date, int]] = []
            full_payment_amount = 0
            for line in lines_entered:
                if line.count('-') != 1:
                    await context.bot.send_message(GROUP_ID, error_msg)
                    return
                day = line[:line.find('-')].strip()
                payment_amount = line[line.find('-') + 1:].strip()
                try:
                    if self.gv.CALLBACK_DATA['contract_type'] == 'regular':
                        day = int(day)
                        if not 1 <= day <= 28:
                            raise ValueError
                        day = date(date.today().year, date.today().month, day)
                    else:
                        day = datetime.strptime(day, "%d.%m.%y").date()
                    payment_amount = int(payment_amount)
                except ValueError:
                    await context.bot.send_message(GROUP_ID, error_msg)
                    return
                scheduled_payments.append([day, payment_amount])
                full_payment_amount += payment_amount
            if full_payment_amount != self.gv.CALLBACK_DATA['full_payment_amount']:
                ans = f"Полные суммы платежей не совпадают\n\nОжидалось: {self.gv.CALLBACK_DATA['full_payment_amount']:,} ₽"
                ans += f'\nБыло введено: {full_payment_amount:,} ₽'
                ans += '\n\nПовтори попытку или нажми "отмена"'
                await context.bot.send_message(GROUP_ID, ans)
                return

            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_CONTRACTS)
            self.db.update_payment_dates_and_amounts(self.gv.CALLBACK_DATA['contract_id'], scheduled_payments)
            await context.bot.send_message(GROUP_ID, 'График платежей успешно изменен ✅', reply_markup=ReplyKeyboardRemove())

    async def list_of_contracts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        active_contracts, closed_contracts = self.db.get_contracts_list()
        if active_contracts is None and closed_contracts is None:
            await context.bot.send_message(self.gv.ACCOUNTANT_GROUP_ID, 'На сервере пока нет договоров')
            return
        msg = ''
        if active_contracts:
            counter = 1
            msg = 'Действующие договоры:\n'
            for contract in active_contracts:
                contract_name = contract[2][:contract[2].rfind('.')]
                msg += f'\n{counter}) {contract[0]} {contract[1]} 🤝 {contract_name}'
                counter += 1
        if closed_contracts:
            counter = 1
            if msg:
                msg += '\n\n'
            msg += 'Закрытые договоры:\n'
            for contract in closed_contracts:
                contract_name = contract[2][:contract[2].rfind('.')]
                msg += f'\n{counter}) {contract[0]} {contract[1]} 🤝🏻 {contract_name}'
                counter += 1
        await context.bot.send_message(self.gv.ACCOUNTANT_GROUP_ID, msg)

    async def send_contract(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        business_directions = self.db.get_business_directions_containing_active_contracts()
        if business_directions is None:
            await context.bot.send_message(GROUP_ID, 'На сервере пока нет договоров')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_CONTRACT)
        self.gv.CALLBACK_DATA.clear()
        buttons = []
        for i in range(len(business_directions)):
            buttons.append([InlineKeyboardButton(business_directions[i], callback_data=f"btn_{i}")])
            self.gv.CALLBACK_DATA[f"btn_{i}"] = business_directions[i]
        buttons.append([InlineKeyboardButton("отмена", callback_data="отмена")])
        await context.bot.send_message(GROUP_ID, 'Выбери направление бизнеса человека, договор с которым нужно скинуть',
                                       reply_markup=InlineKeyboardMarkup(buttons))

    async def add_or_change_contract_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        self.gv.set_group_status('accountant', self.gv.Status_SENDING_NEW_CONTRACT_TEMPLATE)
        await context.bot.send_message(GROUP_ID, 'Скинь новый шаблон договора или нажми "отмена"', reply_markup=ReplyKeyboardMarkup(self.gv.CANCEL_BUTTON))

    async def delete_contract_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        if update.effective_chat.id != GROUP_ID:
            return
        if self.gv.ACCOUNTANT_GROUP_STATUS != self.gv.Status_IN_SECTION_CONTRACTS:
            await context.bot.send_message(GROUP_ID, 'Сначала заверши предыдущее действие, нажав одну из кнопок')
            return

        template_names = os.listdir(self.gv.PATH_CONCTRACT_TEMPLATES)
        if not template_names:
            await context.bot.send_message(self.gv.ACCOUNTANT_GROUP_ID, 'Удалять пока нечего)')
            return
        self.gv.set_group_status('accountant', self.gv.Status_PRESSING_CONTRACT_TEMPLATE_TO_DELETE_ONE)
        buttons = []
        counter = 1
        for template_name in template_names:
            buttons.append([InlineKeyboardButton(template_name[:template_name.rfind('.')], callback_data=f'{counter}')])
            self.gv.CALLBACK_DATA[f'{counter}'] = template_name
            counter += 1
        buttons.append([InlineKeyboardButton('НИНАДА', callback_data='отмена')])
        await context.bot.send_message(GROUP_ID, 'Какой из шаблонов удалить?', reply_markup=InlineKeyboardMarkup(buttons))

    @staticmethod
    def contract_name_has_english_letters(contract_name: str):
        return re.search('[a-zA-Z]', contract_name) is not None