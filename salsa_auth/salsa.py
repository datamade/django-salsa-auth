import json

from django.conf import settings
import requests


class SalsaAPI(object):
    '''
    Wrapper for supporter methods:
    https://help.salsalabs.com/hc/en-us/articles/224470107-Engage-API-Supporter-Data
    '''

    HOSTNAME = 'https://api.salsalabs.org'

    def __init__(self, api_key):
        self.api_key = api_key

    def put_supporter(self, user):
        endpoint = '{}/api/integration/ext/v1/supporters'.format(self.HOSTNAME)

        payload = {
            'supporters': [
                {
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'postalCode': user.zip_code,
                    'contacts': [{
                        'type': 'EMAIL',
                        'value': user.email,
                        'status':'OPT_IN'
                    }],
                }
            ]
        }

        try:
            response = requests.put(endpoint, data=json.dump({'payload': payload}), headers={'authToken': settings.SALSA_API_TOKEN})
        except:
            '''
            When the call to add or update completes, the resulting payload will include all of the data that was sent within the call. Each supporter within the call will have a decorated result attribute to indicate the result of the operation.  For adds or updates, these values will  be:

            ADDED - the provided supporter was added to the system
            UPDATED - the provided supporter was updated
            VALIDATION_ERROR - if one or more objects for the supporter has validation errors with the provided data
            SYSTEM_ERROR - if an unrecoverable occurs on the Salsa Engage System
            NOT_FOUND - if the id provided with the supporter did not exist within the system
            '''
            pass

        return response

    def get_supporter(self, email_address):
        endpoint = '{}/api/integration/ext/v1/supporters/search'.format(self.HOSTNAME)

        payload = {
            'identifiers': [email_address]
            'identifierType': 'EMAIL_ADDESSS'
        }

        response = requests.post(endpoint, data=json.dump({'payload': payload}), headers={'authToken': settings.SALSA_API_TOKEN})

        '''
        return supporter
        '''

client = SalsaAPI()
