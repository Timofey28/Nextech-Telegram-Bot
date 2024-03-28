import logging
import os
from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
)


class GlobalVars:
    def __init__(self):
        # Статусы
        self.Status_MAIN = 'main'
        self.Status_ENTERING_BUSINESS_DIRECTION = 'entering_business_direction'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE = 'pressing_business_direction'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT = 'pressing_business_direction_to_add_new_client'
        self.Status_ENTERING_CLIENTS_DATA = 'entering_clients_data'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE = 'pressing_business_direction_to_send_file'
        self.Status_PRESSING_CLIENT_TO_SEND_FILE = 'pressing_client_to_send_file'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT = 'pressing_business_direction_to_delete_client'
        self.Status_PRESSING_CLIENT_TO_DELETE_ONE = 'pressing_client_to_delete_one'
        self.Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE = 'pressing_client_to_delete_last_message'
        self.Status_PRESSING_BUTTON_WHILE_PAYING_SALARIES = 'pressing_button_while_paying_salaries'
        self.Status_PRESSING_BUTTON_TO_DECIDE_WHETHER_TO_PAY_SALARIES = 'pressing_button_to_decide_whether_to_pay_debts'
        self.Status_IN_SECTION_CLIENTS = 'in_section_clients'
        self.Status_IN_SECTION_CONTRACTS = 'in_section_contracts'
        self.Status_IN_SECTION_PAYMENTS = 'in_section_payments'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CLIENT = 'pressing_business_direction_to_edit_client'
        self.Status_PRESSING_CLIENT_TO_EDIT_ONE = 'pressing_client_to_edit_one'
        self.Status_EDITING_CLIENT = 'editing_client'
        self.Status_PRESSING_CONTRACT_TEMPLATE_TO_SEND_ONE = 'pressing_contract_template_to_send_one'
        self.Status_SENDING_NEW_CONTRACT_TEMPLATE = 'sending_new_contract_template'
        self.Status_PRESSING_CONTRACT_TEMPLATE_TO_DELETE_ONE = 'pressing_contract_template_to_delete_one'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CONTRACT = 'pressing_business_direction_to_add_new_contract'
        self.Status_PRESSING_CLIENT_TO_ADD_NEW_CONTRACT = 'pressing_client_to_add_new_contract'
        self.Status_ENTERING_CONTRACT_INFO_STAGE_1 = 'entering_contract_info_stage_1'
        self.Status_ENTERING_CONTRACT_INFO_STAGE_2 = 'entering_contract_info_stage_2'
        self.Status_ENTERING_CONTRACT_INFO_STAGE_3 = 'entering_contract_info_stage_3'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CONTRACT = 'pressing_business_direction_to_edit_contract'
        self.Status_PRESSING_CLIENT_TO_EDIT_CONTRACT = 'pressing_client_to_edit_contract'
        self.Status_CHOOSING_WHICH_CONTRACT_TO_EDIT = 'choosing_which_contract_to_edit'
        self.Status_CHOOSING_WHAT_IN_CONTRACT_TO_EDIT = 'choosing_what_in_contract_to_edit'
        self.Status_SENDING_UPDATED_CONTRACT = 'sending_updated_contract'
        self.Status_ENTERING_UPDATED_CONTRACT_PAYMENT_SCHEDULE = 'entering_updated_contract_payment_schedule'
        self.Status_ENTERING_PAID_PAYMENT_INFO = 'entering_paid_payment_info'
        self.Status_ADDING_PAID_PAYMENT_CONFIRMATION = 'adding_paid_payment_confirmation'
        self.Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_CONTRACT = 'pressing_business_direction_to_send_contract'
        self.Status_PRESSING_CLIENT_TO_SEND_CONTRACT = 'pressing_client_to_send_contract'
        self.Status_CHOOSING_WHICH_CONTRACT_TO_SEND = 'choosing_which_contract_to_send'

        self.ADMIN_GROUP_STATUS = self.Status_MAIN
        self.ACCOUNTANT_GROUP_STATUS = self.Status_MAIN
        self.ADMIN_GROUP_ID = 0
        self.ACCOUNTANT_GROUP_ID = 0
        self.read_group_ids()
        self.CALLBACK_DATA = {}
        self.CONTRACT_INFO = {}
        self.PAYMENT_INFO = {}
        self.CANCEL_BUTTON = [[KeyboardButton("отмена")]]
        self.PAY_SALARIES_INLINE_KEYBOARD = [[InlineKeyboardButton("Отмена ❌", callback_data="отмена"),
                                              InlineKeyboardButton("Пропустить ⏩️", callback_data="пропустить")],
                                             [InlineKeyboardButton("Оплачено! ✅", callback_data="оплачено")]]
        self.CURRENT_FILE = ''
        self.CURRENT_OFFSET = 0
        self.CURRENT_DEBT = {}

        # Константы
        self.PATH_CONCTRACT_TEMPLATES = 'Contract_templates'
        self.PATH_CONTRACTS = 'Contracts'

    def set_group_status(self, group: str, status: str):
        assert group == 'accountant'
        if group == 'accountant':
            if not (status == self.Status_MAIN or
                    status == self.Status_ENTERING_BUSINESS_DIRECTION or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_ONE or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CLIENT or
                    status == self.Status_ENTERING_CLIENTS_DATA or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_FILE or
                    status == self.Status_PRESSING_CLIENT_TO_SEND_FILE or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_DELETE_CLIENT or
                    status == self.Status_PRESSING_CLIENT_TO_DELETE_ONE or
                    status == self.Status_PRESSING_CLIENT_TO_DELETE_LAST_MESSAGE or
                    status == self.Status_PRESSING_BUTTON_WHILE_PAYING_SALARIES or
                    status == self.Status_PRESSING_BUTTON_TO_DECIDE_WHETHER_TO_PAY_SALARIES or
                    status == self.Status_IN_SECTION_CLIENTS or
                    status == self.Status_IN_SECTION_CONTRACTS or
                    status == self.Status_IN_SECTION_PAYMENTS or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CLIENT or
                    status == self.Status_PRESSING_CLIENT_TO_EDIT_ONE or
                    status == self.Status_EDITING_CLIENT or
                    status == self.Status_PRESSING_CONTRACT_TEMPLATE_TO_SEND_ONE or
                    status == self.Status_SENDING_NEW_CONTRACT_TEMPLATE or
                    status == self.Status_PRESSING_CONTRACT_TEMPLATE_TO_DELETE_ONE or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_ADD_NEW_CONTRACT or
                    status == self.Status_PRESSING_CLIENT_TO_ADD_NEW_CONTRACT or
                    status == self.Status_ENTERING_CONTRACT_INFO_STAGE_1 or
                    status == self.Status_ENTERING_CONTRACT_INFO_STAGE_2 or
                    status == self.Status_ENTERING_CONTRACT_INFO_STAGE_3 or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_EDIT_CONTRACT or
                    status == self.Status_PRESSING_CLIENT_TO_EDIT_CONTRACT or
                    status == self.Status_CHOOSING_WHICH_CONTRACT_TO_EDIT or
                    status == self.Status_CHOOSING_WHAT_IN_CONTRACT_TO_EDIT or
                    status == self.Status_SENDING_UPDATED_CONTRACT or
                    status == self.Status_ENTERING_UPDATED_CONTRACT_PAYMENT_SCHEDULE or
                    status == self.Status_ENTERING_PAID_PAYMENT_INFO or
                    status == self.Status_ADDING_PAID_PAYMENT_CONFIRMATION or
                    status == self.Status_PRESSING_BUSINESS_DIRECTION_TO_SEND_CONTRACT or
                    status == self.Status_PRESSING_CLIENT_TO_SEND_CONTRACT or
                    status == self.Status_CHOOSING_WHICH_CONTRACT_TO_SEND):
                logging.error(f'Unknown status was encountered: "{status}"')
            self.ACCOUNTANT_GROUP_STATUS = status

    def read_group_ids(self):
        if os.path.exists("admin_group_id.txt"):
            with open("admin_group_id.txt") as file:
                self.ADMIN_GROUP_ID = int(file.read())
        if os.path.exists("accountant_group_id.txt"):
            with open("accountant_group_id.txt") as file:
                self.ACCOUNTANT_GROUP_ID = int(file.read())