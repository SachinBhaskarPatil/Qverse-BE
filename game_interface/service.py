from user.models import User, UserProfile
from game_interface.models import UserGameplay, UserScoreByCategoryForGameplay


def calculate_user_score(user_id):
    '''
    Calculates the user's total score from accross gameplays.
    '''
    user_gameplays = UserGameplay.objects.filter(user_id=user_id, completed=True)

    # get all the scores from UserScoreByCategoryForGameplay for the gameplays
    scores = UserScoreByCategoryForGameplay.objects.filter(user_gameplay__in=user_gameplays)

    total_score = 0
    for score in scores:
        total_score += score.score
        
    user_profile = UserProfile.objects.get(user_id=user_id)
    user_profile.total_score = total_score
    user_profile.save()
    return total_score

