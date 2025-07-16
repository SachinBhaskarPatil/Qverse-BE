from django.db import models
from user.models import User
from generator.models import Quest, Question, ScoreCategory

# Create your models here.

class UserGameplay(models.Model):
    """
    A model to store the user's gameplay progress. The quest user played/playing. 
    Has the user completed the quest or if not, what is the current question the user is on.
    This model will be used for two things:
    1. To reload the game if the user drops off in the middle of the quest.
    2. To calculate overall score and leaderboard.
    
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    current_question = models.ForeignKey(Question, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'quest']
        # table name override
        db_table = 'user_gameplay'
        
    def __str__(self):
        return f"{self.user.username} - {self.quest.quest_name}"
    

class UserScoreByCategoryForGameplay(models.Model):
    '''
    Tracks the user's score for a gameplay across all the score categories available for the quest
    '''
    user_gameplay = models.ForeignKey(UserGameplay, on_delete=models.CASCADE)
    score_category = models.ForeignKey(ScoreCategory, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

class UserCollectible(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collectibles')
    collectible = models.ForeignKey('generator.Collectible', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        unique_together = ['user', 'collectible']

    def __str__(self):
        return f"{self.user.user.username} - {self.collectible.name}: {self.quantity}"


# model to store user universe suggestions. the fields should be created_at, universe_description
class UserUniverseSuggestion(models.Model):
    universe_description = models.CharField(max_length=1500)
    name  = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    mobile = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_universe_suggestion'
    
    def __str__(self):
        return f"{self.universe_description[:20]}"