import requests
import json
from .models import Universe, Quest, Question, Option, ScoreCategory, Collectible, QuestRewardCollection, QuestGameplayImages, Character, News
import anthropic
from django.db import transaction
import requests
import mimetypes
import uuid
from http import HTTPStatus
import boto3
import time

from django.shortcuts import get_object_or_404
from openai import OpenAI
from django.core.cache import cache
from django.conf import settings
from urllib.parse import urlparse
from .serializers import *
from common.utils import *
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from structlog import get_logger
from qverse.celery_manager import celery_app
# from phi.agent import Agent
# from phi.model.openai import OpenAIChat
# from phi.tools.duckduckgo import DuckDuckGo
from pathlib import Path

import os
import uuid
from pathlib import Path


ELEVEN_LABS_API_KEY = settings.ELEVEN_LABS_API_KEY
OPEN_AI_API_KEY = settings.OPEN_AI_API_KEY


logger = get_logger()

MODEL= {
    'text_model': "gpt-3.5-turbo-instruct",
    'image_model': "dall-e-3"
}

# Claude API configuration
CLAUDE_API_KEY = settings.CLAUDE_API_KEY

AWS_ACCESS_KEY_ID=settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=settings.AWS_SECRET_ACCESS_KEY

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def get_s3_base_url(base_url):
    return f"https://{base_url}.s3.ap-south-1.amazonaws.com"


S3_UNIVERSE_BASE_URL=get_s3_base_url('qverse-universe-test')

def query_claude(prompt):
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=8192,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"}
            ]
        )
        return '{'+message.content[0].text
    except Exception as e:
        logger.info("Failed to query claude, trying again to check if timeout", er=e)
        time.sleep(5)
        # if timeout error, retry
        try:
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error("Failed to query claude", er=e)
            raise


def get_generate_universe_prompt(universe_description):
    prompt = f"""
        Create a game universe for the below description 
        {universe_description}.
        The universe should be rich in detail and provide a foundation for multiple quests.
        Generate main characters which should be a list of characters with their name, role, description, voice description, look description which will be used in quests.
        Format the response as a JSON object with the following structure:
        {{
            "name": "string",
            "description": "string",
            "key_elements": ["string", "string", "string"],
            "main_characters": [
                {{"name": "string", "role": "string", "description": "string", "image_description":"string", "voice_description": "string"}} for _ in range(4)
            ]
        }}
        The key_elements should be a list of important aspects or themes of this universe that can be referenced in quests and questions.
        """
    return prompt

@transaction.atomic
def generate_universe(universe_description, prompt = None):
    yield {'status': 'Generating universe data'}

    if not prompt:
        prompt = get_generate_universe_prompt(universe_description)

    yield {'status': 'Prompt generated'}

    response = query_claude(prompt)
    data = json.loads(response)
    
    yield {'status': 'Adding universe in database'}
    universe = Universe.objects.create(
        universe_name=data['name'],
        description=data['description'],
        key_elements=json.dumps(data['key_elements']),
        main_characters=json.dumps(data['main_characters']),
        slug=generate_slug(data['name']) 
    )
    yield {'status': 'Universe created'}

    # Save the characters in the character model as well
    for character in data['main_characters']:
        Character.objects.create(
            universe=universe,
            name=character['name'],
            role=character['role'],
            description=character['description'],
            image_description=character['image_description'],
            voice_description=character['voice_description'],
            slug= generate_slug(character['name'])
        )
    yield {'status': 'Characters created', 'universe_id': universe.id}
    
    return universe.id


def generate_quest_prompt(universe_id, quest_prompt = None, max_questions=9):
    universe = Universe.objects.get(id=universe_id)
    key_elements = json.loads(universe.key_elements)
    main_characters = get_main_characters_migrated(universe_id)

    prompt = f"""
    Create a quest for the universe: "{universe.universe_name}".
    Universe description: {universe.description}
    The Universe has the following characters with their respective descriptions:
    {', '.join([f"{c['name']} ({c['role']}) - {c['description']}" for c in main_characters])} \
    Key elements of the universe: {', '.join(key_elements)} \
    {'The quest\'s description is as follows ' + quest_prompt if quest_prompt else ''} \
    The quest should have a compelling story with characters that relate to the universe's themes.\
    Provide a description of what music or sound effects would be used in the quest as background audio.\
    The audio description should make it clear on what instruments are used, the tempo, and the mood of the audio. There should not be any vocals in the audio. The instruments used should be related to the universe's theme.\
    Make sure the audio description is detailed and is restricted to 450 characters.\
    Add instruction in the audio description to make sure the audio doesn't contain vocals and it starts and ends with same note, velocity and tempo so that it can be looped.\
    Also, add a description of the background audio that will be played during the gameplay of the quest and it should enhance the gameplay.\
    It will have a maximum of {max_questions} questions.
    The quest score for each player will be based on the three score_categories. Each category will have a description and a name. The score will be calculated based on the player's choices in the questions.
    Format the response as a JSON object with the following structure:
    {{
        "name": "string",
        "description": "string",
        "main_characters": [
            {{"name": "string", "role": "string", "description": "string"}} for _ in range(4)
        ],
        "story_outline": ["string", "string", "string"],
        "intro": "string",
        "background_audio_description": "string",
        "score_categories": [{{"category_name": "string", "description": "string"}} for _ in range(3)]
    }}
    The story_outline should be a list of key plot points that will guide the questions.
    """

    return prompt


@transaction.atomic
def generate_quest(universe_id, quest_prompt=None,max_questions=9):
    '''
    Generates a quest for the given universe.
    This does not generate questions for the quest. Use generate_question for that.
    This does not generate assets like audio/video. Use generate_quest_assets for that.
    '''
    
    prompt = generate_quest_prompt(universe_id, quest_prompt, max_questions)
    response = query_claude(prompt)
    data = json.loads(response)

    quest = Quest.objects.create(
        universe_id=universe_id,
        quest_name=data['name'],
        intro = data['intro'],
        description=data['description'],
        main_characters=json.dumps(data['main_characters']),
        story_outline=json.dumps(data['story_outline']),
        max_questions=max_questions,
        slug=generate_slug(data['name']),
        background_audio_description=data['background_audio_description']
    )

    # create score categories for the quest from the response
    for category in data['score_categories']:
        ScoreCategory.objects.create(
            quest=quest,
            name=category['category_name'],
            description=category['description']
        )

    return quest.id



@transaction.atomic
def generate_question(quest_id, prev_option_id=None, num_of_options=2):
    quest = Quest.objects.get(id=quest_id)
    universe = quest.universe
    prev_option = Option.objects.get(id=prev_option_id) if prev_option_id else None
    
    # check if max questions are reached
    # to check this we have to backtrack from current question to 1st question 
    # and count the number of questions

    questions_in_path = 0

    if prev_option:
        first_question = prev_option.question

        while first_question.parent_option:
            questions_in_path += 1
            first_question = first_question.parent_option.question

    if questions_in_path >= quest.max_questions:
        return None
    
    main_characters = json.loads(quest.main_characters)
    story_outline   = json.loads(quest.story_outline)
    key_elements    = json.loads(universe.key_elements)

    # get score categories for the quest
    score_categories = ScoreCategory.objects.filter(quest_id=quest_id).values('id', 'name', 'description')

    previous_question = prev_option.question if prev_option else None
    if previous_question:
        options_in_previous_question = Option.objects.filter(question=previous_question).exclude(pk=prev_option_id)
    
    prompt = f"""Generate a new question for the quest: "{quest.quest_name}" in the universe: "{universe.universe_name}".
    Universe key elements: {', '.join(key_elements)}
    Quest description: {quest.description}
    This quest has maximum of {quest.max_questions} questions and this is question number {questions_in_path+1}.
    Main characters: {', '.join([f"{c['name']} ({c['role']})" for c in main_characters])}
    Story outline: {', '.join(story_outline)}
    Previous question: "{prev_option.question.question_text if prev_option else 'Initial question'}"
    Previous selected option: "{prev_option.option_text if prev_option else 'N/A'}"
    Option that was selected in the previous question: {', '.join([option.option_text for option in options_in_previous_question]) if prev_option else 'N/A'}
    Create a question that advances the story and relates to the universe's themes. Irrespective of what option is choosen, the story should progress positively.
    The question should be engaging. The question should be limited to 150 characters at max. The question should not contain phrases like "What do you think", "What would you do", "How will you", etc rather it should be like a description of a scenario which the player has to respond to.
    Provide {num_of_options} options that offer meaningful choices and potentially different story directions.\
    The option should be limited to 70 characters at max.\
    Provide the characters involved in the question.\
    Each option modifies the score of the player for the below score categories. Provide the points in score_rewards for each category that the player will receive if they choose this option. The points can be positive or negative.
    Score categories: {', '.join([f"ID: {category['id']}  Name: {category['name']}  Description: ({category['description']})" for category in score_categories])}
    Format the response as a JSON object with the following structure.
    {{
        "text": "string",
        "options": [
            {{
                "text": "string",
                "score_rewards": {{"score_category_id": points, "score_category_id": points}}
            }} for _ in range(num_of_options)
        ],
        "characters" : ["string", "string"]
    }}
    """
    response = query_claude(prompt)
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        try:
            json.loads(response.replace('""', '"'))
        except json.JSONDecodeError as e:
            logger.error("Failed to decode response from claude", response=response, er=e)
            raise

    question_text=data['text']

    question = Question.objects.create(
        quest=quest,
        question_text=question_text,
        characters=json.dumps(data['characters']),
        parent_option=prev_option,
        question_number=questions_in_path+1
    )
    
    for option_data in data['options']:
        option_obj =  Option.objects.create(
            question=question,
            option_text=option_data['text']
        )

        # store the score rewards for the option
        for score_category_id, points in option_data['score_rewards'].items():
            option_obj.score_rewards[score_category_id] = points
        option_obj.save()
    
    if prev_option:
        prev_option.next_question = question
        prev_option.save()

    return question.id


def get_quest_question(quest_id, prev_option_id, num_of_options=2):
    if prev_option_id:
        prev_option = Option.objects.get(id=prev_option_id)
        if prev_option.next_question:
            if not prev_option.next_question.image_file_path:
                prev_option.next_question.save()
            question = prev_option.next_question
        else:
            new_question = generate_question(quest_id, prev_option_id, num_of_options)
            if new_question:
                question = Question.objects.get(id=new_question)
            else:
                return None
    else:
        # check if the first question for the quest is already generated
        question =  Question.objects.filter(quest_id=quest_id).first()
        if not question:
            question = Question.objects.get(id=generate_question(quest_id, None, num_of_options))
        
        if not question:
            return None
    
    return QuestionSerializer(question).data


def upload_audio_from_url(input_url, output_path):
    '''
    uploads the audio file to s3
    input_url: url of the audio file
    output_path: s3 path to upload the audio

    returns path of the uploaded audio
    '''
    try:
        # if no output path is provded, use a test path

        if not output_path:
            output_path = f"test"

        # get the audio file
        response = requests.get(input_url)
        if response.status_code == HTTPStatus.OK:
            audio_data = response.content
            content_type = get_mime_type(input_url)
            audio_format = get_file_extension(input_url)

            # take the output path and add filename to it. the file name is a uuid
            # UNIVERSE_BASE_URL is the base url of the s3 bucket
            output_path = output_path + '/' + str(uuid.uuid4()) + audio_format

            # upload the audio to s3
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3.put_object(Body=audio_data,
                            Bucket='qverse-universe-test',
                            Key=output_path,
                            ContentType=content_type,
                            ACL='public-read')
            
            # return the url of the uploaded audio
            return S3_UNIVERSE_BASE_URL+ '/' + output_path
        
    except Exception as e:
        logger.error("Failed to upload audio to S3", er=e)
        return False
    

def upload_image_from_url(input_url, output_path):
    '''
    uploads the image file to s3
    input_url: url of the image file
    output_path: s3 path to upload the image

    returns path of the uploaded image
    '''
    try:
        # if no output path is provded, use a test path

        if not output_path:
            output_path = f"test"

        # get the image file
        response = requests.get(input_url)
        if response.status_code == HTTPStatus.OK:
            image_data = response.content
            img_format = get_file_extension(input_url)
            content_type = get_mime_type(input_url)

            # take the output path and add filename to it. the file name is a uuid
            # UNIVERSE_BASE_URL is the base url of the s3 bucket
            output_path = output_path + '/' + str(uuid.uuid4()) + img_format

            # upload the image to s3
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3.put_object(Body=image_data,
                            Bucket='qverse-universe-test',
                            Key=output_path,
                            ContentType=content_type,
                            ACL='public-read')
            
            # return the url of the uploaded image
            return S3_UNIVERSE_BASE_URL+ '/' + output_path

    except Exception as e:
        logger.error("Failed to upload image to S3", er=e)
        return False



def upload_audio_from_input_path(input_path, output_path):
    '''
    uploads the audio file to s3
    input_path: local file path of the audio
    output_path: s3 path to upload the audio

    returns path of the uploaded audio
    '''
    try:
        # if no output path is provded, use a test path

        if not output_path:
            output_path = f"test"

        # get the audio file
        with open(input_path, 'rb') as audio_file:
            audio_data = audio_file.read()
            file_name = input_path.split('/')[-1]
            audio_format = file_name.split('.')[-1]

            # take the output path and add filename to it. the file name is a uuid
            # UNIVERSE_BASE_URL is the base url of the s3 bucket
            output_path = output_path + '/' + str(uuid.uuid4()) + '.'+ audio_format
            content_type = mimetypes.types_map['.' + audio_format]

            # upload the audio to s3
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3.put_object(Body=audio_data,
                            Bucket='qverse-universe-test',
                            Key=output_path,
                            ContentType=content_type,
                            ACL='public-read')
            
            # return the url of the uploaded audio
            return S3_UNIVERSE_BASE_URL+ '/' + output_path
    
    except Exception as e:
        logger.error("Failed to upload audio to S3", er=e)
        return False


def upload_raw_audio(audio, output_path):
    '''
    uploads the audio file to s3
    input_path: raw bytes of the audio
    output_path: s3 path to upload the audio

    returns path of the uploaded audio
    '''
    try:
        # if no output path is provded, use a test path

        if not output_path:
            output_path = f"test"

        # take the output path and add filename to it. the file name is a uuid
        # UNIVERSE_BASE_URL is the base url of the s3 bucket
        output_path = output_path + '/' + str(uuid.uuid4()) + '.mp3'

        # upload the audio to s3
        s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        s3.put_object(Body=audio,
                        Bucket='qverse-universe-test',
                        Key=output_path,
                        ContentType='audio/mpeg',
                        ACL='public-read')
        
        # return the url of the uploaded audio
        return S3_UNIVERSE_BASE_URL+ '/' + output_path

    except Exception as e:
        logger.error("Failed to upload audio to S3", er=e)
        return False


def upload_image_from_input_path(input_path, output_path):
    '''
    uploads the image file to s3
    input_path: local file path of the image
    output_path: s3 path to upload the image

    returns path of the uploaded image
    '''
    try:
        # if no output path is provded, use a test path

        if not output_path:
            output_path = f"test"

        # get the image file
        with open(input_path, 'rb') as image_file:
            image_data = image_file.read()
            file_name = input_path.split('/')[-1]
            img_format = file_name.split('.')[-1]

            # take the output path and add filename to it. the file name is a uuid
            # UNIVERSE_BASE_URL is the base url of the s3 bucket
            output_path = output_path + '/' + str(uuid.uuid4()) + '.'+ img_format
            content_type = mimetypes.types_map['.' + img_format]

            # upload the image to s3
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3.put_object(Body=image_data,
                            Bucket='qverse-universe-test',
                            Key=output_path,
                            ContentType=content_type,
                            ACL='public-read')
            
            # return the url of the uploaded image
            return S3_UNIVERSE_BASE_URL+ '/' + output_path

    except Exception as e:
        logger.error("Failed to upload image to S3", er=e)
        return False
    

def generate_image(prompt):
    '''
    generates image for the given prompt

    returns url of the generated image. this url is usually signed and is valid for a short period of time

    Note:
        This function requires an OpenAI API key to be set as an environment variable 'OPEN_AI_API_KEY'.
        It utilizes the DALL-E model for image generation.
        The DALL-E-3 model is used with a fixed number of images generated (n=1).
    '''
    # if the generation fails retry 3 times with a delay of 5 seconds

    # add generic instructions in prompt to prevent any content which can be harmful
    prompt = f"""
    {prompt}
    Make sure the image generated doesn't contain any harmful content like violence, nudity, etc. Also, make sure the image doesn't contain any text
    """

    attempts = 0
    try:
        while(attempts<3):
            try:
                client = OpenAI(api_key= settings.OPEN_AI_API_KEY)
                response = client.images.generate(
                    model=MODEL['image_model'],
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                if response is None:
                    logger.error("response is none in generate_image", response=response)
                else:
                    image_link= response.data[0].url
                    return image_link
            except Exception as e:
                logger.error('Something went wrong while generating image from dalle',e=e, attempts=attempts)
            
            # add delay
            time.sleep(5)
            attempts+=1

    except Exception as e:
        logger.error('Something went wrong while generating image',e=e)
        return None


def get_main_characters_migrated(universe_id):
    '''
    returns the main characters in the given universe
    '''
    # Get characters
    characters = Character.objects.filter(universe_id=universe_id)
    characters = [{'name': c.name, 'description': c.description, 'image': c.image_path, 'role': c.role, 'slug': c.slug} for c in characters]

    return characters


@transaction.atomic
def generate_trivia(trivia_prompt=None, no_of_questions=10):
    '''
    Generates a trivia with the given prompt and number of questions, 
    then saves the trivia, questions, options, and characters to the database.
    '''

    prompt = generate_trivia_prompt(trivia_prompt, no_of_questions)
    response = query_claude(prompt)
    data = json.loads(response)
    
    trivia_name = data.get('name')
    trivia_description = data.get('description')
    thumbnail_description = data.get('thumbnail_description')
    background_audio_description = data.get('background_audio_description')
    main_characters_data = data.get('main_characters', [])
    questions_data = data.get('questions', [])

    trivia = Trivia.objects.create(
        name=trivia_name,
        description=trivia_description,
    )  
        
    trivia_thumbnail_url  = generate_image(thumbnail_description)
    trivia_thumbnail_url = upload_image_from_url(trivia_thumbnail_url, f"trivia/{trivia.id}")
    audio_url = generate_trivia_audio(trivia.id, background_audio_description)

    trivia.audio_url = audio_url
    trivia.thumbnail = trivia_thumbnail_url
    trivia.save()

    previous_question = None
    for index, question_data in enumerate(questions_data):
        question_image_url = generate_image(question_data['question_image_description'])
        question_image_url = upload_image_from_url(question_image_url, f"trivia/{trivia.id}/question/{index}")

        trivia_question = TriviaQuestion.objects.create(
            trivia=trivia,
            question_text=question_data['question_text'],
            question_number=question_data['question_number'],
            options=question_data['options'],
            image=question_image_url
        )

        if previous_question:
            trivia_question.previous_question = previous_question  
            previous_question.next_question = trivia_question  
            previous_question.save()
        
        trivia_question.save()

        previous_question = trivia_question

    return data


def generate_trivia_prompt(trivia_prompt, no_of_questions):
    """
    Generates a detailed prompt for creating trivia, focusing on a specific topic if provided.
    
    Parameters:
    trivia_prompt (str): Description or topic for the trivia.
    no_of_questions (int): Number of questions to include in the trivia.
    
    Returns:
    str: A formatted prompt for trivia creation.
    """

    prompt = f"""
    Create a trivia with {no_of_questions} questions based on the description below.
    {'Topic: ' + trivia_prompt if trivia_prompt else 'Create a general trivia based on some topic.'}
    
    Each question should be related to the topic and include:
    - Clear and concise question text , with a word limit of 20 words and the question should not be dependent on any external thing like audio , video , images etc.
    - 4 multiple-choice options with only one correct answer each option should have a word limit of 5.
    - A brief description of the image to accompany each question, relevant to the topic and the question.
    
    Additionally, provide the following details for the trivia:
    - A title (name) that captures the essence of the trivia.
    - A description summarizing the trivia theme and what players will learn or experience.
    - A thumbnail description for the trivia, to visually represent the theme.
    - A brief outline or summary of the background audio that will be played, enhancing the game experience.
    - A list of some main characters (if applicable to the story), with names, roles, and descriptions.
    - A background audio description that sets the mood and tone for the trivia game, specifying the type of instrumental sounds and effects.


    Format the output as a JSON object with this structure:
    {{
        "name": "string",
        "description": "string", 
        "thumbnail_description": "string", ( maximum of 250 characters )
        "background_audio_description": "string", ( maximum of 100 characters )
        "main_characters": [
            {{"name": "string", "role": "string", "description": "string"}}
            for each character (up to 4)
        ],

        "questions": [
            {{
                "question_text": "string",
                "question_number": "integer" (1 to {no_of_questions}),
                "options": [
                    {{"text": "string", "is_correct": "boolean"}},
                    for each option   
                ],
                "question_image_description": "string" ( Provide a clear, contextually relevant image description that accurately represents the question's topic without introducing misleading elements or unrelated information. The background image should not indicate the correct answer but should simply serve as a representation of the question.)
            }}
            for each question
        ]
    }}
    """

    return prompt


def generate_trivia_audio(trivia_id, prompt):
    '''
    Generates a background audio for the given trivia using the prompt given.
    '''
   
    trivia = get_object_or_404(Trivia, pk=trivia_id)

    # if trivia.audio_url:
    #     return trivia.audio_url

    prompt = f"""Create an instrumental background track for the Trivia game '{trivia.name[:50]}' to enhance gameplay subtly. Follow these guidelines from {prompt[:100]}:

    Important Requirements:
    - Instrumental only, no vocals or loud sounds
    - Professional, smooth, and loopable
    - Soft, non-distracting, with gentle, steady tempo
    """

    client = ElevenLabs(
        api_key=ELEVEN_LABS_API_KEY, 
    )
    result = client.text_to_sound_effects.convert(
        text=prompt,
        # duration_seconds=10,
        prompt_influence=0.7,  # Optional, if not provided will use the default value of 0.3
    )

    # save the audio in a temp file with uuid as name
    audio_path = f"tmp/audio/{str(uuid.uuid4())}.mp3"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    save(result, audio_path)

    audio_url = upload_audio_from_input_path(audio_path, f"trivia/{trivia.id}/audio")

    return audio_url


def get_news_category(prompt):

    category_promt = f"""
        Categorize the news based on the given prompt into one of the following categories:
        1. {News.NewsTypes.MYSTERY_CRIME}
        2. {News.NewsTypes.TECH_INNOVATIONS}
        3. {News.NewsTypes.HISTORICAL_EVENTS}
        4. {News.NewsTypes.OTHERS}
        5. {News.NewsTypes.ENVIRONMENTAL_AWARENESS}
        6. {News.NewsTypes.CULTURAL_TRADITIONS}
        7. {News.NewsTypes.HEALTH_WELLNESS}
        8. {News.NewsTypes.ART_MOVEMENTS}
        9. {News.NewsTypes.SCIENCE_DISCOVERIES}
        10. {News.NewsTypes.ENTREPRENEURSHIP_STARTUPS}
        11. {News.NewsTypes.POLITICAL}
        12. {News.NewsTypes.SPORTS}
        13. {News.NewsTypes.WAR}
        14. {News.NewsTypes.CELEBRITIES}

        Prompt: {prompt}

        The response should be a JSON object with the following structure:
        {{
            "category": "string"
        }}
    """

    response = query_claude(category_promt)
    data = json.loads(response)
    category = data['category']

    return getattr(News.NewsTypes, category.upper(), News.NewsTypes.OTHERS)


# def get_news(promt):
#     '''
#     Generates news based on the given prompt using PhiData's OpenAI model
#     '''
#     web_agent = Agent(
#     name="Web Agent",
#     model=OpenAIChat(id="gpt-4o",api_key=OPEN_AI_API_KEY),  
#     tools=[DuckDuckGo()],
#     instructions=[
#         "Provide the response in the form of a JSON array. "
#         "Each element in the array should be a JSON object with the following structure: "
#         "[{ 'Title': '<string max Char lenght of 255 >', 'date': '<YYYY-MM-DD>', "
#         "'readable-content': '<string that resembles how a news anchor would report the news>', "
#         "'source': '<string>', 'link': '<URL>' }]. "
#         "Ensure the 'Title' summarizes the news, "
#         "and the 'readable-content' mimics a spoken news report. "
#         "All fields should be properly populated and concise."
#     ],
#     show_tool_calls=True,
#     markdown=True,
#     )

#     response = web_agent.run(promt)
#     formatted_response = query_claude("""
#     You are an expert at formatting and structuring unstructured content. Your task is to transform the given news content into JSON format with the following schema:

#     {
#         "Title": "<string>", ( max 255 characters )
#         "Date": "<YYYY-MM-DD>",
#         "ReadableContent": "<string>",
#         "Source": "<string>",
#         "Link": "<URL>",
#         "Thumbanil-description": "<string>" ( description of the image that will be used as thumbnail , max 150 characters )
#     }

#     **Instructions:**
#     1. Extract relevant data to populate the JSON structure, ensuring the fields are appropriately filled.
#     2. Always assume the input contains:
#     - A title line indicating the main headline.
#     - A publication date in standard formats .
#     - A body section representing the readable content.
#     - A source label indicating the origin (e.g., Reuters, BBC).
#     - A hyperlink or source URL.
#     3. If any key information is missing, mark its value as `null` in the JSON.
#     4. Validate the final JSON format to ensure it adheres to JSON syntax rules (double quotes for keys and string values, commas between items).

#     Now process the input below:
#     {response.content}
#     """)

#     data = json.loads(formatted_response)
#     return data


def generate_voice_over(
    text,
    voice_style="professional",
    output_dir=Path("output")
):
    """Generates voice-over using ElevenLabs or OpenAI."""
    try:
        # Define the output file path
        output_path = str(output_dir / "audio" / f"{uuid.uuid4()}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Map voice styles to ElevenLabs voices
        voice_mapping = {
            "professional": "Adam",
            "casual": "Sam",
            "energetic": "Josh",
            "storyteller": "Brian",
            "dramatic": "Patrick"
        }
        voice = voice_mapping.get(voice_style, "Adam")

        # Generate audio using ElevenLabs
        elevenlabs_client = ElevenLabs(api_key=ELEVEN_LABS_API_KEY)
        audio = elevenlabs_client.generate(
            text=text,
            voice=voice,
            model="eleven_multilingual_v2"
        )
        # Save the audio
        save(audio, output_path)
        
        # Upload to S3
        s3_url = upload_audio_from_input_path(output_path, "news/audio")
        
        # Clean up local file
        try:
            os.remove(output_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary voice over file: {e}")
        
        return s3_url

    except Exception as e:
        logger.error(f"Error generating voice over: {e}")
        raise


def generate_news(prompt):
    '''
    Generates news based on the given prompt
    '''
    category = get_news_category(prompt)
    news_response=""
    # news_response = get_news(prompt)  
    audio_url = generate_voice_over(news_response['ReadableContent'], voice_style="professional")
    thumbnail_url = generate_image(news_response['Thumbanil-description'])
    thumbnail_url = upload_image_from_url(thumbnail_url, f"news/")
    
    news = News.objects.create(
        name=news_response['Title'],
        category=category,
        description=news_response['ReadableContent'],
        thumbnail=thumbnail_url,
        audio_url=audio_url,
        video_url=None,
    )
    
    return news