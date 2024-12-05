import csv
import datetime
import os
import logging

log = logging.getLogger()


def get_global_folder():
    # Get the path to the specified folder
    global_folder = "D:\\Global"

    # Create the folder if it doesn't exist
    if not os.path.exists(global_folder):
        os.makedirs(global_folder)

    return global_folder


def get_filename():
    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    global_folder = get_global_folder()
    return os.path.join(global_folder, f"data_{today}.csv")


def entry_exists(data, filename):
    try:
        if not os.path.isfile(filename):
            return False
        with open(filename, mode='r', newline='') as csvfile:
            reader = list(csv.DictReader(csvfile))
            for row in reversed(reader):
                if row['Barcode_No'] == data['Barcode_No']:
                    log.info(f"Matching Barcode_No found: {data['Barcode_No']}")
                    log.info("Columns in CSV row:")
                    for key in data:
                        if key not in ['time', 'date']:  # Skip the 'time' and 'date' columns in comparison
                            log.info(f"{key}: CSV Value: {row[key]}, Data Value: {data[key]}")
                    if all(key in ['time', 'date'] or row[key] == str(data[key]) for key in data):
                        log.info(f"Entry exists with same values (excluding time and date): True")
                        return True
                    else:
                        log.info(f"Barcode {data['Barcode_No']} exists with different values.")
                        return False
        log.info(f"Entry exists with same values (excluding time and date): False")
        return False
    except Exception as e:
        log.error(f"Error while checking if barcode entry is unique or not: {e}")
        return None


def write_payload(data):
    filename = get_filename()

    # if entry_exists(data, filename):
    #     barcode = data["Barcode_No"]
    #     log.info(f"Entry for barcode {barcode} with same values already exists. Skipping.")
    #     return

    try:
        with open(filename, 'a+', newline='') as csvfile:
            fieldnames = [fields for fields in data]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(data)
        log.info(f"Data written to {filename} successfully.")
    except Exception as e:
        log.error(f"Error in adding data into csv file: {e}")

