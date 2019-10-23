import json

from django.conf import settings
import requests


class SalsaAPI(object):
    '''
    Wrapper for supporter methods:
    https://help.salsalabs.com/hc/en-us/articles/224470107-Engage-API-Supporter-Data
    '''
    HOSTNAME = 'https://api.salsalabs.org'

    def put_supporter(self, user):
        if settings.SALSA_AUTH_DEBUG:
            return json.dumps({
                'payload': {
                    'count': 1,
                    'offset': 0,
                    'total': '1200',
                    'supporters': [
                        {
                            'firstName': '',
                            'lastName': '',
                            'postalCode': '',
                            'contacts': [{
                                'type': 'EMAIL',
                                'value': '',
                                'status':'OPT_IN'
                            }],
                        }
                    ]
                }
            })

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
            response = requests.put(endpoint, data=json.dumps({'payload': payload}), headers={'authToken': settings.SALSA_AUTH_API_KEY})
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
        '''
        Return the first supporter with a matching email address that is valid,
        i.e., does not have a status of 'HARD_BOUNCE'.
        '''
        if settings.SALSA_AUTH_DEBUG:
            return json.dumps({
                'payload': {
                    'count': 1,
                    'offset': 0,
                    'total': '1200',
                    'supporters': [{
                        'result': 'FOUND',
                        'contacts': [{
                            'type': 'EMAIL',
                            'value': '',
                            'status':'OPT_IN'
                        }],
                    }]
                }
            })

        endpoint = '{}/api/integration/ext/v1/supporters/search'.format(self.HOSTNAME)

        payload = {
            'identifiers': [email_address],
            'identifierType': 'EMAIL_ADDRESS'
        }

        response = requests.post(endpoint,
                                 json={'payload': payload},
                                 headers={'authToken': settings.SALSA_AUTH_API_KEY})

        response_data = json.loads(response.text)

        if response_data['payload']['count'] == 1:
            supporter, = response_data['payload']['supporters']

            if supporter['result'] == 'FOUND' and self._has_valid_email(supporter, email_address):
                return supporter

        else:
            for supporter in response_data['payload']['supporters']:
                if self._has_valid_email(supporter, email_address):
                    return supporter

    def _has_valid_email(self, supporter, email_address):
        '''
        Determine whether a supporter has a valid contact matching the given
        email address.
        '''
        for contact in supporter['contacts']:
            email_valid = (contact['type'] == 'EMAIL' and
                           contact['value'] == email_address and
                           contact['status'] != 'HARD_BOUNCE')

            if email_valid:
                return True

        return False

client = SalsaAPI()
