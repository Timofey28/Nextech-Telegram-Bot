from datetime import date, datetime
import psycopg2
import pandas as pd


class Database:
    def __init__(self, db_dbname: str, db_host: str, db_user: str, db_password: str):
        self.connection = psycopg2.connect(dbname=db_dbname,
                                           host=db_host,
                                           user=db_user,
                                           password=db_password)
        self.curr = self.connection.cursor()

    def add_business_direction(self, direction_name: str):
        query = f"INSERT INTO business_directions (name) VALUES('{direction_name}');"
        self.curr.execute(query)
        self.connection.commit()

    def delete_business_direction(self, business_direction_name: str) -> bool:
        query = f"SELECT bd.name FROM clients JOIN business_directions bd ON clients.business_direction_id = bd.id;"
        self.curr.execute(query)
        result = self.curr.fetchall()
        names = [item[0] for item in result] if result else None
        if names is None or business_direction_name not in names:
            query = f"DELETE FROM business_directions WHERE name = '{business_direction_name}';"
            self.curr.execute(query)
            self.connection.commit()
            return True
        else:
            return False

    def business_direction_exists(self, business_direction_name: str) -> bool:
        query = f"SELECT * FROM business_directions WHERE name = '{business_direction_name}';"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            return True
        return False

    def get_business_directions(self, which: str):
        assert which == 'all' or which == 'non-empty'
        if which == 'all':
            query = f"SELECT name FROM business_directions;"
        else:
            query = f"SELECT DISTINCT bd.name FROM clients JOIN business_directions bd ON business_direction_id = bd.id;"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            return [item[0] for item in result]
        else:
            return None

    def get_business_direction_id(self, business_direction_name: str) -> int:
        query = f"SELECT id FROM business_directions WHERE name = '{business_direction_name}';"
        self.curr.execute(query)
        result = self.curr.fetchall()
        assert result != []
        return result[0][0]

    def add_client(self, surname: str, name: str, patronymic: str, sex: str, tg_id: int, inn: str,
                   business_direction_id: int, phone_number: str, email: str) -> bool:
        assert phone_number.isdigit()
        query = f"INSERT INTO clients (surname, name, patronymic, sex, tg_id, inn, business_direction_id, phone_number, email) " + \
                f"VALUES('{surname}', '{name}', '{patronymic}', '{sex}', {tg_id}, '{inn}', {business_direction_id}, '{phone_number}', '{email}');"
        try:
            self.curr.execute(query)
            self.connection.commit()
            return True
        except:
            return False

    def delete_client(self, tg_id: int):
        query = f"DELETE FROM sent_messages WHERE tg_id = {tg_id};"
        self.curr.execute(query)
        query = f"DELETE FROM clients WHERE tg_id = {tg_id};"
        self.curr.execute(query)
        self.connection.commit()

    def get_clients_data(self, tg_id=None):
        if tg_id is None:
            query = "SELECT surname, clients.name, patronymic, sex, tg_id, inn, bd.name, phone_number, email " + \
                    "FROM clients JOIN business_directions bd ON business_direction_id = bd.id;"
        else:
            assert type(tg_id) is int
            query = f"SELECT surname, clients.name, patronymic, sex, tg_id, inn, bd.name, phone_number, email " + \
                    f"FROM clients JOIN business_directions bd ON business_direction_id = bd.id WHERE tg_id = {tg_id};"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            result = list(map(lambda x: list(x), result))
            if tg_id is not None:
                result = result[0]
        else:
            result = None
        return result

    def get_clients_from_business_direction(self, business_direction: str) -> list[list[str]]:
        query = f"SELECT clients.name, surname, tg_id, phone_number FROM clients JOIN business_directions bd ON business_direction_id = bd.id WHERE bd.name = '{business_direction}';"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            result = list(map(lambda x: list(x), result))
        else:
            result = None
        return result

    def client_exists(self, tg_id: int) -> bool:
        query = f"SELECT * FROM clients WHERE tg_id = {tg_id};"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            return True
        return False

    def clients_exist(self) -> bool:
        query = f"SELECT id FROM clients;"
        self.curr.execute(query)
        result = self.curr.fetchall()
        return result != []

    def write_sent_message_info(self, tg_id: int, message_id: int):
        query = f"INSERT INTO sent_messages (tg_id, message_id, sending_datetime) VALUES({tg_id}, {message_id}, NOW()::TIMESTAMP);"
        self.curr.execute(query)
        self.connection.commit()

    def get_last_sent_messages(self, latest_one=False):
        if latest_one:
            query = "SELECT clients.tg_id, message_id, name, surname, phone_number, sending_datetime " + \
                    "FROM sent_messages JOIN clients ON sent_messages.tg_id = clients.tg_id ORDER BY sending_datetime DESC LIMIT 1;"
        else:
            query = "SELECT clients.tg_id, message_id, name, surname, phone_number FROM sent_messages JOIN clients " + \
                    "ON sent_messages.tg_id = clients.tg_id WHERE sending_datetime >= NOW()::TIMESTAMP - INTERVAL '48 HOUR';"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            result = list(map(lambda x: list(x), result))
            if latest_one:
                return result[0]
            # из каждого чата берется только последнее сообщение даже если найдено несколько
            formatted_result = []
            people_already_taken = dict()
            for message in result:
                if message[0] not in people_already_taken:
                    people_already_taken[message[0]] = message[1]
                    formatted_result.append(message)
                elif message[1] > people_already_taken[message[0]]:
                    for item in formatted_result:
                        if item[0] == message[0]:
                            item[1] = message[1]
            return formatted_result
        else:
            return None

    def delete_sent_message_info(self, tg_id: int, message_id: int):
        query = f"DELETE FROM sent_messages WHERE tg_id = {tg_id} AND message_id = {message_id};"
        self.curr.execute(query)
        self.connection.commit()

    @staticmethod
    def __normalize_phone_number(phone_number: str) -> str:
        for char in phone_number:
            if not char.isdigit():
                phone_number = phone_number.replace(char, '')
        if phone_number[0] == '7':
            phone_number = '8' + phone_number[1:]
        return phone_number

    def write_payments_data(self, payments_file_path: str):
        try:
            df = pd.read_excel(payments_file_path, header=None)
            shift_date = datetime.strptime(payments_file_path[payments_file_path.find('/') + 1:payments_file_path.rfind('.')], '%d%m%y').date()
            people = df.iloc[:3, 4:].copy()
            people = people.dropna(axis='columns', how='all')
            if people.empty:
                error_log = 'Нет ни людей, ни телефонов 😔'
                return error_log
            people_without_phone_numbers, people_without_banks, incorrect_phone_numbers = [], [], []
            for i in range(people.shape[1]):
                if type(people.iloc[0, i]) is float:
                    people_without_phone_numbers.append(people.iloc[2, i])
                if type(people.iloc[1, i]) is float:
                    people_without_banks.append(people.iloc[2, i])
                phone_number = str(people.iloc[0, i])
                digits_amount = sum(1 for i in phone_number if i.isdigit())
                if digits_amount != 11:
                    incorrect_phone_numbers.append('"' + phone_number + '"')
            if people_without_phone_numbers:
                if len(people_without_phone_numbers) == 1:
                    return f'Нет номера телефона у сотрудника по имени {people_without_phone_numbers[0]}'
                else:
                    return f"Нет номеров телефона у следующих сотрудников: {', '.join(people_without_phone_numbers)}"
            if people_without_banks:
                if len(people_without_banks) == 1:
                    return f'Нет названия банка у сотрудника по имени {people_without_banks[0]}'
                else:
                    return f"Нет названия банка у следующих сотрудников: {', '.join(people_without_banks)}"
            if incorrect_phone_numbers:
                if len(incorrect_phone_numbers) == 1:
                    return f"Некорректный номер телефона: {incorrect_phone_numbers[0]}"
                else:
                    return f"Некорректные номера телефонов: {', '.join(incorrect_phone_numbers)}"

            employee_ids = []
            act_numbers = []
            for i in list(people.columns):
                phone_number = self.__normalize_phone_number(str(people[i][0]))
                bank = people[i][1]
                first_last_name = people[i][2]
                if not self.__employee_exists(phone_number, employee_ids):
                    query = f"INSERT INTO employees (first_last_name, phone_number, bank) VALUES('{first_last_name}', '{phone_number}', '{bank}') RETURNING id;"
                    self.curr.execute(query)
                    employee_ids.append(self.curr.fetchall()[0][0])
                query = f"SELECT MAX(act_number) FROM shifts WHERE employee_id = {employee_ids[-1]} AND date = '{str(shift_date)}';"
                self.curr.execute(query)
                result = self.curr.fetchall()[0][0]
                if result:
                    act_numbers.append(result + 1)
                else:
                    act_numbers.append(1)

            goods = df.iloc[4:, :4 + len(employee_ids)].copy()
            for i in range(4, 4 + len(employee_ids)):
                goods[i] = goods[i].fillna(0)
            for row in range(goods.shape[0]):
                good_info = list(goods.iloc[row, :][0:3])
                if type(good_info[0]) is float and type(good_info[1]) is float and type(good_info[2]) is float:
                    break
                product_barcode = str(good_info[0]) if good_info[0] else ''
                product_name = str(good_info[2])
                tariff_price = float(good_info[1])
                for i in range(len(employee_ids)):
                    amount = float(goods.iloc[row, 4 + i])
                    if amount > 0:
                        query = f"INSERT INTO shifts (employee_id, product_barcode, product_name, tariff_price, amount, date, act_number) " + \
                                f"VALUES({employee_ids[i]}, '{product_barcode}', '{product_name}', {tariff_price}, {amount}, '{shift_date}', {act_numbers[i]});"
                        self.curr.execute(query)

            self.connection.commit()
            return ''
        except Exception as e:
            return str(e)

    def __employee_exists(self, phone_number: str, employee_ids: list) -> bool:
        query = f"SELECT id FROM employees WHERE phone_number = '{phone_number}';"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            employee_ids.append(result[0][0])
            return True
        return False

    def get_all_shifts(self):
        query = "SELECT date, first_last_name, phone_number, product_barcode, product_name, tariff_price, amount, act_number, was_paid " + \
                "FROM shifts, employees e WHERE employee_id = e.id ORDER BY date, first_last_name;"
        self.curr.execute(query)
        result = self.curr.fetchall()
        if result:
            result = list(map(lambda x: list(x), result))
        else:
            result = None
        return result

    def get_unpaid_shifts_by_dates(self):
        query = "SELECT date, first_last_name, SUM(tariff_price * amount), act_number FROM shifts, employees e " + \
                "WHERE employee_id = e.id AND was_paid = FALSE GROUP BY first_last_name, date, act_number ORDER BY date, first_last_name;"
        self.curr.execute(query)
        debts = self.curr.fetchall()
        total_debt = 0
        if debts:
            result = {}
            '''
            {
                date1: [
                    {
                        "person": first_last_name + <номер акта если их больше 1>,
                        "debt": tariff_price * amount
                    },
                    {
                        "person": ...,
                        "debt": ...
                    }
                ]
                date2: ...
            }
            '''
            for debt in debts:
                debt = list(debt)
                total_debt += debt[2]
                if debt[0] not in result:
                    result[debt[0]] = []
                if debt[3] == 1:
                    result[debt[0]].append({'person': debt[1], 'debt': round(debt[2], 2)})
                else:
                    if debt[3] == 2:
                        result[debt[0]] = [{'person': f"{x['person']} (1 акт)", 'debt': x['debt']} if x['person'] == debt[1] else x for x in result[debt[0]]]
                    result[debt[0]].append({'person': f'{debt[1]} ({debt[3]} акт)', 'debt': round(debt[2], 2)})
        else:
            result = None
        return result, total_debt

    def get_next_payment_by_dates(self, offset=0):
        query = "SELECT date, first_last_name, act_number, SUM(tariff_price * amount) FROM shifts, employees e " + \
                "WHERE employee_id = e.id AND was_paid = FALSE GROUP BY first_last_name, date, act_number " + \
                f"ORDER BY date, first_last_name, act_number OFFSET {offset} LIMIT 1;"
        self.curr.execute(query)
        general_info = self.curr.fetchall()
        if general_info:
            general_info = list(general_info[0])
            general_info[3] = round(general_info[3], 2)
        else:
            return None, None

        query = "SELECT phone_number, bank, product_barcode, product_name, tariff_price, amount FROM shifts " + \
                "JOIN employees e ON employee_id = e.id " + \
                f"WHERE date = '{general_info[0]}' AND first_last_name = '{general_info[1]}' AND act_number = {general_info[2]};"
        self.curr.execute(query)
        specific_info = self.curr.fetchall()
        general_info.insert(3, specific_info[0][1])
        general_info.insert(2, specific_info[0][0])
        specific_info = list(map(lambda x: list(x[2:]), specific_info))
        return general_info, specific_info

    def get_next_payment_by_people(self, offset=0):
        query = "SELECT DISTINCT employee_id, date FROM shifts WHERE was_paid = FALSE ORDER BY date;"
        self.curr.execute(query)
        people_ids = self.curr.fetchall()
        if people_ids:
            people_ids = list(map(lambda x: list(x), people_ids))
        else:
            return None, None, None
        seen = set()
        people_ids_unique = [x for x in people_ids if not (x[0] in seen or seen.add(x[0]))]
        if offset >= len(people_ids_unique):
            return None, None, None
        person_id = people_ids_unique[offset][0]
        query = f"SELECT id, first_last_name, phone_number, bank FROM employees WHERE id = {person_id};"
        self.curr.execute(query)
        person_info = self.curr.fetchall()
        person_info = list(person_info[0])

        query = f"SELECT DISTINCT date, act_number FROM shifts WHERE employee_id = {person_id} AND was_paid = FALSE ORDER BY date, act_number;"
        self.curr.execute(query)
        person_shifts = self.curr.fetchall()
        shifts_info = {}
        '''
        {
            date1: {
                act1: [[product_barcode, product_name, tariff_price, amount], [product_barcode, product_name, tariff_price, amount], ...]
                act2: ...
            },
            date2: ...
        }
        '''
        total_debt = 0
        for person_shift in person_shifts:
            if person_shift[0] not in shifts_info:
                shifts_info[person_shift[0]] = {}
            shifts_info[person_shift[0]][person_shift[1]] = []
            current_date_act = shifts_info[person_shift[0]][person_shift[1]]
            query = f"SELECT product_barcode, product_name, tariff_price, amount FROM shifts WHERE employee_id = {person_id} AND date = '{person_shift[0]}' AND act_number = {person_shift[1]};"
            self.curr.execute(query)
            packages = self.curr.fetchall()
            if packages:
                packages = list(map(lambda x: list(x), packages))
                for package_info in packages:
                    total_debt += package_info[2] * package_info[3]
                    current_date_act.append(package_info)
            else:
                current_date_act.append(None)
        person_info.append(total_debt)
        return person_info, shifts_info, len(people_ids_unique) - 1

    def mark_shift_as_paid__aggregation_by_dates(self, shift_date: date, phone_number: str, act_number: int):
        query = f"UPDATE shifts SET was_paid = TRUE WHERE date = '{shift_date}' AND act_number = {act_number} AND " + \
                f"employee_id = (SELECT DISTINCT employee_id FROM shifts JOIN employees e ON employee_id = e.id WHERE phone_number = '{phone_number}');"
        self.curr.execute(query)
        self.connection.commit()

    def mark_shift_as_paid__aggregation_by_people(self, employee_id: int):
        query = f"UPDATE shifts SET was_paid = TRUE WHERE employee_id = {employee_id};"
        self.curr.execute(query)
        self.connection.commit()