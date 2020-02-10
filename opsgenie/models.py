import opsgenie_sdk
from django.conf import settings


class NotifyOnCall:
    def __init__(self):
        self.conf = opsgenie_sdk.configuration.Configuration()
        self.conf.api_key['Authorization'] = settings.OPSGENIE_API

        self.api_client = opsgenie_sdk.api_client.ApiClient(configuration=self.conf)
        self.alert_api = opsgenie_sdk.AlertApi(api_client=self.api_client)

    def create(self, incident_id, incident_summary, team):
        body = opsgenie_sdk.CreateAlertPayload(
            message=f'{incident_id} - {incident_summary}',
            alias='{team}-{incident_id}',
            description=f'{settings.SITE_URL}/incident/{incident_id}/',
            responders=[{
                'name': team,
                'type': 'team'
              }],
            priority='P1'
          )
        try:
            create_response = self.alert_api.create_alert(create_alert_payload=body)
            print(create_response)
            return create_response
        except opsgenie_sdk.ApiException as err:
            print("Exception when calling AlertApi->create_alert: %s\n" % err)
