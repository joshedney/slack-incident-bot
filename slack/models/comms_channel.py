from datetime import datetime
from django.conf import settings
from django.db import models
from django.urls import reverse
from urllib.parse import urljoin
from core.models.incident import Incident
from response.settings.prod import get_user_id
from slack.slack_utils import *
from slack.block_kit import *
from opsgenie.models import NotifyOnCall
import logging

logger = logging.getLogger(__name__)


class CommsChannelManager(models.Manager):
    def create_comms_channel(self, incident):
        "Creates a comms channel in slack, \
        and saves a reference to it in the DB"

        # Create the channel
        created_channel = False
        name = f"{settings.COMMS_CHANNEL_NAME}-{incident.pk}"
        try:
            channel_id = create_channel(name)
            created_channel = True
        except SlackError as e:
            try:
                get_channel_id(channel_name, auto_unarchive=True)
            except SlackError as e:
                logger.error('Failed to create or get comms channel for {name}: {e}')
                send_message()

        # Update the channel topic
        try:
            doc_url = f'{settings.SITE_URL}/incident/{incident.pk}/'
            set_channel_topic(channel_id, f"{incident.report} - {doc_url}")
        except SlackError as e:
            logger.error('Failed to set channel topic for {name}: {e}')

        # Save the channel
        if created_channel:
            comms_channel = self.create(
                incident=incident,
                channel_id=channel_id,
            )

        # Notify the incident team
        send_message(channel_id, f"<!here> INCIDENT: {incident.report}")

        # Post the current status to the channel
        comms_channel.post_status()

        # Invite the incident team
        SLACK_TOKEN = settings.SLACK_TOKEN
        for i in settings.INCIDENT_TEAM:
            try:
                invite_user_to_channel(get_user_id(i, SLACK_TOKEN), channel_id)
            except SlackError as e:
                logger.error('Failed to invite the incident team ({i}) for {name}: {e}')

        # Trigger alerts
        try:
            alert = NotifyOnCall()
            alert.create(name, incident.report, "Systems Team")
            alert.create(name, incident.report, "Support Team")
            send_message(channel_id, "On-call team paged")
        except e:
            logger.error('Failed to notify the oncall team for {name}: {e}')

        return comms_channel


class CommsChannel(models.Model):

    objects = CommsChannelManager()
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    channel_id = models.CharField(max_length=20, null=False)
    incidents_channel_ref = channel_reference(settings.INCIDENT_CHANNEL_ID)

    ARCHIVE_COMMS_BUTTON = "archive-comms-button"
    SCALE_UP_NORMAL = "scale-up-normal"
    SCALE_UP_LARGE = "scale-up-large"
    SCALE_UP_EMERGENCY = "scale-up-emergency"
    BLOCK_DEPLOYS = "block-deploys"

    def post_in_channel(self, message: str):
        send_message(self.channel_id, message)

    def feedback_command(self, user, message: str):
        send_ephemeral_message(self.channel_id, user, message)

    def rename(self, new_name):
        rename_channel(self.channel_id, new_name)

    def archive_button(self, message: str):
        msg = Message()
        msg.set_fallback_text(f"Do you want to archive the channel?")
        actions = Actions(block_id="actions")
        actions.add_element(Button("Archive Channel ?", self.ARCHIVE_COMMS_BUTTON, value=self.channel_id))
        msg.add_block(actions)
        response = msg.send(message)


    def scaleup_buttons(self, message: str):
        msg = Message()
        msg.set_fallback_text(f"Which scaling policy would you like to invoke?")
        actions = Actions(block_id="scaleup")
        actions.add_element(Button("Normal", self.SCALE_UP_NORMAL, style="primary", value="normal"))
        actions.add_element(Button("Large", self.SCALE_UP_LARGE, style="primary", value="large"))
        actions.add_element(Button("Emergency", self.SCALE_UP_EMERGENCY, style="danger", value="emergency"))
        msg.add_block(actions)
        response = msg.send(message)


    def block_deploys(self, message: str):
        msg = Message()
        msg.set_fallback_text(f"Would you like to block deploys?")
        actions = Actions(block_id="block_deploys")
        actions.add_element(Button("Block Deploys", self.BLOCK_DEPLOYS, style="danger", value="yes"))
        msg.add_block(actions)
        response = msg.send(message)

    # Post the current incident status to the channel
    def post_status(self):
        try:
            msg = Message()
            # Set the fallback text
            msg.set_fallback_text(f"INCIDENT: {self.incident.report}")

            # Incident title
            msg.add_block(Section(block_id="report", text=Text(f":rotating_light: *{self.incident.report}* :rotating_light:")))

            # Lead and status
            incident_lead_text = '-'
            if self.incident.lead:
                incident_lead_text = user_reference(self.incident.lead.external_id)
            msg.add_block(Section(block_id="first_row", fields=[Text(f":male-firefighter: Incident Lead: {incident_lead_text}"), Text(f"{self.incident.status_emoji()} Status: {self.incident.status_text().capitalize()}")]))

            # Reporter and severity
            severity_text = self.incident.severity_text().capitalize() if self.incident.severity_text() else "-"
            msg.add_block(Section(fields=[Text(f":man-raising-hand: Reporter: {user_reference(self.incident.reporter.external_id)}"), Text(f"{self.incident.severity_emoji()} Severity: {severity_text}")]))
            doc_url = urljoin(
                settings.SITE_URL,
                reverse('incident_doc', kwargs={'incident_id': self.incident.pk})
            )

            # Document
            msg.add_block(Section(fields=[Text(f":newspaper: Document: <{doc_url}|Incident {self.incident.pk}>")]))

            # Impact and summary
            msg.add_block(Section(fields=[Text(f":world_map: Impact: {self.incident.impact}")]))
            msg.add_block(Section(fields=[Text(f":rainbow: Summary: {self.incident.summary}")]))

            # Add a help message
            msg.add_block(Divider())
            msg.add_block(Section(fields=[Text(f"For help, please use `@Incident Bot help`")]));

            # Post the message
            response = msg.send(self.channel_id)

        except SlackError as e:
            logger.error('Failed to create status widget for {name}: {e}')


    def __str__(self):
        return self.incident.report
