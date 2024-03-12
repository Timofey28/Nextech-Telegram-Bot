from abc import ABC, abstractmethod
from database import Database
from data import db_dbname, db_host, db_user, db_password


class DebtDisplayStrategy(ABC):
    def __init__(self):
        self.db = Database(db_dbname=db_dbname,
                           db_host=db_host,
                           db_user=db_user,
                           db_password=db_password)
        self.very_small_number = 1e-9

    @abstractmethod
    def get_unpaid_shifts_message(self) -> str:
        pass

    @abstractmethod
    def get_next_payment_message(self, offset=0) -> [str, dict]:
        pass

    @staticmethod
    def prettify_phone_number(phone_number: str) -> str:
        assert len(phone_number) >= 9
        phone_number = phone_number[:1] + ' (' + phone_number[1:4] + ') ' + phone_number[4:7] + '-' + phone_number[7:9] + '-' + phone_number[9:]
        return phone_number