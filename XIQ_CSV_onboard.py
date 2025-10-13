#!/usr/bin/env python3
import os
import inspect
import logging
import argparse
import sys
import time
import getpass
import pandas as pd
import numpy as np
from app.logger import logger
from app.xiq_api import XIQ

# Opt-in to future Pandas behavior (avoids warning)
pd.set_option('future.no_silent_downcasting', True)

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
logger = logging.getLogger('Serial_Onboard.Main')

XIQ_API_token = ''

pageSize = 100

parser = argparse.ArgumentParser()
parser.add_argument('--external',action="store_true", help="Optional - adds External Account selection, to use an external VIQ")
args = parser.parse_args()

PATH = current_dir

# Git Shell Coloring - https://gist.github.com/vratiu/9780109
RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
RESET = "\033[0;0m"


totalExisting = 0
totalOnboard = 0 
totalFailed = 0

def _create_char_spinner():
    """Creates a generator yielding a char based spinner.
    """
    while True:
        for character in '|/-\\':
            yield character

_spinner = _create_char_spinner()

def spinner(label=''):
    """Prints label with a spinner.

    When called repeatedly from inside a loop this prints
    a one line CLI spinner.
    """
    sys.stdout.write("\r%s %s  " % (label, next(_spinner)))
    sys.stdout.flush()

## XIQ API Setup
if XIQ_API_token:
    x = XIQ(token=XIQ_API_token)
else:
    print("Enter your XIQ login credentials")
    username = input("Email: ")
    password = getpass.getpass("Password: ")
    x = XIQ(user_name=username,password = password)
#OPTIONAL - use externally managed XIQ account
if args.external:
    accounts, viqName = x.selectManagedAccount()
    if accounts == 1:
        validResponse = False
        while validResponse != True:
            response = input("No External accounts found. Would you like to import data to your network?")
            if response == 'y':
                validResponse = True
            elif response =='n':
                sys.stdout.write(RED)
                sys.stdout.write("script is exiting....\n")
                sys.stdout.write(RESET)
                raise SystemExit
    elif accounts:
        validResponse = False
        while validResponse != True:
            print("\nWhich VIQ would you like to import the Devices too?")
            accounts_df = pd.DataFrame(accounts)
            count = 0
            for df_id, viq_info in accounts_df.iterrows():
                print(f"   {df_id}. {viq_info['name']}")
                count = df_id
            print(f"   {count+1}. {viqName} (This is Your main account)\n")
            selection = input(f"Please enter 0 - {count+1}: ")
            try:
                selection = int(selection)
            except:
                sys.stdout.write(YELLOW)
                sys.stdout.write("Please enter a valid response!!")
                sys.stdout.write(RESET)
                continue
            if 0 <= selection <= count+1:
                validResponse = True
                if selection != count+1:
                    newViqID = (accounts_df.loc[int(selection),'id'])
                    newViqName = (accounts_df.loc[int(selection),'name'])
                    x.switchAccount(newViqID, newViqName)



print("Make sure the csv file is in the same folder as the python script.")
filename = input("Please enter csv filename: ")
filename = filename.replace("\\ ", " ")
filename = filename.replace("'", "")

# Check if full path (e.g., from drag-and-drop) and extract basename if needed
if os.path.isabs(filename):
    base_filename = os.path.basename(filename)  # e.g., 'myfile.csv' from '/path/to/myfile.csv'
    print(f"Detected full path: {filename}")
    print(f"Using basename: {base_filename}")
else:
    base_filename = filename  # Use as-is if relative/no path

# Read the CSV file
try:
    csv_df = pd.read_csv(filename, dtype=str)
except FileNotFoundError:
    sys.stdout.write(RED)
    print(f"File {filename} was not found.")
    print("script is exiting...")
    sys.stdout.write(RESET)
    raise SystemExit

# check if columns exist
columns_to_check = ['Serial Number', 'Host Name', 'Device Type', 'Floor Id', 'Network Policy Id']
missing_columns = []
for column in columns_to_check:
    if column not in csv_df.columns:
        missing_columns.append(column)
if missing_columns:
    log_msg = "The following columns are missing from the csv file: " + ", ".join(missing_columns)
    logger.error(log_msg)
    print(log_msg)
    print("the script cannot continue.")
    raise SystemExit

# Replace blank strings with NaN in 'Serial Number' and 'floor_id'
csv_df[['Serial Number', 'Host Name', 'Device Type', 'Floor Id', 'Network Policy Id']] = csv_df[['Serial Number', 'Host Name', 'Device Type', 'Floor Id', 'Network Policy Id']].apply(lambda x: x.str.strip()).replace('', np.nan)
csv_df[['Host Name']] = csv_df[['Host Name']].replace(np.nan, '')
# allows for partial completions. Any Device that was checked and csv updated on column 'xiq_status' will be skipped
if 'xiq_status' not in csv_df.columns:
    # if xiq_status column does not exist, the column will be created with every device having a NaN value
    csv_df['xiq_status'] = None
    new_filename = 'new_' + base_filename
else:
    new_filename = base_filename



# Check for duplicates in the CSV
duplicateSN = csv_df['Serial Number'].dropna().duplicated().any()
if duplicateSN:
    log_msg = ("Multiple Devices have the same serial numbers in the CSV file. Please fix and try again.")
    logger.warning(log_msg)
    sys.stdout.write(RED)
    sys.stdout.write('\n' + log_msg + '\n')
    sys.stdout.write("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit


# Check for rows on CSV file that are missing serial numbers
nanValues = csv_df[csv_df['Serial Number'].isna()]

listOfSN = list(csv_df['Serial Number'].dropna().unique())

if nanValues.get('Serial Number', pd.Series()).size > 0 and len(listOfSN) == 0:
    log_msg = ("Serial numbers were not found for any Devices in the CSV. Please check to make sure they are added correctly and try again.")
    logger.warning(log_msg)
    sys.stdout.write(YELLOW)
    sys.stdout.write("\n"+log_msg + '\n')
    print("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit
elif nanValues.get('Serial Number', pd.Series()).size > 0:
    totalFailed += nanValues.get('Serial Number', pd.Series()).size
    sys.stdout.write(YELLOW)
    sys.stdout.write("\nSerial numbers were not found for these Devices. Please correct and run the script again if you would like to add them.\n  ")
    sys.stdout.write(RESET)
    print(*nanValues['Host Name'].values, sep = "\n  ")
    print()
    logger.info("Serial numbers were not found for these Devices: " + ",".join(nanValues['Host Name'].values))

# Check for rows that have a status in xiq_status
new_csv_df = csv_df[csv_df['xiq_status'].isna() & csv_df['Serial Number'].notna()]

if new_csv_df['Serial Number'].size == 0:
    log_msg = ("All serial numbers in the CSV file have a status in 'xiq_status'.")
    logger.info(log_msg)
    sys.stdout.write(YELLOW)
    sys.stdout.write("\n"+log_msg + '\n')
    print("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit
else:
    print(f"\n{csv_df['Serial Number'].size - nanValues.get('Serial Number', pd.Series()).size - new_csv_df['Serial Number'].size} Devices were found with a xiq_status in the CSV file")

# Check for remaining rows on CSV file that are missing location_id
missingFloor = new_csv_df[new_csv_df['Floor Id'].isna()]
if missingFloor.size > 0:
    sys.stdout.write(YELLOW)
    sys.stdout.write("\nFloor ids were not found for these Devices. Please correct and run the script again if you would like to add them. They will be skipped this run.\n  ")
    sys.stdout.write(RESET)
    print(*missingFloor['Host Name'].values, sep = "\n  ")
    logger.info("Floor ids were not found for these Devices: " + ",".join(missingFloor['Host Name'].values))

new_csv_df = new_csv_df.drop(missingFloor.index)


# Check for remaining rows on CSV file that are missing location_id
missingType = new_csv_df[new_csv_df['Device Type'].isna()]
if missingType.size > 0:
    sys.stdout.write(YELLOW)
    sys.stdout.write("\nDevice Type were not found for these Devices. Please correct and run the script again if you would like to add them. They will be skipped this run.\n  ")
    sys.stdout.write(RESET)
    print(*missingType['Host Name'].values, sep = "\n  ")
    logger.info("Device Type were not found for these Devices: " + ",".join(missingType['Host name'].values))
new_csv_df = new_csv_df.drop(missingType.index)

#new_csv_df
onboard_ap_list = [] 
onboard_exos_list = []
onboard_voss_list = []
for row, device_info in new_csv_df.iterrows():
    data = {
        "serial_number": device_info['Serial Number'],
        "location" : {
            "location_id": device_info['Floor Id']
        },
        "hostname": device_info['Host Name']
    }
    if pd.notna(device_info['Network Policy Id']):
        data['network_policy_id'] = device_info["Network Policy Id"]
    if device_info['Device Type'].upper() == 'AP':
        onboard_ap_list.append(data)
    elif device_info['Device Type'].upper() == 'EXOS':
        onboard_exos_list.append(data)
    elif device_info['Device Type'].upper() == 'VOSS':
        onboard_voss_list.append(data)
    else:
        sys.stdout.write(YELLOW)
        sys.stdout.write(f"\nDevice Type is invalid for {device_info['Serial Number']}. Please correct and run the script again if you would like to add it. It will be skipped this run.\n  ")
        sys.stdout.write(RESET)
        print(*missingType['Serial Number'].values, sep = "\n  ")
        logger.info("Device Type were not found for these Devices: " + ",".join(missingType['Serial Number'].values))

# Check number of Devices onboarding
device_count = len(onboard_ap_list) + len(onboard_exos_list) + len(onboard_voss_list)
if device_count > 30: 
    sys.stdout.write(GREEN)
    print("\nWith more the 30 Devices onboarding, Long-running operation will be used.")
    sys.stdout.write(RESET)
    payload = {"extreme": onboard_ap_list,
               "exos": onboard_exos_list,
               "voss": onboard_voss_list,
               "unmanaged": False
               }
    lro_url = x.advanceOnboardAPs(payload,lro=True)
    lro_result = 'PENDING'
    while lro_result != 'SUCCEEDED':
        data = x.checkLRO(lro_url)
        lro_result = data['metadata']['status']
        print(f"\nThe long running operation's result is {lro_result}")
        if lro_result != 'SUCCEEDED':
            print("Script will sleep for 30 secs and check again.")
            t = 120
            while t > 0:
                spinner()
                time.sleep(.25)
                t -= 1
            sys.stdout.write("\r  ")
            sys.stdout.flush()
    response = data['response']

else:
    payload = {"extreme": onboard_ap_list,
               "exos": onboard_exos_list,
               "voss": onboard_voss_list,
               "unmanaged": False
               }
    response = x.advanceOnboardAPs(payload)
    
# Log successes
if "success_devices" in response:
    sys.stdout.write(GREEN)
    print("\nThe following devices were onboarded successfully:")
    sys.stdout.write(RESET)
    for device in response['success_devices']:
        totalOnboard += 1
        filt = csv_df['Serial Number'] == device['serial_number']
        csv_df.loc[filt, "xiq_status"] = 'Onboarded'
        log_msg = f"Device {device['serial_number']} successfully onboarded created with id: {device['device_id']}"
        print(log_msg)
        logger.info(log_msg)

if "failure_devices" in response:
    fd_df = pd.DataFrame(response['failure_devices'])
    error_list = fd_df['error'].unique()
    for error in error_list:
        filt = fd_df['error'] == error
        serials = fd_df.loc[filt,'serial_number'].values
        if error == 'DEVICE_EXISTED':
            totalExisting += len(serials)
            filt = csv_df['Serial Number'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Exists'
            sys.stdout.write(YELLOW)
            print("\nThe following devices are already onboard to a XIQ instance:\n  ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These Device serial numbers are already onboarded to a XIQ instance: " + ",".join(serials))
        elif error == 'EXIST_IN_REDIRECT':
            totalFailed += len(serials)
            filt = csv_df['Serial Number'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Exists in different XIQ'
            sys.stdout.write(YELLOW)
            print("\nTThese Device serial numbers were not able to be onboarded at this time as the serial numbers belong to another XIQ instance. Please check the serial numbers and try again:\n  ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These Device serial numbers are already onboarded in this XIQ instance: " + ",".join(serials))
        elif error == 'PRODUCT_TYPE_NOT_EXIST':
            totalFailed += len(serials)
            filt = csv_df['Serial Number'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Serial number not valid'
            sys.stdout.write(RED)
            print("\nThese Device serial numbers are not valid. Please check serial numbers and try again:\n ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These Device serial numbers are not valid: " + ",".join(serials))
        else:
            totalFailed += len(serials)
            filt = csv_df['Serial Number'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = error
            sys.stdout.write(RED)
            print(f"\nThese Device serial numbers failed to onboard with the error '{error}':")
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning(f"These Device serial numbers failed to onboard with '{error}': " + ",".join(serials)) 


csv_df.to_csv(current_dir +'/'+new_filename,index=False)

print("\nCounts for this run:")
print(f"    totalExisting = {totalExisting}")
print(f"    totalOnboard = {totalOnboard}")
print(f"    totalFailed = {totalFailed}")
logger.info(f"Counts for completed run: totalExisting= {totalExisting}, totalOnboard = {totalOnboard}, totalFailed = {totalFailed}")


