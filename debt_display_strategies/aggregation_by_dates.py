from . import DebtDisplayStrategy


class AggregationByDates(DebtDisplayStrategy):
    def get_unpaid_shifts_message(self) -> str:
        unpaid_shifts, total_debt = self.db.get_unpaid_shifts_by_dates()
        if unpaid_shifts is None:
            return ''
        total_debt = float(total_debt)
        message = f'Общая сумма задолженностей: ' + f'{total_debt:_}'.replace('.', ',').replace('_', '.') + f"{'0 ₽' if total_debt * 100 % 10 == 0 else ' ₽'}"
        for day in unpaid_shifts.keys():
            message += f'\n\nЗа {day.strftime("%d.%m.%Y")}:'
            no = 1
            for salary in unpaid_shifts[day]:
                debt = float(salary['debt'])
                message += f"\n{no}) {salary['person']} -> " + f"{debt:_}".replace('.', ',').replace('_', '.') + f"{'0 ₽' if debt * 100 % 10 == 0 else ' ₽'}"
                no += 1
        return message

    def get_next_payment_message(self, offset=0) -> [str, dict]:
        general_info, specific_info = self.db.get_next_payment_by_dates(offset)
        if general_info is None:
            return '', None
        date, first_last_name, phone_number, act_number, bank, debt = general_info
        current_debt = {'date': date, 'phone_number': phone_number, 'act_number': act_number}
        debt = f"{debt:_}".replace('_', '.') + ",00 ₽"
        message = f'Дата задолженности: {date.strftime("%d.%m.%Y")}\nАкт: {act_number}\nСотрудник: {first_last_name}\n' + \
                  f'Телефон: `{self.prettify_phone_number(phone_number)}`\nБанк: {bank.capitalize()}\nНеобходимо заплатить: {debt}'
        message += f'\n\nУпакованные товары:'
        product_no = 1
        for product in specific_info:
            barcode, name, tariff, amount = product
            message += f'\n{product_no}) {barcode}, "{name}"  ->  {tariff}₽ ✖ {amount} шт.'
            product_no += 1
        return message, current_debt

    def mark_shift_as_paid(self, current_debt: dict):
        self.db.mark_shift_as_paid__aggregation_by_dates(current_debt['date'], current_debt['phone_number'], current_debt['act_number'])