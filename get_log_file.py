import pysftp
from data import my_Hostname, my_Username, my_Password

try:
    with pysftp.Connection(host=my_Hostname, username=my_Username, password=my_Password) as sftp:
        print("Connection succesfully established ... ")
        sftp.get('/root/Nextech-Telegram-Bot/info.log', 'info.log')
    print("*** Файл на базе! ***")
except Exception as e:
    print(str(e))