from core.models import Incident
from slack.models import CommsChannel
from slack .decorators import recurring_notification, single_notification


# Notification for missing severity
@recurring_notification(interval_mins=5, max_notifications=5)
def remind_severity(incident: Incident):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        if not incident.severity:
            comms_channel.post_in_channel("🌤️ This incident doesn't have a severity.  Please set one with `@Incident Bot severity ...`")
    except CommsChannel.DoesNotExist:
        pass


# Notification for missing lead
@recurring_notification(interval_mins=2, max_notifications=5)
def remind_incident_lead(incident: Incident):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        if not incident.lead:
            comms_channel.post_in_channel("👩‍🚒 This incident hasn't got a lead.  Please set one with `@Incident Bot lead ...`")
    except CommsChannel.DoesNotExist:
        pass


@recurring_notification(interval_mins=720, max_notifications=6)
def remind_close_incident(incident: Incident):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        if not incident.is_closed():
            comms_channel.post_in_channel(":timer_clock: This incident has been running a long time.  Can it be closed now?")
        elif incident.is_closed():
            comms_channel.post_in_channel(":timer_clock: This incident has been closed for a long time.  Can the channel be archived?")
    except CommsChannel.DoesNotExist:
        pass


# Notification to update the client
@recurring_notification(interval_mins=60, max_notifications=6)
def remind_client_comms(incident: Incident):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        if not incident.is_closed() and incident.severity < "4":
            comms_channel.post_in_channel("Has the client been updated? :shrug:")
    except CommsChannel.DoesNotExist:
        pass


# Notification to create a status page
@single_notification(initial_delay_mins=30)
def remind_status_page(incident: Incident):
    try:
        comms_channel = CommsChannel.objects.get(incident=incident)
        if not incident.is_closed() and incident.severity < "4":
            comms_channel.post_in_channel(":statuspage: Do we need to put up a statuspage? To do so, use the command `@Incident Bot statuspage`")
    except CommsChannel.DoesNotExist:
        pass
