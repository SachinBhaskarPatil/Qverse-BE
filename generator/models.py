from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string

from utils.helpers import BaseModelMixin


class Universe(BaseModelMixin):
    universe_name           = models.CharField(max_length=255)
    description             = models.TextField()
    narrator_voice_samples  = models.JSONField(default=list)
    narrator_voice_description  = models.TextField(help_text="An old American male voice with a slight hoarseness in his throat. Perfect for news", null=True, blank=True)
    key_elements            = models.JSONField(default=list)
    thumbnail               = models.URLField(null=True, blank=True)
    main_characters         = models.JSONField(default=list)
    slug                    = models.SlugField(unique=True)
    meta                    = models.JSONField(default=dict)


class Quest(BaseModelMixin):
    universe                        = models.ForeignKey(Universe, on_delete=models.CASCADE, related_name='quests')
    quest_name                      = models.CharField(max_length=255)
    intro                           = models.TextField()
    max_questions                   = models.IntegerField(default=10)
    thumbnail                       = models.URLField(null=True, blank=True)
    description                     = models.TextField()
    main_characters                 = models.JSONField(default=list)
    background_audio_description    = models.TextField(null=True, blank=True)
    story_outline                   = models.JSONField(default=list)
    min_score_requirement           = models.IntegerField(default=0)
    audio_url                       = models.CharField(max_length=500, null=True, blank=True, help_text='Each quest can have an audio file associated with it. This audio will be played when the quest is being played.')
    slug                            = models.SlugField(unique=True) 


class ScoreCategory(BaseModelMixin):
    name        = models.CharField(max_length=255)
    quest       = models.ForeignKey(Quest, on_delete=models.CASCADE)
    description = models.TextField()
    icon        = models.CharField(max_length=500)


class Question(BaseModelMixin):
    quest               = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='questions')
    question_text       = models.TextField()
    parent_option       = models.ForeignKey('Option', on_delete=models.SET_NULL, null=True, related_name='child_questions')
    question_number     = models.IntegerField(default=1)
    characters          = models.JSONField(default=list)
    audio_file_path     = models.CharField(max_length=500, null=True, blank=True)
    image_file_path     = models.CharField(max_length=500, null=True, blank=True)


class Option(BaseModelMixin):
    question            = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text         = models.TextField()
    next_question       = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, related_name='previous_options')
    reward_image_path   = models.CharField(max_length=500, null=True, blank=True)
    reward_text         = models.TextField(null=True, blank=True)
    score_rewards       = models.JSONField(default=dict)  # {score_category_id: points}


class Collectible(BaseModelMixin):
    '''
    On choosing an option, a user can be rewarded with a collectible.
    '''
    name            = models.CharField(max_length=255)
    option          = models.ForeignKey(Option, on_delete=models.CASCADE,)
    description     = models.TextField()
    image_path      = models.CharField(max_length=500)


class QuestRewardCollection(BaseModelMixin):
    '''
    All collectibles/rewards for a quest is pregenerated and stored here
    '''
    quest           = models.ForeignKey(Quest, on_delete=models.CASCADE)
    name            = models.CharField(max_length=255)
    description     = models.TextField()
    image_path      = models.CharField(max_length=500)


class QuestGameplayImages(BaseModelMixin):
    '''
    All images of the quest's gameplay is pregenerated and stored here
    '''
    quest           = models.ForeignKey(Quest, on_delete=models.CASCADE)
    description     = models.TextField()
    image_path      = models.CharField(max_length=500)


class Character(BaseModelMixin):
    name                = models.CharField(max_length=255)
    universe            = models.ForeignKey(Universe, on_delete=models.CASCADE, related_name='characters')
    description         = models.TextField()
    slug                = models.SlugField(unique=True)
    image_path          = models.CharField(max_length=500, null=True, blank=True)
    role                = models.CharField(max_length=255)
    voice_description   = models.TextField(null=True, blank=True)
    image_description   = models.TextField(null=True, blank=True)
    meta                = models.JSONField(default=dict)


class HomePage(BaseModelMixin):
    class HomePageTypes(models.TextChoices):
        QUEST       = 'QUEST', 'Quest'
        TRIVIA      = 'TRIVIA', 'Trivia'
        AUDIO_STORY = 'AUDIO_STORY', 'Audio Story'
        COMIC       = 'COMIC', 'Comic'
        OTHERS      = 'OTHERS', 'Others'

    name            = models.CharField(max_length=255)
    description     = models.TextField()
    thumbnail       = models.URLField(null=True, blank=True, max_length=1000)
    type            = models.CharField(max_length=50, choices=HomePageTypes.choices, default=HomePageTypes.OTHERS)
    slug            = models.SlugField(null=True, blank=True)
    display_order   = models.IntegerField(null=True, blank=True, default=1, help_text="Order of components in HomePage (ascending)")
    show_in_banner  = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Trivia(BaseModelMixin):
    name        = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail   = models.URLField(null=True, blank=True, max_length=1000)
    audio_url   = models.URLField(null=True, blank=True, max_length=1000)
    slug        = models.SlugField(unique=True, default="", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = f"{base_slug}-{get_random_string(8)}"
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TriviaQuestion(BaseModelMixin):
    trivia              = models.ForeignKey(Trivia, on_delete=models.CASCADE)
    question_number     = models.IntegerField(null=True, blank=True)
    question_text       = models.TextField()
    options             = models.JSONField()
    image               = models.URLField(null=True, blank=True, max_length=1000)
    previous_question   = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="next_questions_set")
    next_question       = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_questions_set")

    def save(self, *args, **kwargs):
        if not self.question_number:
            if self.previous_question:
                self.question_number = self.previous_question.question_number + 1
            else:
                self.question_number = 1
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Question for {self.trivia.name}: {self.question_number}"


class AudioStory(BaseModelMixin):
    name        = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail   = models.URLField(null=True, blank=True, max_length=1000)
    slug        = models.SlugField(unique=True, default="", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = f"{base_slug}-{get_random_string(8)}"
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Episode(BaseModelMixin):
    audio_story         = models.ForeignKey(AudioStory, on_delete=models.CASCADE)
    name                = models.CharField(max_length=255)
    description         = models.TextField()
    episode_number      = models.IntegerField(null=True, blank=True)
    audio_file_path     = models.CharField(max_length=1000)
    image               = models.URLField(null=True, blank=True, max_length=1000)
    previous_episode    = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="next_episodes_from")
    next_episode        = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_episodes_from")

    def save(self, *args, **kwargs):
        if not self.episode_number:
            if self.previous_episode:
                self.episode_number = self.previous_episode.episode_number + 1
            else:
                self.episode_number = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Episode {self.name} for {self.audio_story.name}"
    

class Comic(BaseModelMixin):
    name       = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail   = models.URLField(null=True, blank=True, max_length=1000)
    slug        = models.SlugField(unique=True, default="", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = f"{base_slug}-{get_random_string(8)}"
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ComicPage(BaseModelMixin):
    comic           = models.ForeignKey(Comic, on_delete=models.CASCADE)
    page_number     = models.IntegerField(null=True, blank=True)
    narration_text  = models.TextField(null=True, blank=True)
    image           = models.URLField(null=True, blank=True, max_length=1000)
    previous_page   = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="next_page_set")
    next_page       = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name="previous_page_set")

    def save(self, *args, **kwargs):
        if not self.page_number:
            if self.previous_page:
                self.page_number = self.previous_page.page_number + 1
            else:
                self.page_number = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Page {self.page_number} for {self.comic.name}"
    

class ShortVideos(BaseModelMixin):
    name        = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail   = models.URLField(null=True, blank=True, max_length=1000)
    url         = models.URLField(null=False, blank=False, max_length=1000)     #with logo and watermark
    raw_url     = models.URLField(null=True, blank=True, max_length=1000)       #without logo and watermark
    slug        = models.SlugField(unique=True, default="", blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = f"{base_slug[:42]}-{get_random_string(8)}"
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class News(BaseModelMixin):
    class NewsTypes(models.TextChoices):
        MYSTERY_CRIME               = 'Mystery & Crime'
        TECH_INNOVATIONS            = 'Tech Innovations'
        HISTORICAL_EVENTS           = 'Historical Events'
        ENVIRONMENTAL_AWARENESS     = 'Environmental Awareness'
        CULTURAL_TRADITIONS         = 'Cultural Traditions'
        HEALTH_WELLNESS             = 'Health & Wellness'
        ART_MOVEMENTS               = 'Art Movements'
        SCIENCE_DISCOVERIES         = 'Science Discoveries'
        ENTREPRENEURSHIP_STARTUPS   = 'Entrepreneurship & Startups'
        POLITICAL                   = 'Political'
        SPORTS                      = 'Sports'
        WAR                         = 'War'
        CELEBRITIES                 = 'Celebrities'
        OTHERS                      = 'Others'

    name        = models.CharField(max_length=255)
    category        = models.CharField(max_length=100, choices=NewsTypes.choices, default=NewsTypes.OTHERS)
    description = models.TextField(max_length=1000)
    thumbnail   = models.URLField(null=True, blank=True, max_length=1000)
    audio_url   = models.URLField(null=True, blank=True, max_length=1000)
    video_url   = models.URLField(null=True, blank=True, max_length=1000)
    slug        = models.SlugField(unique=True, default="", blank=True,max_length=100)

    def __str__(self):
        return self.name 

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = f"{base_slug[:42]}-{get_random_string(8)}"
            self.slug = slug
        
        super().save(*args, **kwargs)