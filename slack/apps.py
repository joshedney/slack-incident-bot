from django.apps import AppConfig
from django.conf import settings


class SlackConfig(AppConfig):
    name = 'slack'

    def ready(self):
        import slack.settings
        import slack.signals
        import slack.action_handlers
        import slack.event_handlers
        import slack.incident_commands
        import slack.keyword_handlers
        import slack.incident_notifications
        import slack.dialog_handlers
        import slack.workflows
        if settings.PAGERDUTY_ENABLED:
            import slack.workflows.pagerduty
