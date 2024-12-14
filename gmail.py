from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.cloud import pubsub_v1
import pickle
import os
from google.cloud import pubsub_v1
import base64
import json
import time

# Define the scope for Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def set_gmail_watch(service, topic_name):
    request = {
        'labelIds': ['INBOX'],
        'topicName': topic_name
    }
    response = service.users().watch(userId='me', body=request).execute()
    return response

def check_inbox(service, history_id):
    response = service.users().history().list(userId='me', startHistoryId=history_id).execute()
    messages = response.get('history', [])
    for history_item in messages:
        for message in history_item.get('messages', []):
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            print(f"New Email: {subject}")
    return response.get('historyId', history_id)







def listen_for_messages(project_id, subscription_name):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    def callback(message):
        print(f"Received message: {message.data}")
        # Acknowledge the message
        message.ack()

        # Extract email ID from the Pub/Sub notification
        notification = json.loads(message.data)
        email_id = notification.get('historyId')

        # Fetch and save the email
        if email_id:
            print(email_id)

    subscriber.subscribe(subscription_path, callback=callback)
    print(f"Listening for messages on {subscription_path}...")

    while True:
        time.sleep(10)

def authenticate_gmail():
    creds = None
    # Load credentials from a file, if available
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no credentials available, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Create Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service







def list_incoming_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=10).execute()
    messages = results.get('messages', [])
    
    for message in messages[:1]:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        #print(f"From: {msg['payload']['headers']}")
        #print(f"Snippet: {msg['snippet']}")
        print(msg.keys())
        print('-' * 40)

def process_new_email(service, message_data):
    """Process new email when notified."""
    # Decode the message data
    message_json = json.loads(base64.urlsafe_b64decode(message_data).decode('utf-8'))
    history_id = message_json.get('historyId')

    if history_id:
        print(f"New email detected, History ID: {history_id}")
        # Get details of new emails using the history API
        history = service.users().history().list(userId='me', startHistoryId=history_id).execute()
        messages = history.get('history', [])
        
        for record in messages:
            for message in record.get('messages', []):
                email_id = message['id']
                email = service.users().messages().get(userId='me', id=email_id, format='full').execute()
                print("Email Content:")
                print(json.dumps(email, indent=2))

def listen_to_emails(subscription_name, service):
    """Continuously listen for email notifications."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = f"projects/YOUR_PROJECT_ID/subscriptions/{subscription_name}"

    def callback(message):
        print(f"Received message: {message.data}")
        process_new_email(service, message.data)
        message.ack()

    print(f"Listening for messages on {subscription_path}...")
    subscriber.subscribe(subscription_path, callback=callback)

    import time
    while True:
        time.sleep(10)


def get_top_email(service):
    """
    Fetches and prints the content of the most recent email in the Gmail inbox.
    Args:
        service: The authenticated Gmail API service instance.
    """
    # Get the list of messages from the inbox
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=1).execute()
    messages = results.get('messages', [])

    if not messages:
        return

    # Get the ID of the most recent email
    top_message_id = messages[0]['id']

    # Fetch the email content
    message = service.users().messages().get(userId='me', id=top_message_id, format='full').execute()

    # Parse and print the email details
    payload = message.get('payload', {})
    headers = payload.get('headers', [])
    body = payload.get('body', {}).get('data')

    # Extract email subject and sender
    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
    sender = next((header['value'] for header in headers if header['name'] == 'From'), "Unknown Sender")

    yield subject
    yield sender

    content = ''

    # Decode the email body if available
    import base64
    if body:
        email_body = base64.urlsafe_b64decode(body).decode('utf-8')
        content += email_body
    else:
        # Handle multipart emails
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                part_body = part.get('body', {}).get('data')
                if part_body:
                    email_body = base64.urlsafe_b64decode(part_body).decode('utf-8')
                    content += email_body
                    break

    yield content

if __name__ == "__main__":
    service = authenticate_gmail()
    listen_to_emails('gmail-pubsub-sub', service)
    #watch_emails(service)