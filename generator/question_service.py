from .service import *
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import urllib

ELEVEN_LABS_API_KEY = settings.ELEVEN_LABS_API_KEY

def generate_question_assets(question_id):
    '''
    generates images/audio/video for question
    '''
    generate_question_image(question_id)
    generate_question_speech_openai(question_id)


def generate_question_image(question_id):
    '''
    generates image for the given question
    '''
    # get question
    question = get_object_or_404(Question, pk=question_id)

    # if image is already present, return the url
    if question.image_file_path:
        return question.image_file_path

    # prompt = f"""
    # In a gameplay, a question is displayed to the user. The question is as follows:
    # {question.question_text}
    # The characters involved in this question are: {', '.join(json.loads(question.characters))}.
    # The question is a part of the quest: {question.quest.quest_name} in the universe: {question.quest.universe.universe_name}.
    # The quest description is as follows: {question.quest.description}.
    # The universe description is as follows: {question.quest.universe.description}.
    # Generate an image for the question. Do not add any text to the image. The image should be visually appealing and should represent the question.
    # """

    # image_url = generate_image(prompt)
    # image_url = upload_image_from_url(image_url, f"universe/{question.quest.universe.id}/quest/{question.quest.id}/question/{question.id}")

    # use QuestGameplayImages to fetch the images and randomly assign the image to the question
    quest_gameplay_images = QuestGameplayImages.objects.filter(quest=question.quest)
    if quest_gameplay_images:
        image_url = random.choice(quest_gameplay_images).image_path
    else:
        image_url = None

    # store the image_url in question
    question.image_file_path = image_url
    question.save()
    return image_url


def generate_question_speech_elevenlabs(question_id):
    '''
    Get the text from the question and generate audio for the same using eleven labs api
    '''
    try:
        question = Question.objects.get(pk=question_id)
        text = question.question_text

        # if the audio is already present, return the url
        if question.audio_file_path:
            return question.audio_file_path

        client = ElevenLabs(
            api_key=ELEVEN_LABS_API_KEY, # Defaults to ELEVEN_API_KEY
            )
        
        if question.quest.universe.narrator_voice_description and len(question.quest.universe.narrator_voice_samples):
            voice = clone_voice(
                voice_name=question.quest.universe.slug,
                voice_description=question.quest.universe.narrator_voice_description,
                voice_files=question.quest.universe.narrator_voice_samples
            )
            audio = client.generate(text=text, voice=voice)
        else:
            audio = client.generate(
            text=text,
            voice="Brian",
            model="eleven_multilingual_v2"
            )

        # save the audio in a temp file with uuid as name
        audio_path = f"tmp/audio/{str(uuid.uuid4())}.mp3"

        # check if the directory exists else create it
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        save(audio, audio_path)

        # upload the audio to s3
        audio_url = upload_audio_from_input_path(audio_path, f"universe/{question.quest.universe.id}/quest/{question.quest.id}/question/{question.id}")
        question.audio_file_path = audio_url
        question.save()
        return audio_url

    except Question.DoesNotExist:
        print(f"Question with id {question_id} does not exist.")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    

def clone_voice(voice_name, voice_description, voice_files:list):
    files= download_files_from_url(voice_files)

    client = ElevenLabs(
                api_key=ELEVEN_LABS_API_KEY, # Defaults to ELEVEN_API_KEY
            )
    
    voice = client.clone(
                name=voice_name,
                files=files,
                description=voice_description, # Optional
            )
    return voice


def download_files_from_url(file_urls:list):
    '''
    returns list of local file paths from the file urls
    '''
    # loop through the file urls and download file in a folder with a unique uuid as folder name
    folder_name = '/temp/'+str(uuid.uuid4())
    os.makedirs(folder_name)
    file_paths = []
    for file_url in file_urls:
        file_path = os.path.join(folder_name, file_url.split('/')[-1])
        urllib.request.urlretrieve(file_url, file_path)
        file_paths.append(file_path)
    return file_paths


def generate_question_speech_openai(question_id):
    '''
    Get the text from the question and generate audio for the same using openai api
    '''
    try:
        question = Question.objects.get(pk=question_id)
        text = question.question_text

        # if the audio is already present, return the url
        if question.audio_file_path:
            return question.audio_file_path

        client = OpenAI(api_key= settings.OPEN_AI_API_KEY)
        
        audio = client.audio.speech.create(
            input=text,
            model='tts-1',
            response_format='mp3',
            voice='shimmer',
            speed=1.0
        )
        
        # save the audio in a temp file with uuid as name
        audio_path = f"tmp/audio/{str(uuid.uuid4())}.mp3"

        # check if the directory exists else create it
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        with open(audio_path, 'wb') as f:
            for chunk in audio.iter_bytes():
                f.write(chunk)
                
        # upload the audio to s3
        audio_url = upload_audio_from_input_path(audio_path, f"universe/{question.quest.universe.id}/quest/{question.quest.id}/question/{question.id}")
        question.audio_file_path = audio_url
        question.save()
        return audio_url

    except Question.DoesNotExist:
        print(f"Question with id {question_id} does not exist.")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")