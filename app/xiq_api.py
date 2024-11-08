import logging
import os
import inspect
from socketserver import BaseRequestHandler
import sys
import json
from xmlrpc.client import APPLICATION_ERROR
from numpy import isin
import requests
from pprint import pprint as pp
current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir) 
from requests.exceptions import HTTPError
from app.logger import logger

logger = logging.getLogger('CCG_Updater.xiq_api')

PATH = current_dir

class XIQ:
    def __init__(self, user_name=None, password=None, token=None):
        self.URL = "https://api.extremecloudiq.com"
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.totalretries = 5
        if token:
            self.headers["Authorization"] = "Bearer " + token
        else:
            try:
                self.__getAccessToken(user_name, password)
            except ValueError as e:
                print(e)
                raise SystemExit
            except HTTPError as e:
               print(e)
               raise SystemExit
            except:
                log_msg = "Unknown Error: Failed to generate token for XIQ"
                logger.error(log_msg)
                print(log_msg)
                raise SystemExit 
    #API CALLS
    def __setup_get_api_call(self, info, url):
        success = False
        for count in range(1, self.totalretries+1):
            try:
                response = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = True
                break
        if not success:
            print(f"failed to {info}. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        if 'error' in response:
            if response['error_message']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return response
        
    def __setup_post_api_call(self, info, url, payload):
        success = False
        for count in range(1, self.totalretries+1):
            try:
                response = self.__post_api_call(url=url, payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = True
                break
        if not success:
            print(f"failed {info}. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        if 'error' in response:
            if response['error_message']:
                log_msg = (f"Status Code {response['error_id']}: {response['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return response
    
    def __setup_put_api_call(self, info, url, payload=''):
        success = False
        for count in range(1, self.totalretries+1):
            try:
                if payload:
                    self.__put_api_call(url=url, payload=payload)
                else:
                    self.__put_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = True
                break
        if not success:
            print(f"failed to {info}. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        
        return 'Success'

    def __setup_lro_api_call(self, info, url, payload, lro):
        success = False
        url = url + str(lro)
        for count in range(1, self.totalretries+1):
            try:
                response = requests.post(url, headers= self.headers, data=payload)
            except HTTPError as http_err:
                logger.error(f'HTTP error occurred: {http_err} - on API {url}')
                print(f"API to {info} failed attempt {count} of {self.totalretries} with HTTP error occurred: {http_err}")
                continue
            if response is None:
                log_msg = "ERROR: No response received from XIQ!"
                logger.error(log_msg)
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {log_msg}")
                continue
            if lro:
                if response.status_code != 202:
                    log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
                    logger.error(f"{log_msg}")
                    logger.warning(f"\t\t{response.text}")
                    print(f"API to {info} failed attempt {count} of {self.totalretries} with {log_msg}")
                    continue
                else:
                    success = True
                    return response
            else:
                if response.status_code != 200:
                    log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
                    logger.error(f"{log_msg}")
                    logger.warning(f"\t\t{response.text}")
                    print(f"API to {info} failed attempt {count} of {self.totalretries} with {log_msg}")
                    continue
                else:
                    success = True
                    break
        if not success:
            print(f"failed to {info}. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            print(f"API to {info} failed attempt {count} of {self.totalretries} with Unable to parse the data from json, script cannot proceed")
        if 'error' in data:
            if data['error_message']:
                log_msg = (f"Status Code {data['error_id']}: {data['error_message']}")
                logger.error(log_msg)
                print(f"API Failed {info} with reason: {log_msg}")
                print("Script is exiting...")
                raise SystemExit
        return data
            
    def __get_api_call(self, url):
        try:
            response = requests.get(url, headers= self.headers)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise ValueError(log_msg)
            raise ValueError(log_msg) 
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data

    def __post_api_call(self, url, payload):
        try:
            response = requests.post(url, headers= self.headers, data=payload)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code == 202:
            return "Success"
        elif response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise Exception(data['error_message'])
            raise ValueError(log_msg)
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
            raise ValueError("Unable to parse the data from json, script cannot proceed")
        return data
    
    def __put_api_call(self, url, payload=''):
        try:
            if payload:
                response = requests.put(url, headers= self.headers, data=payload)
            else:
                response = requests.put(url, headers= self.headers)
        except HTTPError as http_err:
            logger.error(f'HTTP error occurred: {http_err} - on API {url}')
            raise ValueError(f'HTTP error occurred: {http_err}') 
        if response is None:
            log_msg = "ERROR: No response received from XIQ!"
            logger.error(log_msg)
            raise ValueError(log_msg)
        if response.status_code != 200:
            log_msg = f"Error - HTTP Status Code: {str(response.status_code)}"
            logger.error(f"{log_msg}")
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(f"\t\t{response.text}")
            else:
                if 'error_message' in data:
                    logger.warning(f"\t\t{data['error_message']}")
                    raise Exception(data['error_message'])
                else:
                    logger.warning(data)
                raise ValueError(log_msg)
        return response.status_code

    def __getAccessToken(self, user_name, password):
        info = "get XIQ token"
        success = 0
        url = self.URL + "/login"
        payload = json.dumps({"username": user_name, "password": password})
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url,payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print("failed to get XIQ token. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg)

    ## EXTERNAL FUNCTION

    # EXTERNAL ACCOUNTS
    def __getVIQInfo(self):
        info="get current VIQ name"
        success = 0
        url = f"{self.URL}/account/home"
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            self.viqName = data['name']
            self.viqID = data['id']
            
    #ACCOUNT SWITCH
    def selectManagedAccount(self):
        self.__getVIQInfo()
        info="gather accessible external XIQ acccounts"
        success = 0
        url = f"{self.URL}/account/external"
        for count in range(1, self.totalretries):
            try:
                data = self.__get_api_call(url=url)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"Failed to {info}")
            return 1
            
        else:
            return(data, self.viqName)


    def switchAccount(self, viqID, viqName):
        info=f"switch to external account {viqName}"
        success = 0
        url = f"{self.URL}/account/:switch?id={viqID}"
        payload = ''
        for count in range(1, self.totalretries):
            try:
                data = self.__post_api_call(url=url, payload=payload)
            except ValueError as e:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with {e}")
            except Exception as e:
                print(f"API to {info} failed with {e}")
                print('script is exiting...')
                raise SystemExit
            except:
                print(f"API to {info} failed attempt {count} of {self.totalretries} with unknown API error")
            else:
                success = 1
                break
        if success != 1:
            print(f"failed to get XIQ token to {info}. Cannot continue to import. Please check log for more details.")
            print("exiting script...")
            raise SystemExit
        
        if "access_token" in data:
            #print("Logged in and Got access token: " + data["access_token"])
            self.headers["Authorization"] = "Bearer " + data["access_token"]
            self.__getVIQInfo()
            if viqName != self.viqName:
                logger.error(f"Failed to switch external accounts. Script attempted to switch to {viqName} but is still in {self.viqName}")
                print("Failed to switch to external account!!")
                print("Script is exiting...")
                raise SystemExit
            return 0

        else:
            log_msg = "Unknown Error: Unable to gain access token for XIQ"
            logger.warning(log_msg)
            raise ValueError(log_msg) 

    #APS
    def advanceOnboardAPs(self, data, lro=False):
        info="onboard APs"
        payload = json.dumps(data)
        url = f"{self.URL}/devices/:advanced-onboard?async="
        response = self.__setup_lro_api_call(info,url,payload,lro)
        if lro:
            return response.headers['Location']
        else:
            return response

    # LRO
    def checkLRO(self, url):
        info='check lro status'
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error {info} - HTTP Status Code: {str(response.status_code)}")
            print(response.text)
            data = {
                  "metadata": {
                    "status": f"HTTP ERROR: {str(response.status_code)}",
                  }
                }
        else:
            try:
                data = response.json()
            except json.JSONDecodeError:
                    logger.error(f"Unable to parse json data - {url} - HTTP Status Code: {str(response.status_code)}")
                    print(f"API to {info} failed attempt with Unable to parse the data from json, script cannot proceed") 
                    data = {
                          "metadata": {
                            "status": f"Json parse ERROR: {str(response.text)}",
                          }
                        }       
        return data
