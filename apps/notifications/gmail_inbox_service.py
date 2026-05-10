"""
Placeholders for future Gmail inbox support.

Real inbound email processing will require Gmail API users.messages.list,
users.messages.get, Gmail watch, Google Cloud Pub/Sub, a public webhook
endpoint, and historyId handling. Nothing in this module is activated
automatically.
"""


def list_recent_messages():
    raise NotImplementedError("Gmail inbox listing is not implemented yet.")


def get_message_detail(message_id):
    raise NotImplementedError("Gmail message detail is not implemented yet.")


def process_incoming_message(message):
    raise NotImplementedError("Incoming Gmail processing is not implemented yet.")
