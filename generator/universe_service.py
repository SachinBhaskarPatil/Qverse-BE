from .service import *


def generate_universe_thumbnail_image(universe_id):
    '''
    generates thumbnail image for the given universe
    '''
    # get the universe
    universe = get_object_or_404(Universe, pk=universe_id)
    main_characters = get_main_characters_migrated(universe_id)

    # if universe thumbnail is already present, return the url
    if universe.thumbnail:
        return universe.thumbnail

    prompt = f"""
    Create a thumbnail image for the universe: "{universe.universe_name}".
    The universe has the following description: {universe.description}.
    The key elements of this universe are: {', '.join(json.loads(universe.key_elements))}.
    The main characters in this universe are: {', '.join([f"{c['name']} ({c['role']})" for c in main_characters])}.
    Do not add any text to the image. The image should be visually appealing and should represent the universe.
    """

    image_url = generate_image(prompt)

    if image_url:
        image_url = upload_image_from_url(image_url, f"universe/{universe.id}")

    universe.thumbnail = image_url
    universe.save()
    return image_url


def generate_universe_assets(universe_id):
    '''
    generates images/audio/video for universe
    '''
    generate_universe_thumbnail_image(universe_id)

    generate_image_for_character_in_universe(universe_id)

    return {'status': 'completed'}


def generate_image_for_character_in_universe(universe_id):
    '''
    generates images for the main characters in the given universe
    '''
    universe = Universe.objects.get(pk=universe_id)
    chatacters = Character.objects.filter(universe=universe)

    for i in chatacters:
        if i.image_path:
            continue

        prompt = f"""
        Create an image for the character: "{i.name}" in the universe: "{universe.universe_name}".
        The character has the following description: {i.description}.
        The image description is as follows: {i.image_description}
        The character plays the role of: {i.role}.
        The universe description is as follows: {universe.description}.
        Do not add any text to the image. The image should be visually appealing and should represent the character.
        """

        image_url = generate_image(prompt)

        if image_url:
            image_url = upload_image_from_url(image_url, f"universe/{universe.id}/character/{i.id}")

        i.image_path = image_url
        i.save()