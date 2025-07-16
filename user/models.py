from django.db import models
from django.contrib.auth.models import AbstractUser
from common.helpers import BaseModelMixin
from django.utils.translation import gettext_lazy as _

class User(AbstractUser,BaseModelMixin):
   class Meta:
      db_table="user"
      
   username           = models.CharField(max_length=64,null=True,unique=True)
   phone              = models.CharField(max_length=16, unique=True,null=True)
   email              = models.EmailField(max_length=64, null=True, default=None,unique=True)
   email_verified     = models.BooleanField(default= False)
   country_code       = models.CharField(max_length=5,null=True, default=None)
   login_method       = models.CharField(max_length=200,null=True, default=None)

   def get_pk(self):
        return str(self.id)
    
   def __str__(self):
        return f"{self.get_full_name()}"

   def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
        
class UserProfile(BaseModelMixin):
    
    class Genders(models.TextChoices):
        MALE    = 'male',_('Male')
        FEMALE  = 'female', _('Female')
        OTHERS  = 'others', _('Others')
        
    class Meta:
        db_table = "user_profile"
    
    user               = models.OneToOneField(User, on_delete=models.CASCADE)    
    gender             = models.CharField(max_length=10, choices=Genders.choices, default=None, null=True)
    profession         = models.CharField(max_length=25, default=None, null=True)
    dob                = models.DateField(blank=True, null=True)
    photo_url          = models.URLField(blank=True, null=True)
    short_summary      = models.TextField(blank=True, null=True)
    gpt_thread_id      = models.CharField(max_length=200, null=True, blank=True)

class LogTable(BaseModelMixin):
    username    = models.CharField(max_length=255,null=True)
    type        = models.CharField(max_length=255) 
    prev_state  = models.JSONField(default=dict)  
    new_state   = models.JSONField(default=dict)

class ContentRecommendation(BaseModelMixin):
    class Meta:
        db_table = "content_recommendations"
    user_id         = models.IntegerField(null=True)
    content_id      = models.CharField(max_length=255)
    content_type    = models.CharField(max_length=255)