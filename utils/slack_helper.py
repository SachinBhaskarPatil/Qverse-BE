
from structlog import get_logger
from abc import ABC, abstractmethod
import requests
from django.conf import settings
import json
from http import HTTPStatus
from qverse.celery_manager import celery_app


logger = get_logger(file_name='slack_helper')


class Communication(ABC):    
    @abstractmethod
    def validate(self):
        pass
    @abstractmethod
    def send(self):
        pass


class Slack(Communication):
    def validate(self):
        pass
        
class SlackAppWebhook(Slack):
    """
    """

    def __init__(self, message: dict) -> None:
        self.message = message
    
    def send(self):
        response = None
        try:
            url = 'https://hooks.slack.com/services/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'
            data = self.message
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.request("POST", url, headers=headers, data=json.dumps(data), timeout=15)

            if response.status_code != HTTPStatus.OK and response.status_code != HTTPStatus.ACCEPTED:
                logger.error("Failed to send slack message via app and webhook", message=self.message,
                             status_code=response.status_code, error=response.text, provider='slack')
                return False
            return True

        except Exception as e:
            logger.exception("Failed to send message to slack via app and webhook", message=self.message,
                             status_code=getattr(response, 'status_code', 500), error=getattr(response, 'text', str(e)),
                             provider='slack')
            return False


def generate_slack_message(msg:str):
    slack_msg={"blocks":
            [{
            "type":"section",
            "text":
                {
                "type": "mrkdwn",
                "text": msg
                }
            }
        ]}

    return slack_msg



def slack_send_wrapper(msg):
    try:
        slack_bot=SlackAppWebhook(msg)
        if slack_bot.send():
            logger.info("Slack message send",msg=msg)
        else:
            logger.error("Slack message wasn't send",msg=msg)
    except Exception as e:
        logger.error("Error while running slack_send_wrapper method")