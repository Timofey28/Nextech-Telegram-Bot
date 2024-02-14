import psycopg2

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

    def add_client(self, surname: str, name: str, patronymic: str, sex: str, tg_id: int, inn: str, business_direction_id: int, phone_number: str, email: str) -> bool:
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