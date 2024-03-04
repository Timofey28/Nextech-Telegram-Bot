from . import DebtDisplayStrategy


class AggregationByPeople(DebtDisplayStrategy):
    def get_unpaid_shifts_message(self) -> str:
        unpaid_shifts, total_debt = self.db.get_unpaid_shifts_by_dates()
        if unpaid_shifts is None:
            return ''
        message = f'Общая сумма задолженностей: ' + f'{total_debt:_}'.replace('_', '.') + ',00 ₽'
        for day in unpaid_shifts.keys():
            message += f'\n\nЗа {day.strftime("%d.%m.%Y")}:'
            no = 1
            for salary in unpaid_shifts[day]:
                message += f"\n{no}) {salary['person']} -> " + f"{salary['debt']:_}".replace('_', '.') + ',00 ₽'
                no += 1
        return message

    def get_next_payment_message(self, offset=0) -> [str, dict]:
        general_info, specific_info = self.db.get_next_payment_by_people(offset)
        if general_info is None:
            return '', None
        employee_id, first_last_name, phone_number, bank, debt = general_info
        current_debt = {'employee_id': employee_id}
        debt = f"{debt:_}".replace('_', '.') + ",00 ₽"
        message = f'Сотрудник: {first_last_name}\nТелефон: `{self.prettify_phone_number(phone_number)}`\n' + \
                  f'Банк: {bank.capitalize()}\nНеобходимо заплатить: {debt}'
        message += f'\n\nУпакованные товары:'
        for day in specific_info:
            for act_number in specific_info[day]:
                product_no = 1
                message += f'\n\n🔹 За {day.strftime("%d.%m.%Y")}, акт {act_number}:'
                if specific_info[day][act_number] is None:
                    message += '\nНИ-ХУ-Я'
                    continue
                for product in specific_info[day][act_number]:
                    barcode, name, tariff, amount = product
                    message += f'\n{product_no}) {barcode}, "{name}"  ->  {tariff}₽ ✖ {amount} шт.'
                    product_no += 1
        return message, current_debt

    def mark_shift_as_paid(self, current_debt: dict):
        self.db.mark_shift_as_paid__aggregation_by_people(current_debt['employee_id'])