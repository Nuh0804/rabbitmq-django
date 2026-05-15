from django.shortcuts import render

# Create your views here.
from datetime import datetime, timedelta
from django.utils import timezone
from dotenv import dotenv_values
import graphene
from builder.Account import UserProfileBuilder
from dto.Response import ResponseObject
import pytz
from dto.Accounts import *
from django.db import transaction
from django.contrib.auth.models import User
from accounts.models import  *
from uaa.models import UserRoles, UsersWithRoles
# from utils.EmailUtils import CustomEmailBackend
from utils.UserUtils import UserUtils
# from utils.Validator import Validator

config = dotenv_values(".env")


class CreateUserMutation(graphene.Mutation):
    class Arguments:
        input = UserProfileInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(UserProfileObject)

    @classmethod
    @transaction.atomic
    def mutate(self, root, info,  input):
        user_role = UserRoles.objects.filter(role_name="Organization", role_is_active=True).first()
        # if user_role is None:
        #     return self(response=ResponseObject.get_response(id="10"))
        
        if User.objects.filter(email=input.profile_email).exists():
            return self(response=ResponseObject.get_response(id="12"))
        else:
            user = User.objects.create(
                first_name=input.profile_firstname, 
                last_name=input.profile_lastname, 
                username=input.profile_email, 
                email=input.profile_email,
            )

            user_profile = UserProfile.objects.create(
                profile_phone=input.profile_phone if input.profile_phone else None,
                profile_user=user,
                profile_organization  = input.profile_organization,
            )
            UsersWithRoles.objects.create(
             user_with_role_role = user_role,
             user_with_role_user = user,
            )



#         user = User.objects.create(
#             first_name=input.profile_firstname, 
#             last_name=input.profile_lastname, 
#             username=input.profile_email, 
#             email=input.profile_email
#         )
        
#         user.set_password(input.profile_password)

#         user.save()



#         user_profile = UserProfile.objects.create(
#             profile_phone=input.profile_phone if input.profile_phone else None,
#             profile_user=user,
#             profile_affiliated_organization  = input.profile_organization,
#             profile_type = input.profile_type
#         )

#         UsersWithRoles.objects.create(
#             user_with_role_role = user_role,
#             user_with_role_user = user,
#         )
        
        request_token = UserUtils.get_unique_token()
                
        # ActivateAccountTokenUser.objects.create(
        #     token_user = user,
        #     token_token = request_token
        # )
        
        SavePasswordRequestUsers.objects.create(
            save_pswd_user = user,
            save_pswd_token = request_token
        )

        #TODO switch with the email service
        # url = config['FRONTEND_DOMAIN'] + f"/auth/setPwd/{request_token}"
        # body = {
        #     'receiver_details': user.email,
        #     'user': user,
        #     'url': url,
        #     'subject': "my site Activate Account"
        # }        

        # CustomEmailBackend.send_messages(body, '../htmls/create_password.html')
        
        
        response_body = UserProfileBuilder.get_user_profile_data(id=user_profile.profile_unique_id)
        return self(response=ResponseObject.get_response(id="1"), data=response_body)



class UpdateUsersMutation(graphene.Mutation):
    class Arguments:
        input = UserProfileInputObject(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(UserProfileObject)

    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])    
    def mutate(cls, root, info, input):
        try:
            profile = UserProfile.objects.filter(profile_is_active=True, profile_unique_id=input.profile_unique_id).first()

            if profile is None:
                return cls(response=ResponseObject.get_response(id="6"), data=None)

            # Update profile information
            profile.profile_firstname = input.profile_firstname
            profile.profile_lastname = input.profile_lastname
            profile.profile_email = input.profile_email
            profile.profile_phone = input.profile_phone
            profile.profile_organization = input.profile_organization
            if input.profile_type:
                profile.profile_type = input.profile_type.value 

            profile.save()

            # Update user information
            user = profile.profile_user
            user.firstname = input.user_firstname
            user.lastname = input.user_lastname
            user.email = input.user_email
            user.phone = input.user_phone
            user.phone = input.user_phone
            user.organization = input.user_organization
            user.save()

            # Update user's role
            user_role = UserRoles.objects.filter(role_unique_id=input.role_unique_id).first()
            print("role entered" ,input.role_unique_id)
            if user_role:
                UsersWithRoles.objects.update_or_create(user_with_role_user = user, defaults={"user_with_role_role": user_role})
                print(user_role,"his role,,,")

            response_body = UserProfileBuilder.get_user_profile_and_role_data(id=profile.profile_unique_id)
            return cls(response=ResponseObject.get_response(id="1"), data=response_body)
        except Exception as e:
            print(e)
            return cls(response=ResponseObject.get_response(id="5"), data=None)

    
class DeleteUsersMutation(graphene.Mutation):
    class Arguments:
        profile_unique_id = graphene.String(required=True)

    response = graphene.Field(ResponseObject)

    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])
    def mutate(self, root, info,  profile_unique_id):

        admin_profile = UserProfile.objects.filter(profile_unique_id=profile_unique_id).first()

        admin_profile.profile_type = ""
        admin_profile.profile_is_active = False
        admin_profile.save()
        admin_profile.profile_user.is_active = False
        admin_profile.profile_user.save()

        return self(response=ResponseObject.get_response(id="1"))
    
    
class UpdateMyProfileMutation(graphene.Mutation):
    class Arguments:
        input = UserProfileInputObject()

    response = graphene.Field(ResponseObject)
    data = graphene.Field(UserProfileObject)

    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])    
    def mutate(cls, root, info, input):
        profile_id = UserUtils.__profile__(info.context.headers)
        profile = UserProfile.objects.filter(profile_unique_id=profile_id, profile_is_active=True).first()

        if profile is None:
            return cls(response=ResponseObject.get_response(id="10"), data=None)

        if input.profile_phone is not None:
            profile.profile_phone = input.profile_phone
        if input.profile_firstname is not None:
            profile.profile_firstname = input.profile_firstname
        if input.profile_firstname is not None:
            profile.profile_firstname = input.profile_firstname
        profile.save()

        user = profile.profile_user
        if input.user_first_name is not None:
            user.first_name = input.user_first_name
        if input.user_last_name is not None:
            user.last_name = input.user_last_name
        if input.user_email is not None:
            user.email = input.user_email
        user.save()

        response_body = UserProfileBuilder.get_user_profile_data(id=profile.profile_unique_id)

        return cls(response=ResponseObject.get_response(id="1"), data=response_body)
        

        '''ToDo: Implement'''

class ForgotPasswordMutation(graphene.Mutation):
    class Arguments:
        input = ForgotPasswordFilteringInputObject()
    
    response = graphene.Field(ResponseObject)
    
    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])
    def mutate(self, root, info, input):
            try:

                user = User.objects.filter(username=input.user_email).first()
                if user is None:
                    return self(response=ResponseObject.get_response(id="10"))
                
                request_token = UserUtils.get_unique_token()
                naive_datetime = datetime.now()
                naive_datetime_with_timezone = timezone.make_aware(naive_datetime, timezone.utc)

                expiration_time = naive_datetime_with_timezone + timedelta(minutes=30)
                print(expiration_time)
                password_requests = ForgotPasswordRequestUser.objects.filter(request_user=user,).first()
                
                if password_requests:
                    time_diff = naive_datetime_with_timezone.second - password_requests.request_created_date.second
                    time_diff = time_diff/60
                    if time_diff<30:
                        return self(response=ResponseObject(id='21',status=False ,code=9020,
                                                                        message="Please wait 30 minutes to reset password again."))
            
                ForgotPasswordRequestUser.objects.create(
                    request_user=user,
                    request_token=request_token,
                    request_expiration_time=expiration_time  
                )
                #TODO switch with the email service
                # url = config['FRONTEND_DOMAIN'] + f"auth/password-reset/{request_token}"

                # body = {
                #     'receiver_details': user.email,
                #     'user': user,
                #     'url': url,
                #     'subject': "my site Password Reset"
                # }

                # CustomEmailBackend.send_messages(body, '../htmls/forget_password.html')

                return self(response=ResponseObject.get_response(id="1"))
            except:
                return self(response=ResponseObject.get_response(id="5"))
        

class ResetPasswordMutation(graphene.Mutation):
    class Arguments:
        input = SetPasswordFilteringInputObject()
    
    response = graphene.Field(ResponseObject)
    
    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])
    def mutate(self, root, info, input):
        try: 
            requested_token = ForgotPasswordRequestUser.objects.filter(request_token = input.request_token).first()

            current_datetime = datetime.now(pytz.UTC)
            print(current_datetime)
            print(requested_token.request_expiration_time)

            request_token_expired = requested_token.request_expiration_time < current_datetime
            print("request token expired?",request_token_expired)

            if request_token_expired or requested_token is None:
                return self(response= ResponseObject.get_response(id="19"))
            
            user =requested_token.request_user
            user.set_password(input.user_password)
            user.save()
            requested_token.request_is_used = True
            requested_token.save()

            return self(response=ResponseObject.get_response(id="1"))
        except:
            return self(response=ResponseObject.get_response(id="5"))
        
        
class ChangePasswordMutation(graphene.Mutation):
    class Arguments:
        input = ChangePasswordFilteringInputObject()
    response = graphene.Field(ResponseObject)

    @classmethod
    # @has_mutation_access(permissions=['can_configure_system_settings_details'])
    def mutate(cls, root, info, input):
        try:
            user_data = UserUtils.__profile__(info.context.headers)
            if user_data is None:
                return cls(response=ResponseObject.get_response(id="6"))
            user_profile = UserProfile.objects.filter(
                profile_unique_id = user_data
            ).first()                     
            
            user = User.objects.get(pk=user_profile.profile_user.pk)
            
            if not user.check_password(input.old_password):
                return cls(response=ResponseObject.get_response(id="12"))
            
            user.set_password(input.new_password)
            user.save()
            user_profile.profile_default_password = False
            user_profile.save()
            
            return cls(response=ResponseObject.get_response(id='1'))

        except:
            return cls(response=ResponseObject.get_response(id='5'))




class SetPasswordMutation(graphene.Mutation):
    class Arguments:
        input = SetPasswordFilteringInputObject()
    
    response = graphene.Field(ResponseObject)
    
    @classmethod
    def mutate(self, root, info, input):
        try: 
            requested_token = SavePasswordRequestUsers.objects.filter( save_pswd_token = input.request_token, save_pswd_is_used = False).first()

            # current_datetime = datetime.now(pytz.UTC)
            # print(requested_token.request_expiration_time)

            # request_token_expired = requested_token.save_pswd_expiration_time < current_datetime
            # print("request token expired?",request_token_expired)

            if requested_token is None:
                return self(response= ResponseObject.get_response(id="18"))
            
            user =requested_token.save_pswd_user
            user.set_password(input.user_password)
            user.save()
            requested_token.save_pswd_is_used = True
            requested_token.save()

            return self(response=ResponseObject.get_response(id="1"))
        except:
            return self(response=ResponseObject.get_response(id="5"))

class ResendPasswordSetEmail(graphene.Mutation):
    class Arguments:
        input = ForgotPasswordFilteringInputObject()
    response = graphene.Field(ResponseObject)

    @classmethod
    def mutate(self, root, info, input):
            # print("niajee")
            # prev_request = SavePasswordRequestUsers.objects.filter(save_pswd_user = input.user_email, save_pswd_is_used = False).first()
            user = User.objects.filter(email=input.user_email).first()
            if user is None:
                return self(response = ResponseObject.get_response(id="20"))
            
            request_token = UserUtils.get_unique_token()
            
        
            SavePasswordRequestUsers.objects.create(
                save_pswd_user = user,
                save_pswd_token = request_token
            )
            #TODO switch with the email service
            # url = config['FRONTEND_DOMAIN'] + f"/auth/setPwd/{request_token}"
            # body = {
            #     'receiver_details': user.email,
            #     'user': user,
            #     'url': url,
            #     'subject': "my site Activate Account"
            # }        

            # CustomEmailBackend.send_messages(body, '../htmls/create_password.html')
            return self(response=ResponseObject.get_response(id="1"))


            



class Mutation(graphene.ObjectType):
    create_user_mutation = CreateUserMutation.Field()
    update_user_mutation = UpdateUsersMutation.Field()
    delete_user_mutation = DeleteUsersMutation.Field()
    update_my_profile_mutations = UpdateMyProfileMutation.Field()
    forgot_password_mutation = ForgotPasswordMutation.Field()
    reset_password_mutation = ResetPasswordMutation.Field()
    change_password_mutation= ChangePasswordMutation.Field()
    set_password_mutation = SetPasswordMutation.Field()
    resend_password_setEmail = ResendPasswordSetEmail.Field()

