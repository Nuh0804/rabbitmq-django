from dto.Accounts import  UserProfileObject
from accounts.models import UserProfile
from uaa.models import *
from builder.UAA import UAABuilder

class UserProfileBuilder:
   
     
   #user profile
   def get_user_profile_data(id):
        try:
            if id is None:
                return UserProfileObject()
            
            user_profile=UserProfile.objects.filter(profile_unique_id=id).first()

            return UserProfileObject(
                id = user_profile.id,
                profile_unique_id = user_profile.profile_unique_id,
                profile_organization = user_profile.profile_organization,
                profile_firstname = user_profile.profile_user.first_name,
                profile_lastname = user_profile.profile_user.last_name,
                profile_email = user_profile.profile_user.email,
                profile_phone = user_profile.profile_phone,
                profile_type = user_profile.profile_type
            )
        except Exception as e:
            return UserProfileObject()
        
   def get_user_profile_and_role_data(id):
        # try:
            user_profile=UserProfile.objects.filter(profile_is_active=True,profile_unique_id=id).first()
            user_with_role= UsersWithRoles.objects.filter(user_with_role_user=user_profile.profile_user).first()
            return UserProfileObject(
                id = user_profile.id,
                profile_unique_id = user_profile.profile_unique_id,
                profile_organization = user_profile.profile_organization,
                profile_firstname = user_profile.profile_user.first_name,
                profile_lastname = user_profile.profile_user.last_name,
                profile_email = user_profile.profile_user.email,
                profile_phone = user_profile.profile_phone,
                profile_type = user_profile.profile_type,
                user_roles = UAABuilder.get_role_data(id=user_with_role.user_with_role_role.role_unique_id if user_with_role else None),
            )
        # except Exception as e:
        #     return UserProfileAndRoleObjects()
        
