from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed 
from django.conf import settings
import os

from rest_framework.authentication import CSRFCheck
from rest_framework import permissions, authentication

from rest_framework_simplejwt import exceptions

API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")


def enforce_csrf(request):
    check = CSRFCheck()
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied('CSRF Failed: %s' % reason)


class CustomAuthentication(JWTAuthentication):

    def authenticate(self, request):
        header = self.get_header(request)

        if header is None:
            raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE']) or request.COOKIES.get('auth-key') or None
            if not raw_token:
                raw_token = request.META.get('HTTP_AUTH_KEY') or request.headers.get('auth_key') or request.headers.get('auth-key') or None
        else:
            raw_token = self.get_raw_token(header)
        if raw_token is None:
            raise AuthenticationFailed(
                detail={
                    "success": False,
                    "message": "User is invalid, unable to authenticate.",
                    "additional_info": "Token is missing or invalid."
                },
                code="authentication_failed"
            )


        validated_token = self.get_validated_token(raw_token)
        # enforce_csrf(request)
        return self.get_user(validated_token), validated_token


class APITokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_token = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION') or request.headers.get('auth_token') or None

        if auth_token == settings.API_KEY:
            return (None, None)
        
        raise exceptions.AuthenticationFailed('Invalid token')