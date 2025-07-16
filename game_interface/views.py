from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from user.models import UserProfile
from generator.models import Quest, Question, Option, ScoreCategory, Collectible, Universe
from generator.service import get_quest_question
from rest_framework.views import APIView
from .models import UserGameplay, UserScoreByCategoryForGameplay, UserCollectible, UserUniverseSuggestion
from django.db.models import Sum
from utils.slack_helper import generate_slack_message, slack_send_wrapper
class GameplayViewSet(viewsets.ViewSet):
    authentication_classes = ()
    permission_classes = ()
    @action(detail=True, methods=['post'])
    def start_quest(self, request, slug=None):
        try:
            quest = Quest.objects.get(slug=slug)
            # if user_profile.total_score < quest.min_score_requirement:
            #     return Response({'error': 'Insufficient score to start this quest'}, status=status.HTTP_400_BAD_REQUEST)
            num_of_options = int(request.data.get('num_of_options', 2))
            question_data = get_quest_question(quest.id, None, num_of_options)
            quest_audio = quest.audio_url
            # # Create or get UserGameplay
            # user_gameplay, created = UserGameplay.objects.get_or_create(
            #     user=request.user,
            #     quest=quest,
            #     defaults={'current_question': Question.objects.get(id=question_data['id'])}
            # )
            collectible = {}

            score_categories = ScoreCategory.objects.filter(quest=quest).all()

            score_values = {category.id: {
                'score_change'  : 0,
                'max_score'     : 10,
                'image'         : category.icon,
                'description'   : category.description,
                'name'          : category.name
            } for category in score_categories}

            return Response({
                **question_data,
                'score'         : score_values,
                'collectible'   : collectible,
                'quest_audio': quest_audio,
                'quest_thumbnail' : quest.thumbnail,
                'description' : quest.description,
                'quest_name' : quest.quest_name,
                'quest_intro' : quest.intro
                })
        
        except Quest.DoesNotExist:
            return Response({'error': 'Quest not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def answer_question(self, request, pk=None):
        try:
            question = Question.objects.get(pk=pk)
            option_id = request.data.get('option_id')
            option = Option.objects.get(id=option_id)
            # user_gameplay = UserGameplay.objects.filter(user=request.user, quest=question.quest).last()

            # Update user's score and collectibles
            # for category_id, points in option.score_rewards.items():
            #     user_score, created = UserScoreByCategoryForGameplay.objects.get_or_create(
            #         user_gameplay=user_gameplay,
            #         score_category_id=category_id,
            #         defaults={'score': 0}
            #     )
            #     user_score.score += points
            #     user_score.save()
            
            collectible = {}

            # get applicable collectible
            collectible_item = Collectible.objects.filter(option=option).first()

            if collectible_item:
                collectible = {
                    'name'          : collectible_item.name,
                    'description'   : collectible_item.description,
                    'image_path'    : collectible_item.image_path
                }

            # fetch categories of the score rewards
            score_categories = ScoreCategory.objects.filter(id__in=option.score_rewards.keys())

            # initialise score_values to 0
            score_values = {category.id: {
                'score_change'  : 0,
                'max_score'     : 10,
                'image'         : category.icon,
                'description'   : category.description,
                'name'          : category.name
            } for category in score_categories}

            # update the score_values with the points from the option
            for category_id, points in option.score_rewards.items():
                score_values[int(category_id)] = {
                    **score_values[int(category_id)],
                    'score_change': points
                }

            # if collectible:
            #     user_collectible, created = UserCollectible.objects.get_or_create(
            #         user=request.user,
            #         collectible=collectible,
            #         defaults={'quantity': 0}
            #     )
            #     user_collectible.quantity += 1
            #     user_collectible.save()

            # Update total score
            # total_score = UserScoreByCategoryForGameplay.objects.filter(
            #     user_gameplay=user_gameplay
            # ).aggregate(total_score=Sum('score'))['total_score'] or 0
            next_question_data = get_quest_question(question.quest.id, option.id, len(question.options.all()))

            if next_question_data:
                return_data = {
                    **next_question_data,
                    'score'         : score_values,
                    'collectible'   : collectible
                }
                # user_gameplay.current_question = Question.objects.get(id=next_question_data['id'])
                # user_gameplay.save()
            else:
                # user_gameplay.completed = True
                # user_gameplay.save()
                return_data = {
                    'message'       : 'Quest completed',
                    'score'         : score_values,
                    'collectible'   : collectible
                }

            return Response(return_data)
        
        except (Question.DoesNotExist, Option.DoesNotExist, UserGameplay.DoesNotExist):
            return Response({'error': 'Question, Option or UserGameplay not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # @action(detail=False, methods=['get'])
    # def current_gameplay_score(self, request):
    #     try:
    #         user_gameplay = UserGameplay.objects.filter(user=request.user, completed=False).last()
    #         scores = UserScoreByCategoryForGameplay.objects.filter(user_gameplay=user_gameplay)
    #         score_data = [{'category': score.score_category.name, 'score': score.score, 'image':score.score_category.icon, 'max_score': 10} for score in scores]
    #         return Response({
    #             'score_data': score_data,
    #             'current_question_no': user_gameplay.current_question.question_number,
    #             'total_questions': user_gameplay.quest.max_questions
    #         })
    #     except UserGameplay.DoesNotExist:
    #         return Response({'error': 'No active gameplay found'}, status=status.HTTP_404_NOT_FOUND)

    # @action(detail=False, methods=['get'])
    # def user_stats(self, request):
    #     total_rewards = UserCollectible.objects.filter(user=request.user).count()
    #     completed_quests = UserGameplay.objects.filter(user=request.user, completed=True).count()
        
    #     return Response({
    #         'total_score': 100,
    #         'total_rewards': total_rewards,
    #         'completed_quests': completed_quests
    #     })
    
    @action(detail=False, methods=['get'])
    def get_score_categories(self, request, slug=None):
        # get the quest id from the slug
        quest = Quest.objects.get(slug=slug)
        score_categories = ScoreCategory.objects.filter(quest=quest).all()
        return Response([{'id': category.id, 'name': category.name, 'description': category.description, 'icon': category.icon} for category in score_categories])
    
    @action(detail=False, methods=['get'])
    def get_universes(self, request):
        universes = Universe.objects.all()
        universe_data = []

        for i in universes:
            quests = Quest.objects.filter(universe=i)
            quest_data = []
            for j in quests:
                quest_data.append({
                    'name': j.quest_name,
                    'description': j.description,
                    'thumbnail': j.thumbnail,
                    'slug': j.slug,
                    'playing': 100,
                    'tag': "Popular"
                })
            universe_data.append({
                'name': i.universe_name,
                'description': i.description,
                'thumbnail': i.thumbnail,
                'slug': i.slug,
                'quests': quest_data
            })

        return Response({'universe': universe_data})


class LeaderBoardViewSet(viewsets.ViewSet):
    authentication_classes = ()
    permission_classes = ()
    @action(detail=False, methods=['get'])
    def get_leaderboard(self, request):
        user_profiles = UserProfile.objects.order_by('-total_score')[:10]
        leaderboard = [{'username': profile.user.username, 'total_score': profile.total_score} for profile in user_profiles]
        return Response(leaderboard)


class MockLeaderboardView(APIView):
    authentication_classes = ()
    permission_classes = ()
    def get(self, request):
        mock_data = {
            'success': True,
            'data': {
                'leaderboard_name': "Kunal Shah's Top Fans",
                'leaderboard_details': [
                    {
                        'name': 'Kaushik',
                        'score': '10',
                        'rewards_collected': '100',
                        'quests_completed': '2'
                    },
                    {
                        'name': 'Gunjan',
                        'score': '2',
                        'rewards_collected': '50',
                        'quests_completed': '2'
                    },
                    {
                        'name': 'Rahul',
                        'score': '8',
                        'rewards_collected': '75',
                        'quests_completed': '3'
                    },
                    {
                        'name': 'Priya',
                        'score': '5',
                        'rewards_collected': '60',
                        'quests_completed': '1'
                    },
                    {
                        'name': 'Amit',
                        'score': '7',
                        'rewards_collected': '80',
                        'quests_completed': '2'
                    }
                ]
            },
            'message': 'Success'
        }
        return Response(mock_data)
    

# user can suggest universes. the suggestions will be stored in the database
class UserUniverseSuggestionViewSet(viewsets.ViewSet):
    authentication_classes = ()
    permission_classes = ()
    @action(detail=False, methods=['post'])
    def suggest_universe(self, request):
        universe_description = request.data.get('universe_description')
        name = request.data.get('name')
        email = request.data.get('email')
        mobile = request.data.get('mobile', None)
        UserUniverseSuggestion.objects.create(universe_description=universe_description, name=name, email=email, mobile=mobile)
        message=generate_slack_message(f"universe_description={universe_description}, name={name}, email={email}, mobile={mobile}")
        slack_send_wrapper(message)
        return Response({'message': 'Universe suggestion submitted successfully'})