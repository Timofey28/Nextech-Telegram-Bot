import os
from datetime import datetime, date, timedelta
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


class Payments:
    def __init__(self, globalVars: GlobalVars, database: Database):
        self.gv = globalVars
        self.db = database
        self.YES_OR_NO = [[InlineKeyboardButton('Нееее', callback_data='no'), InlineKeyboardButton('Да 💪', callback_data='yes')]]

    async def add_paid_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.gv.set_group_status('accountant', self.gv.Status_ENTERING_PAID_PAYMENT_INFO)
        msg = 'Введи номер договора и сумму платежа через пробел ✏\n\n'
        msg += '❗Если платеж пришел не сегодня, то обязательно добавь дату его прихода в той же строке через пробел в формате "дд.мм.гг"'
        msg += f'\n\nПримеры ввода:\n- A1 100000\n- б1 50000 {(date.today() - timedelta(days=5)).strftime("%d.%m.%y")}'
        await context.bot.send_message(self.gv.ACCOUNTANT_GROUP_ID, msg, reply_markup=ReplyKeyboardMarkup(self.gv.CANCEL_BUTTON))

    async def enter_paid_payment_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        msg = update.message.text
        if msg == 'отмена':
            self.gv.set_group_status('accountant', self.gv.Status_IN_SECTION_PAYMENTS)
            await context.bot.send_message(GROUP_ID, '🆗', reply_markup=ReplyKeyboardRemove())
            return
        contract_code = msg[:msg.find(' ')]
        payment_amount = msg[msg.find(' ') + 1:].strip()
        payment_date = date.today()
        if payment_amount.find(' ') != -1:
            s = payment_amount[payment_amount.find(' '):].strip()
            payment_amount = payment_amount[:payment_amount.find(' ')]
            try:
                payment_date = datetime.strptime(s, "%d.%m.%y").date()
            except ValueError:
                msg = 'Не удалось прочитать дату платежа, '
                if len(s) == 8 and s[:2].isdigit() and s[3:5].isdigit() and s[6:].isdigit() and s[2] == s[5] == '.':
                    msg += 'она должна существовать. '
                else:
                    msg += 'она должна быть в формате "дд.мм.гг". '
                msg += 'Повтори попытку или нажми "отмена"'
                await context.bot.send_message(GROUP_ID, msg)
                return

        if not self.db.contract_code_exists(contract_code):
            await context.bot.send_message(GROUP_ID, 'Договора с таким номером нет. Повтори попытку или нажми "отмена"')
            return
        try:
            payment_amount = int(payment_amount)
        except ValueError:
            msg = 'Не удалось прочитать сумму платежа. Она должна состоять только из цифр от 0 до 9. Повтори попытку или нажми "отмена"'
            await context.bot.send_message(GROUP_ID, msg)
            return
        self.gv.set_group_status('accountant', self.gv.Status_ADDING_PAID_PAYMENT_CONFIRMATION)
        self.gv.CALLBACK_DATA.clear()
        self.gv.CALLBACK_DATA['contract_code'] = contract_code
        self.gv.CALLBACK_DATA['payment_date'] = payment_date
        self.gv.CALLBACK_DATA['payment_amount'] = payment_amount
        msg = f'Добавляем оплаченный {payment_date.strftime("%d.%m.%y")} платеж договора номер "{contract_code.upper()}" в размере {payment_amount:,} ₽?'
        await context.bot.send_message(GROUP_ID, msg, reply_markup=InlineKeyboardMarkup(self.YES_OR_NO))

    def get_scheduled_payments_for_today_tomorrow_msg(self) -> (str, bool):
        today_contracts_regular = self.db.get_soonest_debts_cns('regular', 'today')
        today_contracts_onetime = self.db.get_soonest_debts_cns('onetime', 'today')
        tomorrow_contracts_regular = self.db.get_soonest_debts_cns('regular', 'tomorrow')
        tomorrow_contracts_onetime = self.db.get_soonest_debts_cns('onetime', 'tomorrow')
        today_debts_regular, today_debts_onetime = [], []
        tomorrow_debts_regular, tomorrow_debts_onetime = [], []

        today = date.today()
        tomorrow = today + timedelta(days=1)
        remark = False

        if today_contracts_regular:
            for code, client_name, surname, date_of_conclusion in today_contracts_regular:
                debts = self.db.get_total_scheduled_payment(code, 'regular')
                total_debt = 0
                month_diff = self.get_months_difference(date_of_conclusion, today) - 1
                if month_diff < 0:
                    for day, amount in debts:
                        if date_of_conclusion.day < day <= today.day:
                            total_debt += amount
                else:
                    monthly_debt = sum(list(map(lambda x: x[1], debts)))
                    total_debt += monthly_debt * month_diff  # считаем за все месяцы кроме первого и текущего (все полные месяцы)
                    for day, amount in debts:
                        # если даты графика платежей входят в промежуток, то прибавляем задолженности за первый и текущий месяцы
                        if day > date_of_conclusion.day:
                            total_debt += amount
                        if day <= today.day:
                            total_debt += amount
                total_paid = self.db.get_total_actual_payment(code)
                if total_debt > total_paid:
                    today_scheduled_payment = self.db.get_certain_day_scheduled_payment(code, 'regular', 'today')
                    debt = total_debt - total_paid
                    past_debt = debt - today_scheduled_payment if debt > today_scheduled_payment else 0
                    if past_debt > 0:
                        remark = True
                    today_debts_regular.append([code, client_name, surname, debt, past_debt])
        if today_contracts_onetime:
            for code, client_name, surname, date_of_conclusion in today_contracts_onetime:
                total_debt = self.db.get_total_scheduled_payment(code, 'onetime', 'today')
                total_paid = self.db.get_total_actual_payment(code)
                if total_debt > total_paid:
                    today_scheduled_payment = self.db.get_certain_day_scheduled_payment(code, 'onetime', 'today')
                    debt = total_debt - total_paid
                    past_debt = debt - today_scheduled_payment if debt > today_scheduled_payment else 0
                    if past_debt > 0:
                        remark = True
                    today_debts_onetime.append([code, client_name, surname, debt, past_debt])
        if tomorrow_contracts_regular:
            for code, client_name, surname, date_of_conclusion in tomorrow_contracts_regular:
                debts = self.db.get_total_scheduled_payment(code, 'regular')
                total_debt = 0
                month_diff = self.get_months_difference(date_of_conclusion, tomorrow) - 1
                if month_diff < 0:
                    for day, amount in debts:
                        if date_of_conclusion.day < day <= today.day:
                            total_debt += amount
                else:
                    monthly_debt = sum(list(map(lambda x: x[1], debts)))
                    total_debt += monthly_debt * month_diff  # считаем за все месяцы кроме первого и текущего (все полные месяцы)
                    for day, amount in debts:
                        # если даты графика платежей входят в промежуток, то прибавляем задолженности за первый и текущий месяцы
                        if day > date_of_conclusion.day:
                            total_debt += amount
                        if day <= tomorrow.day:
                            total_debt += amount
                total_paid = self.db.get_total_actual_payment(code)
                if total_debt > total_paid:
                    tomorrow_scheduled_payment = self.db.get_certain_day_scheduled_payment(code, 'regular', 'tomorrow')
                    debt = total_debt - total_paid
                    past_debt = debt - tomorrow_scheduled_payment if debt > tomorrow_scheduled_payment else 0
                    if past_debt > 0:
                        remark = True
                    tomorrow_debts_regular.append([code, client_name, surname, debt, past_debt])
        if tomorrow_contracts_onetime:
            for code, client_name, surname, date_of_conclusion in tomorrow_contracts_onetime:
                total_debt = self.db.get_total_scheduled_payment(code, 'onetime', 'tomorrow')
                total_paid = self.db.get_total_actual_payment(code)
                if total_debt > total_paid:
                    tomorrow_scheduled_payment = self.db.get_certain_day_scheduled_payment(code, 'onetime', 'tomorrow')
                    debt = total_debt - total_paid
                    past_debt = debt - tomorrow_scheduled_payment if debt > tomorrow_scheduled_payment else 0
                    if past_debt > 0:
                        remark = True
                    tomorrow_debts_onetime.append([code, client_name, surname, debt, past_debt])

        msg = ''
        if today_debts_regular or today_debts_onetime:
            msg = 'Плановые платежи *на сегодня*\n'
            counter = 1
            if today_debts_regular:
                for code, client_name, surname, debt, past_debt in today_debts_regular:
                    msg += f'\n{counter}) {client_name} {surname}, {code.upper()} -> {debt:,} ₽'
                    if past_debt:
                        msg += f' (+{past_debt:,} ₽)'
                    counter += 1
            if today_debts_onetime:
                for code, client_name, surname, debt, past_debt in today_debts_onetime:
                    msg += f'\n{counter}) {client_name} {surname}, {code.upper()} -> {debt:,} ₽'
                    if past_debt:
                        msg += f' (+{past_debt:,} ₽)'
                    counter += 1

        if tomorrow_debts_regular or tomorrow_debts_onetime:
            msg += '\n\nПлановые платежи *на завтра*\n'
            counter = 1
            if tomorrow_debts_regular:
                for code, client_name, surname, debt, past_debt in tomorrow_debts_regular:
                    msg += f'\n{counter}) {client_name} {surname}, {code.upper()} -> {debt:,} ₽'
                    if past_debt:
                        msg += f' (+{past_debt:,} ₽)'
                    counter += 1
            if tomorrow_debts_onetime:
                for code, client_name, surname, debt, past_debt in tomorrow_debts_onetime:
                    msg += f'\n{counter}) {client_name} {surname}, {code.upper()} -> {debt:,} ₽'
                    if past_debt:
                        msg += f' (+{past_debt:,} ₽)'
                    counter += 1

        if remark:
            remark = 'Порядок вывода:\n♦️Первое число - общая задолженность клиента\n'
            remark += '♦️Число в скобках - задолженность до текущего дня (она входит в общую и как бы добавляется к сегодняшней/завтрашней)'
        return msg, remark

    async def payment_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        regular_contracts_schedule = self.db.get_contracts_payment_schedule('regular')
        onetime_contracts_schedule = self.db.get_contracts_payment_schedule('onetime')
        msg = ''
        if regular_contracts_schedule:
            msg = '*Постоянные платежи*'
            for contract, schedule in regular_contracts_schedule:
                code, client_name, surname = contract
                schedule.sort()
                msg += f'\n\n📋 {code} ({client_name} {surname})\n'
                for day, amount in schedule:
                    msg += f'\n💰 {day} - {amount:,} ₽'
        if onetime_contracts_schedule:
            msg += '\n\n\n*Разовые платежи*'
            for contract, schedule in onetime_contracts_schedule:
                for i in range(len(schedule)):
                    schedule[i] = [date(schedule[i][0], schedule[i][1], schedule[i][2]), schedule[i][3]]
                schedule.sort()
            for contract, schedule in onetime_contracts_schedule:
                code, client_name, surname = contract
                schedule.sort()
                msg += f'\n\n📄 {code} ({client_name} {surname})\n'
                for dat, amount in schedule:
                    msg += f'\n💸 {dat.strftime("%d.%m.%y")} - {amount:,} ₽'
        if not regular_contracts_schedule and not onetime_contracts_schedule:
            await context.bot.send_message(GROUP_ID, 'Пока не добавлено ни одного договора')
        else:
            await context.bot.send_message(GROUP_ID, msg, parse_mode='markdown')

    async def list_of_clients_debts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        debts = self.db.get_contracts_debts()
        regular_debts, onetime_debts = [], []
        today = date.today()
        for contract_info, date_of_conclusion, paying_schedule, debt in debts:
            code, client_name, surname, contract_type = contract_info
            paid = self.db.get_paid_amount(code)
            if contract_type == 'regular':
                total_debt = 0
                month_diff = self.get_months_difference(date_of_conclusion, today) - 1
                if month_diff < 0:
                    for day, amount in debts:
                        if date_of_conclusion.day < day <= today.day:
                            total_debt += amount
                else:
                    total_debt += debt * month_diff  # считаем за все месяцы кроме первого и текущего (все полные месяцы)
                    for day, amount in paying_schedule:
                        # если даты графика платежей входят в промежуток, то прибавляем задолженности за первый и текущий месяцы
                        if day > date_of_conclusion.day:
                            total_debt += amount
                        if day <= today.day:
                            total_debt += amount
                debt = total_debt
                assert debt - paid >= 0
                if debt - paid > 0:
                    regular_debts.append([code, client_name, surname, debt - paid])
            else:
                assert debt - paid >= 0
                onetime_debts.append([code, client_name, surname, debt - paid])
        msg = ''
        counter = 1
        if regular_debts:
            msg = '*Регулярные клиенты*\n'
            for code, client_name, surname, debt in regular_debts:
                msg += f'\n{counter}) {client_name} {surname} ({code.upper()}) -> {debt:,} ₽'
                counter += 1
        if onetime_debts:
            msg += '\n\n*Нерегулярные клиенты*\n'
            for code, client_name, surname, debt in onetime_debts:
                msg += f'\n{counter}) {client_name} {surname} ({code.upper()}) -> {debt:,} ₽'
                if debt == 0:
                    msg += ' (закрой этот договор, или я продолжу тратить лишнее время на подсчет долга, которого нет 😐)'
                counter += 1
        if not regular_debts and not onetime_debts:
            await context.bot.send_message(GROUP_ID, 'На данный момент никаких задолженностей нет')
        else:
            await context.bot.send_message(GROUP_ID, msg, parse_mode='markdown')

    async def list_of_actual_payments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        GROUP_ID = self.gv.ACCOUNTANT_GROUP_ID
        actual_payments = self.db.get_all_actual_payments()
        if actual_payments is None:
            await context.bot.send_message(GROUP_ID, 'Пока не было фактических платежей')
        else:
            df = pd.DataFrame(actual_payments, columns=['Дата', 'Номер договора', 'ФИО', 'Сумма платежа'])
            file_path = f'File/actual_payments.xlsx'
            df.to_excel(file_path, sheet_name='Фактические платежи', index=False)
            await context.bot.send_document(GROUP_ID, file_path)
            os.remove(file_path)

    @staticmethod
    def get_months_difference(d1: date, d2: date) -> int:
        if d1 > d2:
            d1, d2 = d2, d1
        diff_year = d2.year - d1.year
        diff_month = d2.month - d1.month
        return diff_month + diff_year * 12