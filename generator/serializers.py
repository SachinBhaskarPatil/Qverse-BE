import json

from rest_framework import serializers
from .models import Universe, Quest, Question, Option, HomePage, Trivia, TriviaQuestion, AudioStory, Episode, Comic, ComicPage, ShortVideos, News

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'option_text']


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)
    characters = serializers.SerializerMethodField()

    def get_characters(self, obj):
        quest = obj.quest
        main_characters = json.loads(quest.main_characters or '[]') if quest else []
        characters = []
        question_characters = json.loads(obj.characters or '[]')
        for i in main_characters:
            if i['name'] in question_characters:
                characters.append({
                    'name': i.get('name'),
                    'image': i.get('image'),
                    'role': i.get('role'),
                    'description': i.get('description')
                })
        return characters
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'audio_file_path', 'image_file_path', 'options', 'characters']


class QuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quest
        fields = ['id', 'quest_name', 'description', 'min_score_requirement', 'slug', 'thumbnail']


class UniverseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Universe
        fields = ['id', 'universe_name', 'description', 'key_elements', 'slug']


class HomePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomePage
        fields = ['id', 'name', 'description', 'thumbnail', 'type', 'display_order']


class TriviaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trivia
        fields = ['id', 'name', 'description', 'thumbnail', 'slug', 'audio_url']


class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = ['id', 'trivia', 'question_number', 'question_text', 'options', 'image', 'previous_question', 'next_question']


class AudioStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioStory
        fields = ['id', 'name', 'description', 'thumbnail', 'slug']


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ['id', 'audio_story', 'name', 'description', 'episode_number', 'audio_file_path', 'image', 'previous_episode', 'next_episode']


class ComicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comic
        fields = ['id', 'name', 'description', 'thumbnail', 'slug']


class ComicPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComicPage
        fields = ['id', 'comic', 'page_number', 'narration_text', 'image', 'previous_page', 'next_page']


class ShortVideosSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShortVideos
        fields = ['id','name', 'description', 'thumbnail', 'url', 'slug']


class NewsSerializer(serializers.ModelSerializer):

    class Meta:
        model = News
        fields = ['id','name', 'category' ,'description', 'thumbnail', 'audio_url', 'slug']


class CombinedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    thumbnail = serializers.URLField(required=False)
    slug = serializers.CharField()