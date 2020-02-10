import json
from datetime import datetime

from django.conf import settings
from core.models.incident import Incident

from slack.settings import INCIDENT_EDIT_DIALOG
from slack.dialog_builder import Dialog, Text, TextArea, SelectWithOptions, SelectFromUsers
from slack.models import HeadlinePost, CommsChannel
from slack.slack_utils import *
from slack.aws_utils import *
from slack.decorators import action_handler, ActionContext

import logging
logger = logging.getLogger(__name__)

@action_handler(CommsChannel.ARCHIVE_COMMS_BUTTON)
def handle_archive_comms(ac: ActionContext):
    archive_channel(ac.button_value)

@action_handler(HeadlinePost.CLOSE_INCIDENT_BUTTON)
def handle_close_incident(ac: ActionContext):
    ac.incident.end_time = datetime.now()
    ac.incident.save()


@action_handler(HeadlinePost.CREATE_COMMS_CHANNEL_BUTTON)
def handle_create_comms_channel(ac: ActionContext):
    if CommsChannel.objects.filter(incident=ac.incident).exists():
        return

    comms_channel = CommsChannel.objects.create_comms_channel(ac.incident)

    # Invite the bot to the channel
    try:
        invite_user_to_channel(settings.INCIDENT_BOT_ID, comms_channel.channel_id)
    except Exception as ex:
        logger.error(ex)

    # Un-invite the user who owns the Slack token,
    #   otherwise they'll be added to every incident channel
    # slack_token_owner = get_slack_token_owner()
    # if ac.incident.reporter != slack_token_owner:
    #     leave_channel(comms_channel.channel_id)

    # Update the headline post to link to this
    headline_post = HeadlinePost.objects.get(
        incident=ac.incident
    )
    headline_post.comms_channel = comms_channel
    headline_post.save()


@action_handler(HeadlinePost.EDIT_INCIDENT_BUTTON)
def handle_edit_incident_button(ac: ActionContext):
    dialog = Dialog(
        title=f"Edit Incident {ac.incident.pk}",
        submit_label="Save",
        state=ac.incident.pk,
        elements=[
            Text(label="Report", name="report", value=ac.incident.report),
            TextArea(label="Summary", name="summary", value=ac.incident.summary, optional=True, placeholder="Can you share any more details?"),
            TextArea(label="Impact", name="impact", value=ac.incident.impact, optional=True, placeholder="Who or what might be affected?", hint="Think about affected people, systems, and processes"),
            SelectFromUsers(label="Lead", name="lead", value=ac.incident.lead.external_id if ac.incident.lead else None, optional=True),
            SelectWithOptions([(s.capitalize(), i) for i, s in Incident.SEVERITIES], value=ac.incident.severity, label="Severity", name="severity", optional=True)
        ]
    )

    dialog.send_open_dialog(INCIDENT_EDIT_DIALOG, ac.trigger_id)


# Handeling for scaling buttons
@action_handler(CommsChannel.SCALE_UP_NORMAL)
def handle_scaleup_normal(ac: ActionContext):
    comms_channel = CommsChannel.objects.get(incident=ac.incident)
    response = invoke_lambda_scaleup(ac.button_value.lower(), user_reference(ac.user_id))
    comms_channel.post_in_channel(response)


@action_handler(CommsChannel.SCALE_UP_LARGE)
def handle_scaleup_large(ac: ActionContext):
    comms_channel = CommsChannel.objects.get(incident=ac.incident)
    response = invoke_lambda_scaleup(ac.button_value.lower(), user_reference(ac.user_id))
    comms_channel.post_in_channel(response)


@action_handler(CommsChannel.SCALE_UP_EMERGENCY)
def handle_scaleup_emergency(ac: ActionContext):
    comms_channel = CommsChannel.objects.get(incident=ac.incident)
    response = invoke_lambda_scaleup(ac.button_value.lower(), user_reference(ac.user_id))
    comms_channel.post_in_channel(response)


# Handling for blocking deploys
@action_handler(CommsChannel.BLOCK_DEPLOYS)
def handle_block_deploys(ac: ActionContext):
    comms_channel = CommsChannel.objects.get(incident=ac.incident)
    comms_channel.post_in_channel(f"Blocking deploys across all clients. \n Please standby...")
    response = block_deploys(ac.user_id)
    comms_channel.post_in_channel(response)
