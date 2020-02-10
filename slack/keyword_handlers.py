from core.models.incident import Incident

from slack.models import CommsChannel
from slack.decorators import keyword_handler

import logging
logger = logging.getLogger(__name__)

# Keyword handler for statuspage | status page
@keyword_handler(['status page', 'statuspage'])
def status_page_notification(comms_channel: CommsChannel, user: str, text: str, ts: str):
    comms_channel.post_in_channel("ℹ️ You mentioned the Status Page - To create or update the statuspage use the command `@Incident Bot statuspage`")

# Keyword handler for scaleup | scale up
@keyword_handler(['scaleup', 'scale up'])
def scale_up_notification(comms_channel: CommsChannel, user: str, text: str, ts: str):
    comms_channel.post_in_channel("ℹ️ You mentioned scaling up - If you would like to scaleup, please use one of the buttons below.")


@keyword_handler(['block deploys', 'block deploy'])
def block_deploys_notification(comms_channel: CommsChannel, user: str, text: str, ts: str):
    comms_channel.post_in_channel("ℹ️ Would you like to block deploys?")
    comms_channel.block_deploys(comms_channel.channel_id)
