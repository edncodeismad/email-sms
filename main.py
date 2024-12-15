from gmail import authenticate_gmail
from tools import send_llm, send_sms
import time
import asyncio
import os
import pickle

USER_PHONE_NUMBER = ''

GMAIL_SERVICE = authenticate_gmail()

reminders = {}
last_content = ''

tasks = {
    1: 'add reminder',
    2: 'list reminders',
    3: 'delete reminder'
}

def list_reminders(): #
    return ' -- '.join([f'{num}: {msg}' for num, msg in reminders.items()])

def add_reminder(input_text): #
    system = "Your task is to add this message to the list of important reminders that the user has. Correct the grammar/ make the new reminder more concise such that all the important information is preserved, and return this new reminder. If the new reminder is already present in the list, or there is a very similar one, return only '__warning__' and nothing else."
    message = f"New reminder: {input_text}.\n Existing reminders: {list_reminders()}"
    response = send_llm(system, message)
    if response == '__warning__':
        text = "A similar reminder is already on your list. Consider double checking your existing reminders."
        send_sms(text, USER_PHONE_NUMBER)
        return
    elif len(reminders.keys()) == 0:
        reminders[1] = response
    else:
        reminders[max(reminders.keys())+1] = response
    send_sms(f'New reminder added: {response}', USER_PHONE_NUMBER)

def get_reminders(): #
    if len(reminders.keys()) == 0:
        send_sms('You have no reminders set.', USER_PHONE_NUMBER)
    send_sms(list_reminders(), USER_PHONE_NUMBER)

def remove_reminder(num): #
    global reminders
    del reminders[num]
    reminders = {k+1: v for k, v in enumerate(reminders.values())}

def send_alert(email, max_chars=5000):
    if len(reminders.keys()) == 0:
        return
    system_message = """
    Your task is to determine whether or not the given email text is relevant to one or more of the reminders listed in the user message.
    Consider that the recipient of the email should only be notified if the email is directly relevant to the given reminder.
    If the email is relevant to a particular reminder, respond with the number of that reminder AND NOTHING ELSE.
    If the email is relevant to multiple reminders, respond with their number separated by ampersands (&), eg. '2&4&5'.
    If the email is not relevant to any reminder, respond with the digit zero (0) AND NOTHING ELSE.
    """

    if len(email) > max_chars:
        email_chunks = None
    else:
        input = f"LIST OF REMINDERS: {list_reminders()}\nEMAIL CONTENT: {email}"
        result = send_llm(system_message, input)
        if result == '0':
            return
        results = [int(n) for n in result.split('&')]

    rems = []
    for r in results:
        rems.append(reminders[r])
    joined = '\n'.join(rems)
    text = f"Hey! You just got an email that is relevant to the following reminders: \n{joined}"
    send_sms(text, USER_PHONE_NUMBER)

def get_todays_summary():
    pass

def check_inbox(service, history_id): #
    response = service.users().history().list(userId='me', startHistoryId=history_id).execute()
    messages = response.get('history', [])
    for history_item in messages:
        for message in history_item.get('messages', []):
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            payload = msg.get('payload', {})
            body_data = None
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body_data = part.get('body', {}).get('data')
                        break
            else:
                body_data = payload.get('body', {}).get('data')
            if body_data:
                import base64
                decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8')
            else:
                decoded_body = "No Content"

            email = f"SUBJECT: {subject}, SENDER: {sender}, EMAIL CONTENT: {decoded_body}"
            #print(email)
            send_alert(email)
    return response.get('historyId', history_id)


if __name__ == '__main__':
    history_id = GMAIL_SERVICE.users().getProfile(userId='me').execute()['historyId']
    # implement these async so can run concurrently
    while True:
        print('checking inbox ...')
        history_id = check_inbox(GMAIL_SERVICE, history_id)
        time.sleep(10)

