#!/usr/bin/env python3
import os
import inspect
import logging
import argparse
import sys
import math
import time
import getpass
import pandas as pd
import numpy as np
from app.logger import logger
from app.xiq_api import XIQ
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
logger = logging.getLogger('Serial_Onboard.Main')
# Set the option to opt-in to the future behavior
pd.set_option('future.no_silent_downcasting', True)

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
            print("\nWhich VIQ would you like to import the floor plan and APs too?")
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

# Read the CSV file
try:
    csv_df = pd.read_csv(filename, dtype=str)
except FileNotFoundError:
    sys.stdout.write(RED)
    print(f"File {filename} was not found.")
    print("script is exiting...")
    sys.stdout.write(RESET)
    raise SystemExit

# Replace blank strings with NaN in 'serialnumber' and 'floor_id'
csv_df[['serialnumber', 'floor_id', 'network_policy']] = csv_df[['serialnumber', 'floor_id', 'network_policy']].apply(lambda x: x.str.strip()).replace('', np.nan)

# allows for partial completions. Any Device that was checked and csv updated on columm 'xiq_status' will be skipped
if 'xiq_status' not in csv_df.columns:
    # if xiq_status column does not exist, the column will be created with every device having a NaN value
    csv_df['xiq_status'] = None
    new_filename = 'new_' + filename
else:
    new_filename = filename



# Check for duplicates in the CSV
duplicateSN = csv_df['serialnumber'].dropna().duplicated().any()
if duplicateSN:
    log_msg = ("Multiple APs have the same serial numbers in the CSV file. Please fix and try again.")
    logger.warning(log_msg)
    sys.stdout.write(RED)
    sys.stdout.write('\n' + log_msg + '\n')
    sys.stdout.write("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit


# Check for rows on CSV file that are missing serial numbers
nanValues = csv_df[csv_df['serialnumber'].isna()]

# Check for rows that have a status in xiq_status
new_csv_df = csv_df[csv_df['xiq_status'].isna() & csv_df['serialnumber'].notna()]

if new_csv_df.serialnumber.size == 0:
    log_msg = ("All serial numbers in the CSV file have a status in 'xiq_status'.")
    logger.info(log_msg)
    sys.stdout.write(YELLOW)
    sys.stdout.write("\n"+log_msg + '\n')
    print("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit
else:
    print(f"\n{csv_df.serialnumber.size - new_csv_df.serialnumber.size} APs were found with a xiq_status in the CSV file")


listOfSN = list(new_csv_df['serialnumber'].dropna().unique())

if nanValues.serialnumber.size > 0 and len(listOfSN) == 0:
    log_msg = ("Serial numbers were not found for any AP in the CSV. Please check to make sure they are added correctly and try again.")
    logger.warning(log_msg)
    sys.stdout.write(YELLOW)
    sys.stdout.write("\n"+log_msg + '\n')
    print("script is exiting....")
    sys.stdout.write(RESET)
    raise SystemExit
elif nanValues.serialnumber.size > 0:
    totalFailed += nanValues.serialnumber.size
    sys.stdout.write(YELLOW)
    sys.stdout.write("\nSerial numbers were not found for these APs. Please correct and run the script again if you would like to add them.\n  ")
    sys.stdout.write(RESET)
    print(*nanValues.hostname.values, sep = "\n  ")
    print()
    logger.info("Serial numbers were not found for these APs: " + ",".join(nanValues.hostname.values))

# Check for remaining rows on CSV file that are missing location_id
missingFloor = new_csv_df[new_csv_df['floor_id'].isna()]
if missingFloor.size > 0:
    sys.stdout.write(YELLOW)
    sys.stdout.write("\nFloor ids were not found for these APs. Please correct and run the script again if you would like to add them. They will be skipped this run.\n  ")
    sys.stdout.write(RESET)
    print(*missingFloor.hostname.values, sep = "\n  ")

new_csv_df = new_csv_df.drop(missingFloor.index)

#new_csv_df
onboard_list = []
for row, ap_info in new_csv_df.iterrows():
    data = {
        "serial_number": ap_info['serialnumber'],
        "location" : {
            "location_id": ap_info['floor_id']
        },
        "hostname": ap_info['hostname']
    }
    if pd.notna(ap_info['network_policy']):
        data['network_policy_id'] = ap_info["network_policy"]
    onboard_list.append(data)

# Check number of APs onboarding
if len(onboard_list) > 30:
    sys.stdout.write(GREEN)
    print("\nWith more the 30 APs onboarding, Long-running operation will be used.")
    sys.stdout.write(RESET)
    payload = {"extreme": onboard_list,
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
    payload = {"extreme": onboard_list,
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
        filt = csv_df['serialnumber'] == device['serial_number']
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
            filt = csv_df['serialnumber'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Exists'
            sys.stdout.write(YELLOW)
            print("\nThe following AP are already onboard in this XIQ instance:\n  ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These AP serial numbers are already onboarded in this XIQ instance: " + ",".join(serials))
            #response = yesNoLoop("Would you like to move these existing APs to the floorplan?")
        elif error == 'EXIST_IN_REDIRECT':
            totalFailed += len(serials)
            filt = csv_df['serialnumber'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Exists in different XIQ'
            sys.stdout.write(YELLOW)
            print("\nTThese AP serial numbers were not able to be onboarded at this time as the serial numbers belong to another XIQ instance. Please check the serial numbers and try again:\n  ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These AP serial numbers are already onboarded in this XIQ instance: " + ",".join(serials))
        elif error == 'PRODUCT_TYPE_NOT_EXIST':
            totalFailed += len(serials)
            filt = csv_df['serialnumber'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = 'Serial number not valid'
            sys.stdout.write(RED)
            print("\nThese AP serial numbers are not valid. Please check serial numbers and try again:\n ", end='')
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning("These AP serial numbers are not valid: " + ",".join(serials))
        else:
            totalFailed += len(serials)
            filt = csv_df['serialnumber'].isin(serials)
            csv_df.loc[filt, "xiq_status"] = error
            sys.stdout.write(RED)
            print(f"\nThese AP serial numbers failed to onboard with the error '{error}':")
            print(*serials, sep='\n  ')
            sys.stdout.write(RESET)
            logger.warning(f"These AP serial numbers failed to onboard with '{error}': " + ",".join(serials)) 


csv_df.to_csv(current_dir +'/'+new_filename,index=False)

print("\nCounts for this run:")
print(f"    totalExisting = {totalExisting}")
print(f"    totalOnboard = {totalOnboard}")
print(f"    totalFailed = {totalFailed}")
logger.info(f"Counts for completed run: totalExisting= {totalExisting}, totalOnboard = {totalOnboard}, totalFailed = {totalFailed}")


