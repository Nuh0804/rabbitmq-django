import uuid
from dotenv import dotenv_values
from builder.UAA import UAABuilder

from uaa.models import UsersWithRoles
from accounts.models import UserProfile

from .BearTokenAuthentication import BearerTokenAuthentication

config = dotenv_values(".env")


class UserUtils:
    def __init__(self, request):
        self.request = request

    @staticmethod
    def get_user(request=None):
        is_authenticated, user = BearerTokenAuthentication.authenticate(None, request)
        user_data = {}

        
        if not is_authenticated:
            return False , user_data


        profile = UserProfile.objects.filter(profile_user=user).first()
        if profile is None:
            return  False ,user_data
        
        user_with_role = UsersWithRoles.objects.filter(user_with_role_user=user).first()

        
        if user_with_role:
            user_roles = UAABuilder.get_role_data(id=user_with_role.user_with_role_role.role_unique_id)
            user_permissions = [permission.permission_code for permission in user_roles.role_permissions]
            user_data.update({'user_permissions': user_permissions})
        
        user_data.update({'user_permissions': []})
 
        user_data.update({
            'id': str(profile.profile_user.pk),
            'profile_unique_id': str(profile.profile_unique_id),
            'first_name': profile.profile_user.first_name,
            'last_name': profile.profile_user.last_name,
            'username': profile.profile_user.username,
            'email': profile.profile_user.email,
        })

                
        return True , user_data


    @staticmethod
    def __profile__(request):
        success , data = UserUtils.get_user(request)

        if not success:
            return None

        return data['profile_unique_id']
        
    @staticmethod
    def get_unique_token():
        token = str(uuid.uuid4())
        return token
