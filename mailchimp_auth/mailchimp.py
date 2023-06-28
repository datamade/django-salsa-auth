from django.conf import settings
import email_normalize
import logging

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError


class MailchimpAPI(object):
    '''
    Wrapper for supporter methods:
    https://mailchimp.com/developer/marketing/api/list-members/
    '''
    LIST_ID = settings.MAILCHIMP_LIST_ID
    API_KEY = settings.MAILCHIMP_API_KEY
    SERVER = settings.MAILCHIMP_SERVER

    def __init__(self):
        try:
            self.client = MailchimpMarketing.Client()
            self.client.set_config({
                "api_key": self.API_KEY,
                "server": self.SERVER
            })

        except ApiClientError as error:
            logging.warning("Error: {}".format(error.text))
        

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
            response = self.client.lists.set_list_member(self.LIST_ID, subscriber, payload)
        except ApiClientError as error:
            logging.warning("Error: {}".format(error.text))
            return 'error'  # Used to help display front end errors

        return response  # A dict representing the member that has been added

    def get_supporter(self, email_address, allow_invalid=False):
        '''
        Return the supporter with an exactly matching email address that is valid.
        '''

        try:
            response = self.client.searchMembers.search(query=email_address, fields=["exact_matches"])
        except ApiClientError as error:
            logging.warning("Error: {}".format(error.text))
            return 'error'

        if response['exact_matches']['total_items'] == 1:
            supporter = response['exact_matches']['members'][0]

            if allow_invalid:
                return supporter

            elif self._has_valid_email(supporter, email_address):
                return supporter

        else:
            # No single, exact match found
            return None


client = MailchimpAPI()