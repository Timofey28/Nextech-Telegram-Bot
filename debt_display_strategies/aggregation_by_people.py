from . import DebtDisplayStrategy


class AggregationByPeople(DebtDisplayStrategy):
    def get_unpaid_shifts_message(self) -> str:
        unpaid_shifts, total_debt = self.db.get_unpaid_shifts_by_dates()
        if unpaid_shifts is None:
            return ''
        total_debt = round(float(total_debt), 2)
        total_debt_str = f'{total_debt:_}'.replace('.', ',').replace('_', '.') + f"{'0 ₽' if total_debt * 10 % 1 < self.very_small_number else ' ₽'}"
        message = f'Общая сумма задолженностей: {total_debt_str}'
        for day in unpaid_shifts.keys():
            message += f'\n\nЗа {day.strftime("%d.%m.%Y")}:'
            no = 1
            for salary in unpaid_shifts[day]:
                debt = round(float(salary['debt']), 2)
                debt_str = f"{debt:_}".replace('.', ',').replace('_', '.') + f"{'0 ₽' if debt * 10 % 1 < self.very_small_number else ' ₽'}"
                message += f"\n{no}) {salary['person']} -> {debt_str}"
                no += 1
        return message

    def get_next_payment_message(self, offset=0) -> [str, dict]:
        general_info, specific_info, people_left = self.db.get_next_payment_by_people(offset)
        if general_info is None:
            return '', None
        employee_id, first_last_name, phone_number, bank, debt = general_info
        current_debt = {'employee_id': employee_id}
        debt = round(float(debt), 2)
        debt_str = f"{debt:_}".replace('.', ',').replace('_', '.') + f"{'0 ₽' if debt * 10 % 1 < self.very_small_number else ' ₽'}"
        message = f'Сотрудник: {first_last_name}\nТелефон: `{self.prettify_phone_number(phone_number)}`\n' + \
                  f'Банк: {bank.capitalize()}\nНеобходимо заплатить: {debt_str}\nЛюдей осталось: {people_left if people_left else "этот последний"}'
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