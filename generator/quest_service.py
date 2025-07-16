from .service import *


def generate_quest_thumbnail_image(quest_id):
    '''
    generates thumbnail image for the given quest
    '''
    # get the quest
    quest = get_object_or_404(Quest, pk=quest_id)
    # if quest thumbnail is already present, return the url
    if quest.thumbnail:
        return quest.thumbnail

    prompt = f"""
    Create a thumbnail image for the quest: "{quest.quest_name}" in the universe: "{quest.universe.universe_name}".
    The quest goes as follows:
    {quest.description}
    This quest is a part of the universe with the following description: {quest.universe.description}.
    The quest involves the following main characters: {', '.join([f"{c['name']} ({c['role']})" for c in json.loads(quest.main_characters)])}.
    The story outline for this quest is as follows: {', '.join(json.loads(quest.story_outline))}.
    Do not add any text to the image. The image should be visually appealing and should represent the quest.
    """


    image_url = generate_image(prompt)
    image_url = upload_image_from_url(image_url, f"universe/{quest.universe.id}/quest/{quest.id}")

    quest.thumbnail = image_url
    quest.save()
    return image_url


def get_prompt_for_score_category_icon_image(name, quest_name, description):
    prompt = f"""
    Create an icon for the score category {name} in the quest game of {quest_name} where this category signifies {description}.
    Do not add any text to the icon. The icon should be visually appealing and should represent the category.
    """
    return prompt


def generate_icons_for_score_categories(quest_id):
    '''
    generates icons for the score categories for the given quest
    '''
    score_categories = ScoreCategory.objects.filter(quest_id=quest_id)
    for category in score_categories:
        if category.icon:
            continue
        prompt = get_prompt_for_score_category_icon_image(category.name, category.quest.quest_name, category.description)
        image_url = generate_image(prompt=prompt)
        image_url = upload_image_from_url(image_url, f"universe/{category.quest.universe.id}/quest/{category.quest.id}/score_category/{category.id}")
        category.icon = image_url
        category.save()


def generate_image_for_character_in_quest(quest_id):
    quest = Quest.objects.get(pk=quest_id)
    universe = quest.universe
    main_characters = json.loads(quest.main_characters)
    story_outline = json.loads(quest.story_outline)
    story_outline = ''.join(story_outline)

    universe_main_characters = get_main_characters_migrated(universe_id=universe.id)

    for i in range(len(main_characters)):
        # if image is already present, skip
        if main_characters[i].get('image'):
            continue

        # some characters are reused from the universe. So, we need to check if the image is already present
        if main_characters[i]['name'] in [c['name'] for c in universe_main_characters]:
            # use the same image from the universe in quest's main_character
            main_characters[i] = {
                **main_characters[i],
                'image': [c['image'] for c in universe_main_characters if c['name'] == main_characters[i]['name']][0]
            }
            continue

        image_url = generate_image(
            f''' Generate an image for the character {main_characters[i]['name']} whose role is {main_characters[i]['role']} in the quest {quest.quest_name} in the universe {quest.universe.universe_name}.
            The description of the character is as follows: {main_characters[i]['description']}
            The image description is as follows: {main_characters[i]['image_description']}
            The character is a part of the story outline: {story_outline}
            The quest description is as follows: {quest.description}
            The universe description is as follows: {quest.universe.description}
            Do not add any text to the image. The image should be visually appealing and should represent the character.
        ''')
        image_url = upload_image_from_url(image_url, f"universe/{quest.universe.id}/quest/{quest.id}/character/{i}")

        main_characters[i] = {
            **main_characters[i],
            'image': image_url
        }

    quest.main_characters = json.dumps(main_characters)
    quest.save()



def generate_quest_images(quest_id):
    '''
    generates images for the given quest
    '''
    # generate thumbnail
    generate_quest_thumbnail_image(quest_id)

    # generate character images
    generate_image_for_character_in_quest(quest_id)

    # generate icons for the score categories
    generate_icons_for_score_categories(quest_id)

    # generate reward images
    generate_all_images_for_quest_rewards(quest_id)

    # generate background images for questions
    generate_background_images(quest_id)


def generate_quest_assets(quest_id):
    '''
    generates images/audio/video for quest
    '''
    # rewards
    generate_rewards_for_quest(quest_id) 

    # images
    yield {'status': 'Generating quest images'}
    generate_quest_images(quest_id)

    # audio
    yield {'status': 'Generating quest audios'}
    generate_quest_audio(quest_id)

    yield {'status': 'Asset generation completed'}



def generate_quest_audio(quest_id):
    '''
    generates audio for the given quest
    '''
    # get the quest
    quest = get_object_or_404(Quest, pk=quest_id)

    # if audio is already present, return the url
    if quest.audio_url:
        return quest.audio_url
    
    storyline = ', '.join(json.loads(quest.story_outline))
    # prompt = f"""
    # Generate a background audio for a gameplay which has story which starts like {(storyline[:150] + '..') if len(storyline) > 150 else storyline}.\
    # The audio should be loopable, engaging and immersive, enhancing the player's experience. It should not contain any vocals and should be suitable for a game environment.\
    # """

    prompt = f"""
    Generate an instrumental background audio for a gameplay in the quest: "{quest.quest_name}" in the universe: "{quest.universe.universe_name}".
    It should be engaging and immersive, enhancing the player's experience. It should not contain any vocals and should be suitable for a game environment.\
    The audio should start and end at the same note and velocity, so that it can be looped seamlessly.
    """

    # mocking audio_url 

    # audio_url = "https://qverse-universe-test.s3.ap-south-1.amazonaws.com/test/d09f6ddf-85d2-4a83-ab63-05c306a5043c.mp3"

    client = ElevenLabs(
        api_key=ELEVEN_LABS_API_KEY, # Defaults to ELEVEN_API_KEY
    )
    result = client.text_to_sound_effects.convert(
        text=prompt,
        duration_seconds=10,
        prompt_influence=0.7,  # Optional, if not provided will use the default value of 0.3
    )

    # save the audio in a temp file with uuid as name
    audio_path = f"tmp/audio/{str(uuid.uuid4())}.mp3"

    # check if the directory exists else create it
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    save(result, audio_path)

    # upload the audio to s3
    audio_url = upload_audio_from_input_path(audio_path, f"universe/{quest.universe.id}/quest/{quest.id}")
    quest.audio_url = audio_url
    quest.save()

    return audio_url


def generate_rewards_for_quest(quest_id):
    '''
    generates rewards for the quest
    '''
    quest = get_object_or_404(Quest, pk=quest_id)
    # check if quest rewards are generated
    rewards = QuestRewardCollection.objects.filter(quest_id=quest_id)
    if len(rewards)>0:
        return
    
    prompt = f"""
    Generate rewards for the quest: "{quest.quest_name}" in the universe: "{quest.universe.universe_name}".
    A reward are rare collectibles to be given to the user. provide name and description for the collectibles.
    The quest goes as follows:
    {quest.description}
    This quest is a part of the universe with the following description: {quest.universe.description}.
    The quest involves the following main characters: {', '.join([f"{c['name']} ({c['role']})" for c in json.loads(quest.main_characters)])}.
    The story outline for this quest is as follows: {', '.join(json.loads(quest.story_outline))}.
    Generate 30 such rewards.
    Format the response as a JSON object with the following structure.
    {{
    "collectible_rewards": [
        {{"name": "string", "description": "string"}}
    ]
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

    rewards = data['collectible_rewards']

    # store it in QuestRewardCollection 
    for reward in rewards:
        r = QuestRewardCollection.objects.create(
            quest=quest,
            name=reward['name'],
            description=reward['description']
        )
        r.save()


def generate_all_images_for_quest_rewards(quest_id):
    '''
    generates images for all the quest rewards
    '''
    rewards = QuestRewardCollection.objects.filter(quest_id=quest_id)
    for reward in rewards:
        generate_image_for_quest_reward(reward.id)


def generate_image_for_quest_reward(collectible_id):

    collectible = QuestRewardCollection.objects.get(pk=collectible_id)
    # if image is already present, return the url
    if collectible.image_path:
        return collectible.image_path

    prompt = f"""
    Create an image for the collectible: "{collectible.name}".
    The collectible is associated with the quest: "{collectible.quest.quest_name}" in the universe: "{collectible.quest.universe.universe_name}".
    The description of the collectible is as follows: {collectible.description}.
    The image should be visually appealing and should represent the collectible.
    """
    image_url = generate_image(prompt)
    image_url = upload_image_from_url(image_url, f"universe/{collectible.quest.universe.id}/quest/{collectible.quest.id}/collectible/{collectible.id}")
    collectible.image_path = image_url
    collectible.save()
    return image_url


def assign_rewards_to_questions(quest_id):
    '''
    assigns predefined assets to options in the questions
    '''
    # get all the rewards for the quest
    rewards = QuestRewardCollection.objects.filter(quest_id=quest_id)

    # check if rewards are generated. if not raise error
    if len(rewards) == 0:
        raise Exception("Rewards are not generated for the quest")
    
    # get all the options for the quest's questions
    options = Option.objects.filter(question__quest_id=quest_id)

    '''
    Randomly assign rewards to options.
    Not all options need to have a reward. A gameplay which consists of 10 questions, needs to have atleast two rewards
    '''
    # keeping all options for now
    options_with_rewards = options

    # save rewards in Collectible
    for option in options_with_rewards:
        reward = random.choice(rewards)
        c = Collectible.objects.create(
            option=option,
            name=reward.name,
            description=reward.description,
            image_path=reward.image_path
        )
        c.save()


def generate_background_images(quest_id, num_of_images=20):
    '''
    Generates {num_of_images} background images for the quest to be used in questions
    '''
    # fetch quest
    quest = get_object_or_404(Quest, pk=quest_id)

    # generate prompt for generating {num_of_images} based on the quest
    prompt = f'''We have a quest named "{quest.quest_name}" in the universe "{quest.universe.universe_name}". The quest description is as follows: {quest.description}. The quest involves the following main characters: {', '.join([f"{c['name']} ({c['role']})" for c in json.loads(quest.main_characters)])}. The story outline for this quest is as follows: {', '.join(json.loads(quest.story_outline))}.
    Generate detailed and vivid descriptions for {num_of_images} images that can be used in the quest's gameplay. Each description should capture the essence of the quest, its environment, and the characters involved. Ensure the descriptions are elaborate and immersive, providing a clear visual representation of the scenes.
    Format the response as a JSON object with the following structure.
    {{
    "image_descriptions": [
        "string", "string",
    ]
    }}
    '''

    response = query_claude(prompt)
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        try:
            json.loads(response.replace('""', '"'))
        except json.JSONDecodeError as e:
            logger.error("Failed to decode response from claude", response=response, er=e)
            raise

    image_descriptions = data['image_descriptions']

    for i in image_descriptions:
        # generate image for the description
        image_prompt = f'''
        Generate an image to be used in a game of the quest "{quest.quest_name}" in the universe "{quest.universe.universe_name}". The quest description is as follows: {quest.description}. The quest involves the following main characters: {', '.join([f"{c['name']} ({c['role']})" for c in json.loads(quest.main_characters)])}. The story outline for this quest is as follows: {', '.join(json.loads(quest.story_outline))}.
        The image description is as follows: {i}
        The image should be visually appealing and should be immersive.
        '''
        image_url = generate_image(image_prompt)
        image_url = upload_image_from_url(image_url, f"universe/{quest.universe.id}/quest/{quest.id}/background")
        # QuestGameplayImages
        qgi = QuestGameplayImages.objects.create(
            quest=quest,
            image_path=image_url,
            description = i
        )
        qgi.save()
