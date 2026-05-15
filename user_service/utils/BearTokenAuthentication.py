import json

from django.contrib.auth.backends import BaseBackend

from provider.oauth2.models import AccessToken 
from provider.utils import now


class BearerTokenAuthentication(BaseBackend):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        try:
            bearer_token = str(request.context.headers['Authorization'])
            bearer_token = bearer_token.split(' ')[1]
            token = AccessToken.objects.filter(token=bearer_token,expires__gt=now()).first()               
            return True, token.user
        except AccessToken.DoesNotExist:
            return False, None
        #TODO: remove this when in production
        except Exception as e:
            return False, None
