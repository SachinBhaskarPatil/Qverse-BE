import boto3
import time
import json
import re
from openai import OpenAI

from django.conf import settings
from botocore.exceptions import ClientError
from django.core.exceptions import ObjectDoesNotExist
from structlog import get_logger
from .models import User,UserProfile,ContentRecommendation
from generator.models import AudioStory, ShortVideos
from generator.serializers import AudioStorySerializer, ShortVideosSerializer

OPEN_AI_API_KEY = settings.OPEN_AI_API_KEY 
client = OpenAI(api_key= OPEN_AI_API_KEY)
logger = get_logger()

def verify_user_in_pool(access_token):    
    # Initialize the Cognito Identity Provider client

    client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)
    try:
        # Call to get the user details using the access token
        response = client.get_user(
            AccessToken=access_token
        )
        # If successful, the user exists
        logger.info("User exists: %s", response)
        return True
    except ClientError as e:
        # Handle other client errors (e.g., user not found)
        logger.error("Error verifying user: %s", e)
        return False
    

def valid_name(name:str):
    name = name.strip()
    if not bool(name) or not all(char.isalpha() or char.isspace() or char == '.' for char in name):
        return False
    else:
        return True
    
def get_profile_data(user_instance):
    try:
        from .serializers import UserSerializer,UserProfileSerializer
        user_serializer=UserSerializer(user_instance)
        response_data=dict(user_serializer.data)
        user_profile_instance=UserProfile.objects.get(user=user_instance)
        user_profile_serializer=UserProfileSerializer(user_profile_instance)
        response_data.update(dict(user_profile_serializer.data))
        response_data['name']=response_data['first_name']
        response_data.pop('first_name')
        return response_data
    except Exception as e:
        logger.error("Error getting profile data: %s", e)
    
def save_content_recommendation(user_id, content_id, content_type):
    try:
        # Try to get or create the recommendation
        content_recommendation, created = ContentRecommendation.objects.get_or_create(
            user_id=user_id,
            content_id=content_id,
            content_type=content_type
        )
        
        if created:
            logger.info(f"New entry created for user {user_id}, content {content_id}, type {content_type}")
        else:
            logger.info(f"Entry already exists for user {user_id}, content {content_id}, type {content_type}")
        
        return content_recommendation
    
    except Exception as e:
        logger.error(f"Unexpected error occurred while saving recommendation for user {user_id}, content {content_id}, type {content_type}: {str(e)}")
        return None  # Return None in case of error, can also raise if you want to propagate the error

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


def get_recommendations(user_id: str):
    """
    Fetches content recommendations for a given user.
    This function retrieves content recommendations for a user based on their user ID.
    It fetches recommendations from the ContentRecommendation model and categorizes them
    into short videos and audio stories. The function returns a dictionary containing
    serialized data for both types of content.
    Args:
        user_id (str): The ID of the user for whom recommendations are to be fetched.
    Returns:
        dict: A dictionary containing two keys, 'short_videos' and 'audio_stories', each
              holding a list of serialized content data. If an error occurs, returns None.
    """
    try:
        recommendations = ContentRecommendation.objects.filter(user_id=user_id)

        # Initialize dictionaries to hold the recommendations
        short_videos_recommendations = []
        audio_story_recommendations = []

        # Check if recommendations exist
        if recommendations.exists():
            for recommendation in recommendations:
                content_id = recommendation.content_id
                content_type = recommendation.content_type

                # Fetch corresponding content based on content_type
                # if content_type == 'video':
                #     pass
                #     # try:
                #     #     short_video = ShortVideos.objects.get(id=content_id)
                #     #     short_videos_recommendations.append(ShortVideosSerializer(short_video).data)
                #     # except ObjectDoesNotExist:
                #     #     logger.warning(f"ShortVideo with id {content_id} not found.")

                if content_type == 'audio':
                    try:
                        audio_story = AudioStory.objects.get(id=content_id)
                        serialized_audio = AudioStorySerializer(audio_story).data
                        serialized_audio['type'] = 'audio'
                        audio_story_recommendations.append(serialized_audio)
                    except ObjectDoesNotExist:
                        logger.warning(f"AudioStory with id {content_id} not found.")

        # Combine the results in one dictionary

        return audio_story_recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
        return None


def create_recommendations_by_username(username: str):
    """
    Generate personalized content recommendations for a user based on their username.
    This function retrieves user data and conversation history to generate content recommendations
    using an external assistant service. The recommendations are based exclusively on data from a 
    JSON file and are tailored to the user's behavior and preferences.
    Args:
        username (str): The username of the user for whom recommendations are to be generated.
    Returns:
        list: A list of recommended content items. Each item is a dictionary containing the content ID 
              and content type. If an error occurs, an empty list is returned.
    """ 
    try:
        user_prompt="Recommend 10 content items based exclusively on the data provided in the JSON file retrieved from the file search. The recommendations should be personalized according to the user's behavior, inferred from their messages in this conversation thread. The content recommendations must strictly come from the JSON file retrieved from the file search and should not include additional sources. Provide the content recommendations strictly in JSON format, with no additional messages or explanations. Ensure that the recommendations align with the user's preferences, interests, and actions as derived from the entire conversation history. The output should be a valid JSON object, and it must be parseable using Python’s json.loads(). The output should strictly follow this format: {\"recommendations\": [ { }, { } ]}"
        user      = User.objects.get(username=username)
        user_id   = user.id
        thread_id = get_thread_id_for_user(username)
        user_msg = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=[{"type": "text", "text": user_prompt}]
        )
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
                assistant_id="asst_ZLmfSP2ijfikLBrbaQhwVVqQ"
            ) 
        
        logger.info("Run started", extra={"run_id": run.id, "thread_id": thread_id})  
        recommendation=[] 
        while True:
            time.sleep(5)
            run_status = client.beta.threads.runs.retrieve(
                            thread_id=thread_id,
                            run_id=run.id
                        )
            if run_status.status == 'completed':
                messages        = client.beta.threads.messages.list(thread_id=thread_id)
                latest_message  = messages.data[0] 
                raw_string      = latest_message.content[0].text.value if latest_message.content[0].text.value else ''
                cleaned_string  = re.sub(r'```json\n|\n```', '', raw_string)
                cleaned_string  = json.loads(cleaned_string)
                recommendations = cleaned_string['recommendations']
                for recommendation in recommendations:
                    save_content_recommendation(user_id, recommendation['content_id'], recommendation['content_type'])
                return recommendations
    except Exception as e:  
        logger.error("Error getting recommendations: %s", e)
        return []
        