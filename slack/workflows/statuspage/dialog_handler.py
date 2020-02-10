import json

from slack.workflows.statuspage.connections import get_status_page_conn

from slack.models import Incident
from core.models import IncidentExtension
from slack.slack_utils import send_ephemeral_message


# Create a dictionary for status page messages.
template_statuspage_messages = {}
with open('/home/blubolt/www/incidents.blubolt.com/slack/workflows/statuspage/statuspage_templates.txt') as template_messages:
  for line in template_messages:
      key, value = line.split(":")
      template_statuspage_messages[key] = value


def handle_status_page_update(user_id: str, channel_id: str, submission: json, response_url: str, state: json):
    incident_id = state
    incident = Incident.objects.get(pk=incident_id)
    statuspage_incident_id, created = IncidentExtension.objects.get_or_create(incident=incident, key='statuspage_incident_id')

    if submission['template'] == 'custom':
        vars = {
            'name': submission['name'],
            'status': submission['incident_status'],
            'message': submission['message'] or '',
            'impact_override': submission['impact_override'] or ''
        }
    else:
        vars = {
            'name': submission['name'],
            'status': submission['incident_status'],
            'message': template_statuspage_messages[submission['template']],
            'impact_override': submission['impact_override'] or ''
        }

    try:
        if statuspage_incident_id.value:
            get_status_page_conn().incidents.update(incident_id=statuspage_incident_id.value, **vars)
        else:
            response = get_status_page_conn().incidents.create(**vars)
            statuspage_incident_id.value = response['id']
            statuspage_incident_id.save()

        msg = f'The status page has been updated 👍 Click here to update the <https://manage.statuspage.io/pages/v2dd4xntf4y2/incidents/%s | components affected>' % (statuspage_incident_id.value)

    except Exception as ex:
        msg = f'⚠️ {repr(ex)}'

    send_ephemeral_message(channel_id, user_id, msg)
