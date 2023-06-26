from django.conf import settings
import email_normalize

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
        Return the supporter with an exactly matching email address that is valid.
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


client = MailchimpAPI()


# SAMPLE_PUT_RESPONSE = json.dumps({
#     {
#         "id": "string",
#         "email_address": "string",
#         "unique_email_id": "string",
#         "contact_id": "string",
#         "full_name": "string",
#         "web_id": 0,
#         "email_type": "string",
#         "status": "subscribed",
#         "unsubscribe_reason": "string",
#         "consents_to_one_to_one_messaging": True,
#         "merge_fields": {
#             "FNAME": "string",
#             "LNAME": "string",
#             "property3": None
#         },
#         "interests": {
#             "property1": True,
#             "property2": True
#         },
#         "stats": {
#             "avg_open_rate": 0,
#             "avg_click_rate": 0,
#             "ecommerce_data": {
#             "total_revenue": 0,
#             "number_of_orders": 0,
#             "currency_code": "USD"
#             }
#         },
#         "ip_signup": "string",
#         "timestamp_signup": "2019-08-24T14:15:22Z",
#         "ip_opt": "string",
#         "timestamp_opt": "2019-08-24T14:15:22Z",
#         "member_rating": 0,
#         "last_changed": "2019-08-24T14:15:22Z",
#         "language": "string",
#         "vip": True,
#         "email_client": "string",
#         "location": {
#             "latitude": 0,
#             "longitude": 0,
#             "gmtoff": 0,
#             "dstoff": 0,
#             "country_code": "string",
#             "timezone": "string",
#             "region": "string"
#         },
#         "marketing_permissions": [
#             {
#             "marketing_permission_id": "string",
#             "text": "string",
#             "enabled": True
#             }
#         ],
#         "last_note": {
#             "note_id": 0,
#             "created_at": "2019-08-24T14:15:22Z",
#             "created_by": "string",
#             "note": "string"
#         },
#         "source": "string",
#         "tags_count": 0,
#         "tags": [
#             {
#             "id": 0,
#             "name": "string"
#             }
#         ],
#         "list_id": "string",
#         "_links": [
#             {
#             "rel": "string",
#             "href": "string",
#             "method": "GET",
#             "targetSchema": "string",
#             "schema": "string"
#             }
#         ]
#     }
# })

# SAMPLE_GET_RESPONSE = json.dumps({
#     "exact_matches": {
#         "members": [
#             {
#             ... the same structure as SAMPLE_PUT_RESPONSE,
#             }
#         ]
#     },
#     "total_items": 0
# })
