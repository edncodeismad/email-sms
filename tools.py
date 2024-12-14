from openai import OpenAI
from dotenv import load_dotenv
import os
from twilio.rest import Client

from vonage import Auth, Vonage
import vonage
from vonage_messages.models import Sms

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
twilio_sid = os.getenv('TWILIO_SID')
twilio_token = os.getenv('TWILIO_TOKEN')
openai_client = OpenAI(api_key=api_key)
twilio_client = Client(twilio_sid, twilio_token)

VONAGE_APPLICATION_ID = '2f90e2fb-9437-4f94-80db-daa350797574'
VONAGE_APPLICATION_PRIVATE_KEY_PATH = 'private.key'
VONAGE_BRAND_NAME = 'Vonage APIs'

vonage_client = Vonage(
    Auth(
        application_id=VONAGE_APPLICATION_ID,
        private_key=VONAGE_APPLICATION_PRIVATE_KEY_PATH,
    )
)

def send_llm(system, message, model_name='gpt-3.5-turbo'):
    completion = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message}
            ]
    )
    result = completion.choices[0].message.content
    return result

def send_sms(message, to):
    response = vonage_client.messages.send(Sms(
        to=to,
        from_=VONAGE_BRAND_NAME,
        text=message
    ))
    return response

def send_sms_AWS(message, to):
    sns = boto3.client('sns', region_name='us-east-1')
    try:
        response = sns.publish(
            PhoneNumber=to,
            Message=message
        )
        print("Message sent! Message ID:", response['MessageId'])
    except (BotoCoreError, ClientError) as error:
        print("Failed to send message:", error)

def send_sms_DEPRECATED(text, to):
    message = twilio_client.messages.create(
        body=text,
        to=to,
        from_=None
    )
    return message

if __name__ == '__main__':
    response = send_sms('test message 2', '447827810219')
    print(response)