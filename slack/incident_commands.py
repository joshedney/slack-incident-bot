from core.models import Incident, Action, ExternalUser
from slack.models import CommsChannel
from slack.decorators import incident_command, get_help
from slack.slack_utils import *
from slack.aws_utils import *
from datetime import datetime


@incident_command(['help'], helptext='Display a list of commands and usage')
def send_help_text(incident: Incident, user_id: str, message: str):
    return True, get_help()


@incident_command(['desc', 'description'], helptext='Provide a description of what\'s going on')
def update_summary(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    previous_summary = incident.summary
    incident.summary = message
    incident.save()
    comms_channel.post_in_channel(f"The description has been updated to *{incident.summary}*")
    return True, None


@incident_command(['impact'], helptext='Explain the impact of this')
def update_impact(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    previous_impact = incident.impact
    incident.impact = message
    incident.save()
    comms_channel.post_in_channel(f"Impact changed from *{previous_impact}* to *{incident.impact}*")
    return True, None


@incident_command(['lead'], helptext='Assign someone as the incident lead')
def set_incident_lead(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    assignee = reference_to_id(message) or user_id
    name = get_user_profile(assignee)['name']
    user = GetOrCreateSlackExternalUser(external_id=assignee, display_name=name)
    incident.lead = user
    incident.save()
    comms_channel.post_in_channel(f"The incident lead has been changed to {name}")
    return True, None


@incident_command(['severity', 'sev'], helptext='Set the incident severity')
def set_severity(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    for sev_id, sev_name in Incident.SEVERITIES:
        # look for sev name (e.g. critical) or sev id (1)
        if (sev_name in message) or (sev_id in message):
            incident.severity = sev_id
            incident.save()
            comms_channel.post_in_channel(f"The incident severity has been changed to {sev_name}")
            return True, None

    return False, None


@incident_command(['rename'], helptext='Rename the incident channel')
def rename_incident(incident: Incident, user_id: str, message: str):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        comms_channel.rename(message)
    except SlackError:
        return True, "👋 Sorry, the channel couldn't be renamed. Make sure that name isn't taken already."
    return True, None


@incident_command(['duration'], helptext='How long has this incident been running?')
def set_severity(incident: Incident, user_id: str, message: str):
    duration = incident.duration()

    comms_channel = CommsChannel.objects.get(incident=incident)
    comms_channel.post_in_channel(f"The incident has been running for {duration}")

    return True, None


@incident_command(['close'], helptext='Close this incident.')
def close_incident(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    action_list = Action.objects.filter(incident=incident)

    if incident.is_closed():
        comms_channel.post_in_channel(f"This incident was already closed at {incident.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True, None

    incident.end_time = datetime.now()
    incident.save()

    comms_channel.post_in_channel(f"This incident has been closed! 📖 -> 📕")

    if action_list.exists():
        get_action(incident, user_id, message)
    else:
        comms_channel.post_in_channel(f"There are no actions for this incident.\n You can still add one by using `@Incident Bot action ...`")

    comms_channel.archive_button(comms_channel.channel_id)

    return True, None


@incident_command(['add_action', 'action'], helptext='Log a follow up action')
def set_action(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    name = get_user_profile(user_id)['name']
    action_reporter = GetOrCreateSlackExternalUser(external_id=user_id, display_name=name)
    Action(incident=incident, details=message, user=action_reporter).save()
    text = f"Thank you, your follow up action has been added to the incident.\nYou can view all actions by running `@Incident Bot list_actions`"
    comms_channel.feedback_command(user_id, text)
    return True, None


# Get a list of actions for the incident
@incident_command(['list_actions'], helptext='Retrieve the list of actions')
def get_action(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    action_list = Action.objects.filter(incident=incident)
    if action_list.exists():
        comms_channel.post_in_channel(f"Here are a list of actions for this incident:")
        for action_item in action_list:
            action_reporter = str(action_item.user)
            comms_channel.post_in_channel(f" :pushpin: `{action_item.details}` added by <@{action_reporter.strip(' (slack)')}>")
    else:
        comms_channel.post_in_channel(f"There are no actions for this incident.\n You can add one by using `@Incident Bot add_action ...`")
    return True, None


@incident_command(['scaleup'], helptext='Scale up the number of webworkers')
def scaleup_action(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    comms_channel.scaleup_buttons(comms_channel.channel_id)
    return True, None


# Command to block deploys across blucommerce
@incident_command(['block_deploys'], helptext='Blocks deploys across all clients')
def block_deploys_action(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    comms_channel.post_in_channel(f"Blocking deploys across all clients. \n Please standby...")
    response = block_deploys(get_user_profile(user_id)['name'])
    comms_channel.post_in_channel(f"{response}")
    return True, None


@incident_command(['status'], helptext='Show the current status of the incident')
def set_action(incident: Incident, user_id: str, message: str):
    comms_channel = CommsChannel.objects.get(incident=incident)
    comms_channel.post_status()
    return True, None
