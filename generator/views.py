import random

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Universe, Quest, Question, Option, HomePage, Trivia, TriviaQuestion, AudioStory, Episode, Comic, ComicPage, ShortVideos, News
from .serializers import UniverseSerializer, QuestSerializer, QuestionSerializer, OptionSerializer, HomePageSerializer, TriviaSerializer, TriviaQuestionSerializer, AudioStorySerializer, EpisodeSerializer, ComicSerializer, ComicPageSerializer, ShortVideosSerializer, NewsSerializer

class UniverseViewSet(viewsets.ModelViewSet):
    authentication_classes = ()
    permission_classes = ()
    queryset = Universe.objects.all()
    serializer_class = UniverseSerializer


class QuestViewSet(viewsets.ModelViewSet):
    authentication_classes = ()
    permission_classes = ()
    serializer_class = QuestSerializer

    def get_queryset(self):
        universe_id = self.request.query_params.get('universe')
        if universe_id:
            return Quest.objects.filter(universe_id=universe_id)
        return Quest.objects.all()
    

class QuestionViewSet(viewsets.ModelViewSet):
    authentication_classes = ()
    permission_classes = ()
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    # override the get to add the character images to the response
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        for question in response.data:
            for character in question['characters']:
                # images of the character are in the quest's main_character field in the format as below
                # [{'name': 'character1', 'role': 'role1', 'image': 'image1'}, {'name': 'character2', 'role': 'role2', 'image': 'image2'}]
                for main_character in question['main_characters']:
                    if main_character['name'] == character['name']:
                        character
                        character['image'] = main_character['image']
                        break
        return response

class OptionViewSet(viewsets.ModelViewSet):
    authentication_classes = ()
    permission_classes = ()
    queryset = Option.objects.all()
    serializer_class = OptionSerializer


class HomePageView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, pk=None):
        try:
            homepages = HomePage.objects.all().order_by('display_order')
            serializer = HomePageSerializer(homepages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class BannerView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request):
        try:
            banners = HomePage.objects.filter(show_in_banner=True).order_by('display_order')
            serializer = HomePageSerializer(banners, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

class TriviaView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, slug=None, question_number=None):
        if slug:
            try:
                trivia = Trivia.objects.get(slug=slug)
                if question_number:
                    # Retrieve specific question
                    try:
                        question = TriviaQuestion.objects.get(trivia=trivia, question_number=question_number)
                        serializer = TriviaQuestionSerializer(question)
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    except TriviaQuestion.DoesNotExist:
                        return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
                else:
                    # Retrieve all questions related to the trivia
                    serializer = TriviaSerializer(trivia)
                    questions = TriviaQuestion.objects.filter(trivia=trivia)
                    question_serializer = TriviaQuestionSerializer(questions, many=True)
                    data = {
                        'trivia': serializer.data,
                        'questions': question_serializer.data
                    }
                    return Response(data, status=status.HTTP_200_OK)
            except Trivia.DoesNotExist:
                return Response({"error": "Trivia not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Retrieve all trivia instances
            trivia_list = Trivia.objects.all()
            serializer = TriviaSerializer(trivia_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class AudioStoryView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, slug=None, episode_number=None):
        if slug:
            try:
                audio_story = AudioStory.objects.get(slug=slug)
                if episode_number:
                    # Retrieve specific episode
                    try:
                        episode = Episode.objects.get(audio_story=audio_story, episode_number=episode_number)
                        serializer = EpisodeSerializer(episode)
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    except Episode.DoesNotExist:
                        return Response({"error": "Episode not found"}, status=status.HTTP_404_NOT_FOUND)
                else:
                    # Retrieve all episodes related to the audio story
                    serializer = AudioStorySerializer(audio_story)
                    episodes = Episode.objects.filter(audio_story=audio_story)
                    episode_serializer = EpisodeSerializer(episodes, many=True)
                    data = {
                        'audio_story': serializer.data,
                        'episodes': episode_serializer.data
                    }
                    return Response(data, status=status.HTTP_200_OK)
            except AudioStory.DoesNotExist:
                return Response({"error": "Audio story not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            audio_story_list = AudioStory.objects.all()
            serializer = AudioStorySerializer(audio_story_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class ComicView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, slug=None, page_number=None):
        if slug:
            try:
                comic = Comic.objects.get(slug=slug)
                if page_number:
                    # Retrieve specific page
                    try:
                        page = ComicPage.objects.get(comic=comic, page_number=page_number)
                        serializer = ComicPageSerializer(page)
                        return Response(serializer.data, status=status.HTTP_200_OK)
                    except ComicPage.DoesNotExist:
                        return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
                else:
                    # Retrieve all pages related to the comic
                    serializer = ComicSerializer(comic)
                    pages = ComicPage.objects.filter(comic=comic).order_by('page_number')
                    page_serializer = ComicPageSerializer(pages, many=True)
                    data = {
                        'comic': serializer.data,
                        'pages': page_serializer.data
                    }
                    return Response(data, status=status.HTTP_200_OK)
            except Comic.DoesNotExist:
                return Response({"error": "Comic not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            comic_list = Comic.objects.all()
            serializer = ComicSerializer(comic_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        

class MakeLiveView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def post(self, request, type):
        try:
            slug = request.data.get('slug')
            display_order = request.data.get('display_order')
            show_in_banner = request.data.get('show_in_banner', False)

            if not type or not slug or display_order is None:
                return Response({"error": "type, slug, and display_order are required fields"}, status=status.HTTP_400_BAD_REQUEST)
            
            type = type.upper()
            
            if type == HomePage.HomePageTypes.TRIVIA:
                content = Trivia.objects.get(slug=slug)
            elif type == HomePage.HomePageTypes.AUDIO_STORY:
                content = AudioStory.objects.get(slug=slug)
            elif type == HomePage.HomePageTypes.COMIC:
                content = Comic.objects.get(slug=slug)
            else:
                return Response({"error": "Type not found"}, status=status.HTTP_404_NOT_FOUND)

            homepage = HomePage.objects.create(
                name=content.name,
                description=content.description,
                thumbnail=content.thumbnail,
                type=type, 
                slug=slug,
                display_order=display_order,  
                show_in_banner=show_in_banner
            )

            return Response({"message": "HomePage item created successfully", "id": homepage.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ShortVideosView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, slug=None):
        if slug:
            try:
                short_videos = ShortVideos.objects.get(slug=slug)
                serializer = ShortVideosSerializer(short_videos)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ShortVideos.DoesNotExist:
                return Response({"error": "Short video not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # check if query param has slug. if so then the object with slug comes first and rest of the videos comes after
            query_slug = request.query_params.get('slug')
            if query_slug:
                try:
                    first_video = ShortVideos.objects.get(slug=query_slug)
                    remaining_videos = ShortVideos.objects.all().exclude(slug=query_slug)
                    short_videos_list = [first_video] + list(remaining_videos)
                except ShortVideos.DoesNotExist:
                    return Response({"error": "Short video not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                short_videos_list = ShortVideos.objects.all()
            serializer = ShortVideosSerializer(short_videos_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        

class MixedContentPagination(PageNumberPagination):
    authentication_classes = ()
    permission_classes = ()
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class MixedContentView(APIView):
    authentication_classes = ()
    permission_classes = ()
    pagination_class = MixedContentPagination

    def get(self, request, *args, **kwargs):
        quests = QuestSerializer(Quest.objects.all(), many=True).data
        trivias = TriviaSerializer(Trivia.objects.all(), many=True).data
        audio_stories = AudioStorySerializer(AudioStory.objects.all(), many=True).data
        comics = ComicSerializer(Comic.objects.all(), many=True).data
        short_videos = ShortVideosSerializer(ShortVideos.objects.all(), many=True).data
        news = NewsSerializer(News.objects.all(), many=True).data

        for quest in quests:
            quest['name'] = quest.pop('quest_name')
            quest.pop('min_score_requirement')

        combined_data = (
            [{'type': 'quest', **item} for item in quests] +
            [{'type': 'trivia', **item} for item in trivias] +
            [{'type': 'audio_story', **item} for item in audio_stories] +
            [{'type': 'comic', **item} for item in comics] +
            [{'type': 'short_video', **item} for item in short_videos] +
            [{'type': 'news', **item} for item in news]
        )

        random.shuffle(combined_data)

        paginator = self.pagination_class()
        paginated_data = paginator.paginate_queryset(combined_data, request)
        return paginator.get_paginated_response(paginated_data)


class QuestView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request, slug=None):
        if slug:
            try:
                quest = Quest.objects.get(slug=slug)
                serializer = QuestSerializer(quest)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Quest.DoesNotExist:
                return Response({"error": "Quest not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Slug is required"}, status=status.HTTP_400_BAD_REQUEST)
