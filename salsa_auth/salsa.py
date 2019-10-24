import json

from django.conf import settings
import requests


class SalsaException(Exception):
    pass


class SalsaAPI(object):
    '''
    Wrapper for supporter methods:
    https://help.salsalabs.com/hc/en-us/articles/224470107-Engage-API-Supporter-Data
    '''
    HOSTNAME = 'https://api.salsalabs.org'

    SAMPLE_PUT_RESPONSE = json.dumps({
        'payload': {
            'count': 1,
            'supporters': [
                {
                    'firstName': '',
                    'lastName': '',
                    'address': {'postalCode': ''},
                    'contacts': [{
                        'type': 'EMAIL',
                        'value': '',
                        'status':'OPT_IN'
                    }],
                }
            ]
        }
    })

    SAMPLE_GET_RESPONSE = json.dumps({
        'payload': {
            'count': 1,
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

    def _make_error_message(self, error_object):
        '''
        Create human-readable error message from API response.
        '''
        return 'Invalid field "{fieldName}": {message}. {details}.\n'.format(**error_object)

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

    def put_supporter(self, user):
        '''
        Add or update supporter.
        '''
        endpoint = '{}/api/integration/ext/v1/supporters'.format(self.HOSTNAME)

        payload = {
            'supporters': [
                {
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'address': {'postalCode': user.userzipcode_set.get().zip_code},
                    'contacts': [{
                        'type': 'EMAIL',
                        'value': user.email,
                        'status':'OPT_IN'
                    }],
                }
            ]
        }

        response = requests.put(
            endpoint,
            json={'payload': payload},
            headers={'authToken': settings.SALSA_AUTH_API_KEY}
        )

        response_data = json.loads(response.text)

        if response.status_code == 200:
            supporter, = response_data['payload']['supporters']

            if supporter['result'] in ('ADDED', 'UPDATED'):
                return supporter

            elif supporter['result'] == 'VALIDATION_ERROR':
                error = ''

                for e in supporter['contacts'][0].get('errors', []) + supporter['address'].get('errors', []):
                    error += self._make_error_message(error)

                raise SalsaException(error)

            else:
                raise SalsaException('Supporter could not be added due to {}'.format(supporter['result']))

        else:
            raise SalsaException(response.text)

    def get_supporter(self, email_address):
        '''
        Return the first supporter with a matching email address that is valid,
        i.e., does not have a status of 'HARD_BOUNCE'.
        '''
        endpoint = '{}/api/integration/ext/v1/supporters/search'.format(self.HOSTNAME)

        payload = {
            'identifiers': [email_address],
            'identifierType': 'EMAIL_ADDRESS'
        }

        response = requests.post(endpoint,
                                 json={'payload': payload},
                                 headers={'authToken': settings.SALSA_AUTH_API_KEY})

        if response.status_code == 200:
            response_data = json.loads(response.text)

            if response_data['payload']['count'] == 1:
                supporter, = response_data['payload']['supporters']

                if supporter['result'] == 'FOUND' and self._has_valid_email(supporter, email_address):
                    return supporter

            else:
                for supporter in response_data['payload']['supporters']:
                    if self._has_valid_email(supporter, email_address):
                        return supporter

        else:
            raise SalsaException(response.text)


client = SalsaAPI()
