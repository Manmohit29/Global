import time
import sys
import os
import logging
from pyModbusTCP.client import ModbusClient
from logging.handlers import TimedRotatingFileHandler
import datetime
from csv_func import write_payload
import re

if getattr(sys, 'frozen', False):
    dirname = os.path.dirname(sys.executable)
else:
    dirname = os.path.dirname(os.path.abspath(__file__))

log_level = logging.INFO

FORMAT = '%(asctime)-15s %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s'

logFormatter = logging.Formatter(FORMAT)
log = logging.getLogger()

# checking and creating logs directory here
if not os.path.isdir("./logs"):
    log.info("[-] logs directory doesn't exists")
    try:
        os.mkdir("./logs")
        log.info("[+] Created logs dir successfully")
    except Exception as e:
        log.error(f"[-] Can't create dir logs Error: {e}")

fileHandler = TimedRotatingFileHandler(os.path.join(dirname, f'logs/app_log'),
                                       when='midnight', interval=1)
fileHandler.setFormatter(logFormatter)
fileHandler.suffix = "%Y-%m-%d.log"
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)
log.setLevel(log_level)


def convert_registers_to_ascii(registers):
    try:
        ascii_string = ''
        for value in registers:
            low_byte = value & 0xFF
            high_byte = (value >> 8) & 0xFF
            ascii_string += chr(low_byte) + chr(high_byte)
        return ascii_string
    except Exception as e:
        log.error(f"Error in changing into ascii: {e}")
        return None


# PLC IP address and port number
plc_ip = '192.168.11.194'
plc_port = 502

# this check is used to save file one time only even if trigger didn't reset
SAVE = False
# address range for holding registers
registers = {
    "barcode": [1000, 35],
    "model_no": [1035, 5],
    "parameters": [1040, 8],
}

parameters_status = {
    "ScreenSheet": "",
    "ORing": "",
    "SnapRing": "",
    "GrandRing": "",
    "Groove": "",
    "Spline 1": "",
    "Spline 2": "",
    "OverAll": ""
}

def read_data(addr, length):
    # log.info(f"READING {addr} for {length}")
    client = ModbusClient(host=plc_ip, port=plc_port, unit_id=1, auto_open=True, auto_close=True, timeout=5)
    for i in range(10):
        data = client.read_holding_registers(addr, length)
        if data is not None:
            return data
    client.close()
    return None


def reset_trigger():
    client = ModbusClient(host=plc_ip, port=plc_port, unit_id=1, auto_open=True, auto_close=True, timeout=5)
    client.write_single_register(732, 1)
    log.info(f"Resetted trigger")
    client.close()


# Connect to the PLC
while True:
    try:

        # if client.open():
        #     log.info("Connected to PLC")
        #
        #     # Read holding registers from the PLC
        try:
            barcode_data = read_data(registers['barcode'][0], registers['barcode'][1])
            log.info(barcode_data)

            model_no = read_data(registers['model_no'][0], registers['model_no'][1])
            log.info(model_no)

            parameters = read_data(registers['parameters'][0], registers['parameters'][1])
            log.info(f"parameters : {parameters}")

            model_suffix = read_data(1048, 2)
            log.info(f"Model prefix: {model_suffix}")

            # screen_sheet = client.read_holding_registers(211, 1)
            # if screen_sheet is None:
            #     raise Exception("Failed to read screen sheet")
            # log.info(f"Screen sheet : {screen_sheet}")

            trigger = read_data(730, 1)
            log.info(f"Trigger : {trigger}")
            if trigger[0] == 0:
                SAVE = False
        except Exception as e:
            log.error(f"Error while reading data from plc: {e}")
            barcode_data = None

        try:
            if barcode_data:
                barcode_data = convert_registers_to_ascii(barcode_data)
                real_barcode_data = re.sub(r'\x00.*', '', barcode_data)
                # real_barcode_data = barcode_data.replace("\x00", "")
            else:
                real_barcode_data = None

        except Exception as e:
            log.error(f"Error while replacing x00 from the barcode: {e}")
            real_barcode_data = None

        if real_barcode_data:
            try:
                prefix = "".join(chr(value) for value in model_suffix)
                model_no_data = prefix + "".join([chr(value) for value in model_no])
                real_model_no = model_no_data.replace("\x00", "")
            except Exception as e:
                log.error(f"Error in changing model number: {e}")
                real_model_no = None

            log.info(f"barcode String: {real_barcode_data}")
            log.info(f"model_no String:  {real_model_no}")
            log.info(f"parameters String: {parameters}")

            for i, j in zip(parameters_status, parameters):
                if i == "OverAll":
                    if j == 1:
                        parameters_status[i] = "PASS"
                    elif j == 2:
                        parameters_status[i] = "FAIL"
                elif j == 1:
                    parameters_status[i] = "PRESENT"
                elif j == 2:
                    parameters_status[i] = "NOT PRESENT"
                else:
                    parameters_status[i] = "NOT PRESENT"

            today = datetime.datetime.now().strftime('%Y-%m-%d')
            time_ = datetime.datetime.now().strftime("%H:%M:%S")
            # if screen_sheet == [1]:
            #     screen_sheet_status = "PRESENT"
            # elif screen_sheet == [2]:
            #     screen_sheet_status = "NOT PRESENT"
            # else:
            #     screen_sheet_status = "NOT PRESENT"

            data = {
                "date": today,
                "time": time_,
                "Barcode_No": real_barcode_data,
                "ModelNo": real_model_no,
                "ScreenSheet": parameters_status["ScreenSheet"],
                "ORing": parameters_status["ORing"],
                "SnapRing": parameters_status["SnapRing"],
                "GrandRing": parameters_status["GrandRing"],
                "Groove": parameters_status["Groove"],
                "Spline_1": parameters_status["Spline 1"],
                "Spline_2": parameters_status["Spline 2"],
                "OverAll": parameters_status["OverAll"]
            }
            log.info(f"data : {data}")
            if real_model_no and parameters[1] != 0:
                if trigger[0] and not SAVE:
                    SAVE = True
                    write_payload(data)
                else:
                    log.info(f"Data didn't save because trigger is {trigger[0]} and save status is {SAVE}")

                if SAVE:
                    reset_trigger()

        else:
            log.info(f"Barcode data is not available : {barcode_data}")
        time.sleep(1)
    except Exception as e:
        log.error(f"Error : {e}")
        time.sleep(1)
