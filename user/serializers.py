from rest_framework import serializers
from .models import UserProfile, User 

from .service import valid_name
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError


class UserProfileSerializer(serializers.ModelSerializer):
    dob = serializers.DateField(required=False, input_formats=['%Y-%m-%d'])
    class Meta:
        model=UserProfile
        fields=['gender','dob','photo_url', 'profession']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name','phone','country_code' ]
    def validate(self,data):
        name=data.get('first_name')
        
        if not valid_name(name):
            raise serializers.ValidationError('Name must contain valid characters')

        return data

class UserAuthSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    country_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        phone = data.get('phone')
        email = data.get('email')
        country_code = data.get('country_code')

        if not phone and not email:
            raise serializers.ValidationError("Either phone or email must be provided.")

        if phone:
            if not country_code:
                raise serializers.ValidationError("Country code is required when phone is provided.")
            
            # Example regex for validating phone numbers (modify as needed)
            if not phone.isdigit():
                raise serializers.ValidationError('Phone number is not correct.')           
        
        if email:
            try:
                validate_email(email) 
            except DjangoValidationError:
                raise serializers.ValidationError("Invalid email format.")

        return data
