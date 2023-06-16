import json

from django.conf import settings
import requests
import email_normalize

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError


class SalsaException(Exception):
    pass


class SalsaAPI(object):
    '''
    Wrapper for supporter methods:
    https://help.salsalabs.com/hc/en-us/articles/224470107-Engage-API-Supporter-Data
    '''
    HOSTNAME = 'https://api.salsalabs.org'
    LIST_ID = settings.MAILCHIMP_LIST_ID
    API_KEY = settings.MAILCHIMP_API_KEY
    SERVER = settings.MAILCHIMP_SERVER

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
        email_valid = (email_normalize.normalize(supporter["email_address"]) == email_normalize.normalize(email_address) and
                        supporter['status'] != 'unsubscribed')

        if email_valid:
            return True

        return False

    def put_supporter(self, user):
        '''
        Add or update supporter.
        '''

        payload = {
            "email_address": user.email,
            "status": "subscribed",
            "merge_fields": {
                "FNAME": user.first_name,
                "LNAME": user.last_name,
            }
        }

        subscriber = payload["email_address"]

        try:
            client = MailchimpMarketing.Client()
            client.set_config({
                "api_key": self.API_KEY,
                "server": self.SERVER
            })

            response = client.lists.set_list_member(self.LIST_ID, subscriber, payload)

        except ApiClientError as error:
            print("Error: {}".format(error.text))

        return response  # A dict representing the member that has been added

    def get_supporter(self, email_address, allow_invalid=False):
        '''
        Return the first supporter with a matching email address that is valid,
        i.e., does not have a status of 'HARD_BOUNCE'.
        '''

        try:
            client = MailchimpMarketing.Client()
            client.set_config({
                "api_key": self.API_KEY,
                "server": self.SERVER
            })

            response = client.searchMembers.search(query=email_address, fields=["exact_matches"])

        except ApiClientError as error:
            print("Error: {}".format(error.text))

        if response['exact_matches']['total_items'] == 1:
            supporter = response['exact_matches']['members'][0]

            if allow_invalid:
                return supporter

            elif self._has_valid_email(supporter, email_address):
                return supporter

        else:
            # No single, exact match found
            return None


client = SalsaAPI()
