# XIQ CSV Onboard
### XIQ_CSV_onboard.py
## Purpose
This script will onboard devices from a CSV file. the CSV file will need to have 5 columns with valid information. A column labeled ***'serialnumber'*** that contains a list of serial numbers. A column labeled ***hostname*** with the name of the device. If no name is provided, XIQ will use the default name. A column labeled ***device_type*** specifying the type of device. Valid options are AP, EXOS, or VOSS. A column labeled ***floor_id*** with the ID of the floor the AP belongs to. And a column labeled ***network_policy*** that includes the id of the network policy to be applied to the device. You can leave the value empty for network policy but the column needs added.
## Information
The script will preform API calls to onboard the devices. If any of those serial numbers exist in the VIQ, or another VIQ a message will print on the screen as well as in the log file.
A new CSV file will be created with all the information from the original csv file but have an added column labeled ***'xiq_status'*** . This column will be updated with either ***'Exists'*** if the device already exists in the VIQ, ***'Onboarded'*** if the script successfully onboards the device, ***''Exists in different XIQ''*** if the device belongs to another VIQ, ***'Serial number not valid'*** if the serial number is invalid, or and error message with why XIQ was unable to onboard the device.

## Needed files
the XIQ_CSV_onboard.py script uses several other files. If these files are missing the script will not function.
In the same folder as the XIQ_CSV_onboard.py script there should be an /app/ folder. Inside this folder should be a logger.py file and a xiq_api.py file. After running the script a new file 'xiq_serial_onboard.log' will be created as well as a new CSV file.

The script requires a CSV file to be entered when ran. This CSV file should be added to the same folder as the script.

The log file that is created when running will show any errors that the script might run into. It is a great place to look when troubleshooting any issues. The log file will also include the serial numbers for devices that are not onboarded.

## Preparing the CSV
##### required columns
***serialnumber*** - each device will need to have a valid serial number in this column
***hostname*** - the name you would like applied to the device. this can be left blank
***device_type*** - the type of device. Needs to be AP, EXOS, or VOSS.
***floor_id*** - The ID of the floor you want the AP added to.
> an easy way to get this is to open the floor in the GUIplanning tool. The ID is the number in the URL after extremecloudiq.com/#/plan/ 
***network_policy*** - the ID of the network policy you would like applied to the device
> an easy way to get this is to open the network policy in the GUI. The ID is the number in the URL after extremecloudiq.com/#/config/
> Note: the value for network_policy is optional for the row. If not added the device will not be added to a network policy.

## Running the script
open the terminal to the location of the script and run this command.

```
python XIQ_CSV_onboard.py
```
### Logging in
The script will prompt the user for XIQ credentials.
>Note: your password will not show on the screen as you type

### Entering the csv file
The script will prompt to enter the CSV file.
```
Make sure the csv file is in the same folder as the python script.
Please enter csv filename:
```
Enter the name of the file that is located in the same folder as the script and press enter.

### flags
There is an optional flag that can be added to the script when running.
```
--external
```
This flag will allow you to create the locations and assign the devices to locations on an XIQ account you are an external user on. After logging in with your XIQ credentials the script will give you a numeric option of each of the XIQ instances you have access to. Choose the one you would like to use.

You can add the flag when running the script.
```
python XIQ_CSV_onboard.py --external
```
## requirements
There are additional modules that need to be installed in order for this script to function. They are listed in the requirements.txt file and can be installed with the command 'pip install -r requirements.txt' if using pip.