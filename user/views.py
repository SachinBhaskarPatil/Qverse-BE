import json

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import UserProfile


from rest_framework.views import APIView
from .serializers import UserProfileSerializer,UserAuthSerializer
from rest_framework_simplejwt.tokens import RefreshToken
import requests as py_requests
from django.conf import settings
from django.http import JsonResponse
from .service import verify_user_in_pool,get_recommendations,get_profile_data
from rest_framework import serializers
from structlog import get_logger
from common.exceptions import BadRequest
from utils.helpers import random_alphanumeric
from django.contrib.auth import get_user_model


logger = get_logger()
User = get_user_model()

class UserProfileViewSet(viewsets.ModelViewSet):
    authentication_classes = ()
    permission_classes = ()
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]


    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user.userprofile)
        return Response(serializer.data)
    
    
    def get_permissions(self):
        if self.action in ['google_login', 'check_username']:
            return []
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[])
    def google_login(self, request):
        token = request.data.get('token')
        
        try:
            # Verify the access token
            url = f'https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}'
            response = py_requests.get(url)
            if response.status_code != 200:
                return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
            
            token_info = response.json()
            
            # Get user info
            userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
            headers = {'Authorization': f'Bearer {token}'}
            userinfo_response = py_requests.get(userinfo_url, headers=headers)
            userinfo = userinfo_response.json()

            email = userinfo.get('email')
            if not email:
                return Response({'error': 'Unable to get user email'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user
            user, created = User.objects.get_or_create(email=email, defaults={'username': email})
            
            if created:
                UserProfile.objects.create(user=user)

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': user.id,
                'email': user.email,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[])
    def check_username(self, request):
        username = request.query_params.get('username')
        is_available = not User.objects.filter(username=username).exists()
        return Response({'available': is_available})

    @action(detail=False, methods=['post'])
    def set_username(self, request):
        username = request.data.get('username')
        user = request.user
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username is already taken'}, status=status.HTTP_400_BAD_REQUEST)
        user.username = username
        user.save()
        return Response({'username': username})


class AuthView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request, *args, **kwargs):
        try:
            serializer = UserAuthSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            validated_data     = serializer.validated_data
            phone              = validated_data.get('phone')
            email              = validated_data.get('email')
            country_code       = validated_data.get('country_code')
            aws_access_token   = request.data.get('access_token')

            if not (phone or email):
                raise serializers.ValidationError("Either phone or email is required.")

            if not verify_user_in_pool(aws_access_token):
                logger.info("Invalid user credentials", status_code=400, phone=phone, email=email)
                raise BadRequest("Invalid Access Token")

            # Retrieve or create user logic
            user = None
            if phone:
                user = User.objects.filter(phone=phone).first()
            if not user and email:
                user = User.objects.filter(email=email).first()

            new_user = False
            if not user:
                username_attempt = 0
                username = None
                while username_attempt < 4:  # Try up to 4 times to generate a unique username
                    username_attempt += 1
                    username = random_alphanumeric(8)  # Generate random username
                    if not User.objects.filter(username=username).exists():  # Check if username is unique
                        break  # Exit the loop if the username is unique
                
                if username_attempt == 4:
                    logger.error("Failed to generate a unique username after 4 attempts", phone=phone, country_code=validated_data.get('country_code', ''))
                    raise Exception('Server unable to generate unique username')

                # Now, create the user with the unique username
                user = User.objects.create(
                    username     = username,  
                    phone        = phone if phone else None,
                    email        = email if email else None,
                    country_code = country_code if phone else None,
                    login_method = "email" if email else "phone" if phone else "unknown"
                )
                user.save()
                new_user = True

            # Create or retrieve the associated UserProfile
            user_profile,created=UserProfile.objects.get_or_create(user=user)
            if created:
                user_profile.save()
            # Generate tokens
            refresh         = RefreshToken.for_user(user)
            access_token    = str(refresh.access_token)
            refresh_token  = str(refresh)

            return Response(
                data={
                    'success': True,
                    'message': 'User validation successful. Authentication complete.',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'new_user': new_user,
                    'username': user.username,  
                },
                status=status.HTTP_200_OK,
            )

        except serializers.ValidationError as e:
            logger.error("Validation error", e=str(e))
            return Response(data=
                {"status": False, "message": "Validation error, Invalid Access Token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("Unexpected error", e=str(e))
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfileView(APIView):
    def get(self,request):
        try:
            user = request.user
            data = get_profile_data(user)
            return Response(data={
                'success':True,
                'message':'Profile Fetched Successfully',
                'data':data
            },status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:    
            return Response(
                {"success": False, "message": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error("Error in ProfileView",method="get",e=str(e),user=request.user)  
            return Response(data={
                'success':False,
                'message':'Profile Not Fetched',
            },status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class RecommendationView(APIView):
    def get(self, request):
        try:
            user     = request.user
            user_id  = user.id
            # Fetch recommendations for the user
            data     = get_recommendations(user_id)
            
            # Return success response
            return Response(
                data={
                    'success': True,
                    'message': 'Recommendations fetched successfully.',
                    'data': data
                },
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        except Exception as e:
            logger.error("Error in RecommendationView", method="get", e=str(e), user=request.user)
            return Response(
                {"success": False, "message": "Failed to fetch recommendations"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )