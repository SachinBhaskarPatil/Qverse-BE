import os, sys 
import re
import json
import time
# sys.path.append('../')
sys.path.append('C:/Users/sbpat/Desktop/qverse_backend/qverse')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qverse.settings")

import django 
from openai import OpenAI
from datetime import date
django.setup(set_prefix=True)

from django.conf import settings
from firebase_admin import messaging, db
from structlog import get_logger 
from django.db import transaction
from user.models import UserProfile, User , LogTable

OPEN_AI_API_KEY = settings.OPEN_AI_API_KEY 
logger = get_logger(script='chat_notification.py')
client = OpenAI(api_key= OPEN_AI_API_KEY)

def serialize_for_json(data):
    """
    Helper function to convert non-serializable objects (like date) to JSON-serializable formats.
    """
    if isinstance(data, dict):
        return {k: serialize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_for_json(i) for i in data]
    elif isinstance(data, date):  # Convert date to string
        return data.isoformat()
    return data

def update_user_details(username, **kwargs):
    """
    Update user and user profile details, logging only changed fields.

    Args:
        username (str): The username of the user to update.
        kwargs: Fields to update (e.g., first_name, last_name, phone, gender, profession, dob).

    Returns:
        User: The updated User instance.
        str: Success message or error message.
    """
    updatable_user_fields = {'first_name', 'phone', 'email'}
    updatable_profile_fields = {'gender', 'profession', 'dob'}

    try:
        # Fetch the user instance
        user = User.objects.get(username=username)
        user_profile, created = UserProfile.objects.get_or_create(user=user)

                # Map "name" to "first_name" for the User model
        if "name" in kwargs:
            kwargs["first_name"] = kwargs.pop("name")


        # Initialize dictionaries to track changes
        prev_state = {}
        new_state = {}
        user_changed = False
        profile_changed = False

        with transaction.atomic():
            # Compare and update User model fields
            for field in updatable_user_fields:
                new_value = kwargs.get(field)
                if new_value is not None and getattr(user, field) != new_value:
                    prev_state[field] = getattr(user, field)
                    new_state[field] = new_value
                    setattr(user, field, new_value)
                    user_changed = True

            # Compare and update UserProfile model fields
            for field in updatable_profile_fields:
                new_value = kwargs.get(field)
                if new_value is not None:
                    # Handle 'dob' conversion
                    if field == 'dob' and isinstance(new_value, str):
                        new_value = date.fromisoformat(new_value)

                    if getattr(user_profile, field) != new_value:
                        prev_state[field] = getattr(user_profile, field)
                        new_state[field] = new_value
                        setattr(user_profile, field, new_value)
                        profile_changed = True

            # Save updates
            if user_changed:
                user.save()
            if profile_changed:
                user_profile.save()

            # Log the changes
            if prev_state and new_state:  # Log only if changes occurred
                LogTable.objects.create(
                    username=user.username,
                    type="profile",
                    prev_state=serialize_for_json(prev_state),
                    new_state=serialize_for_json(new_state)
                )

        return "User details updated successfully."

    except User.DoesNotExist:
         return f"User does not exist."
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Function to send a notification to the user
def send_notification(username, message_data):
    # Extract user prompt from the incoming message data
    # Adjust this key if your incoming data structure differs
    user_input = message_data.get('text', '')
    logger.info("User input extracted", username=username, user_input=user_input)

    response_text, urls = generate_bot_response(username, user_input)

    # Add bot response to the database
    bot_message = {
        "sender": "bot",
        "text": response_text,
        "timestamp": int(time.time() * 1000),
        "media": []
    }
    db.reference(f'/users/{username}/messages').push(bot_message)

    image_url = urls[0] if urls else None

    notification = messaging.Notification(
        title="New Message from Bot",
        body=response_text,
        image=image_url
    )

    message = messaging.Message(
        notification=notification,
        topic=username
    )

    try:
        response = messaging.send(message)
        logger.info("Successfully sent message", response=response)
    except Exception as e:
        logger.error("Error sending message", error=str(e))

def get_thread_id_for_user(username):
    """
    Returns a persistent thread_id for the user.
    If one does not exist, creates a new thread, adds a system message, and stores it.
    """
    user_profile = UserProfile.objects.filter(user__username=username).first()
    if user_profile and user_profile.gpt_thread_id:
        return user_profile.gpt_thread_id
    else:
        # Create a new thread
        thread = client.beta.threads.create()

        # Save thread_id in user profile
        if not user_profile:
            user = User.objects.get(username=username)
            user_profile = UserProfile(user=user)
        user_profile.gpt_thread_id = thread.id
        user_profile.save()
        return thread.id

def generate_bot_response(username, user_prompt):
    """
    Generates a bot response for a given user and prompt.
    
    Args:
        username (str): The username of the user.
        user_prompt (str): The prompt provided by the user.
    
    Returns:
        tuple: A tuple containing the cleaned response text and a list of extracted URLs.
    """
    logger.info("Generating bot response", extra={"username": username, "user_prompt": user_prompt})
    
    try:
        # Get the thread ID for the user
        thread_id = get_thread_id_for_user(username)
        
        # Create a user message in the thread
        user_msg = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=[{"type": "text", "text": user_prompt}]
        )
        logger.info("User message created in thread", extra={"thread_id": thread_id, "user_msg": user_msg})
        
        # Start the assistant run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id="asst_ZLmfSP2ijfikLBrbaQhwVVqQ"
        )
        logger.info("Run started", extra={"run_id": run.id, "thread_id": thread_id})
        
        while True:
            time.sleep(5)

            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                latest_message = messages.data[0] 
                
                response_text = latest_message.content[0].text.value if latest_message.content[0].text.value else ''

                urls = re.findall(r'(https?://\S+)', response_text)
                clean_message = re.sub(r'https?://\S+', '', response_text).strip()
                
                return clean_message, urls
            
            elif run_status.status == 'requires_action':
                logger.info("Run requires action", extra={"run_id": run.id})
                
                required_actions = run_status.required_action.submit_tool_outputs.model_dump()
                logger.debug("Required actions retrieved", extra={"required_actions": required_actions})
                
                tool_outputs = []
                
                for action in required_actions["tool_calls"]:
                    func_name = action['function']['name']
                    arguments = json.loads(action['function']['arguments'])
                    
                    if func_name == "update_user_details":
                        filtered_data = {key: value for key, value in arguments.items() if value}
                        output = update_user_details(username, **filtered_data)
                        
                        tool_outputs.append({
                            "tool_call_id": action['id'],
                            "output": output
                        })
                    
                    else:
                        logger.error("Unknown function called", extra={"function_name": func_name})
                        raise ValueError(f"Unknown function: {func_name}")
                
                if tool_outputs:
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    logger.info("Tool outputs submitted", extra={"tool_outputs": tool_outputs})
            
            else:
                logger.info("Waiting for the assistant to process...", extra={"run_id": run.id})
                time.sleep(5)
        
        return "", []

    except Exception as e:
        logger.exception("An error occurred while generating the bot response")
        return "", []

def listen_to_user_messages(event):
    try:
        if event.event_type == 'put':
            logger.info("Received event", event_type=event.event_type, path=event.path)

            path_parts = event.path.strip('/').split('/')
            if len(path_parts) == 3 and path_parts[1] == 'messages':
                username = path_parts[0]
                message_data = event.data

                if message_data and message_data.get('sender') == 'user':
                    logger.info("Received message from user", username=username, message=message_data)
                    send_notification(username, message_data)
            else:
                logger.info("Non-relevant event", path=event.path)
    except Exception as e:
        logger.error("Error in listener", error=str(e), event_path=event.path)


# Reference to the users collection
ref = db.reference('/users/')
ref.listen(listen_to_user_messages)
