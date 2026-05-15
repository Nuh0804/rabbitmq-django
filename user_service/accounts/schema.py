from graphene import ObjectType
import graphene
from builder.Account import UserProfileBuilder
from dto.Response import ResponseObject, PageObject
from django.core.paginator import Paginator

from dto.Accounts import *
from accounts.models import UserProfile

from utils.UserUtils import UserUtils

from django.db.models import Q



class Query(ObjectType):
    get_users = graphene.Field(USerProfileResponseObject,filtering=UserFilteringInputObject(required=True))
    get_user_profile_and_role = graphene.Field(USerProfileResponseObject,filtering=UserFilteringInputObject())


  # @has_query_access(["can_manage_user"])
    def resolve_get_users(self, info, filtering=None, **kwargs):
        try:
            users = UserProfile.objects.values('profile_unique_id')

            paginated_user_data = Paginator(users, filtering.items_per_page if filtering.items_per_page else 10)
            required_page = paginated_user_data.page(filtering.page_number if filtering.page_number else 1)
            page_object = PageObject.get_page(required_page)

            paginated_user_data = list(map(lambda x: UserProfileBuilder.get_user_profile_and_role_data(str(x['profile_unique_id'])), required_page))
            return info.return_type.graphene_type(response=ResponseObject.get_response(id="1"), data = paginated_user_data, page=page_object)
        
        except Exception as e:
            print(e)
            return info.return_type.graphene_type(response=ResponseObject.get_response(id="8"), data = None) 

      


    def resolve_get_user_profile_and_role(self, info,**kwargs):
        # try:
        user_data = UserUtils.__profile__(info)
        if user_data is None:
                return info.return_type.graphene_type(response=ResponseObject.get_response(id="10"))

        profile = UserProfile.objects.filter(profile_unique_id=user_data).first()
        if profile is None:
                return info.return_type.graphene_type(response=ResponseObject.get_response(id="11"))

        user_object=UserProfileBuilder.get_user_profile_and_role_data(profile.profile_unique_id)
            
        return info.return_type.graphene_type(response=ResponseObject.get_response(id="1"),data=user_object)
        # except:
        #     return info.return_type.graphene_type(response=ResponseObject.get_response(id="13"),data=None)





        # filter_conditions = Q(profile_is_active=True)
    
        # profile = UserUtils.get_user(info.context.headers)
        
        # if not profile:
        #     return info.return_type.graphene_type(response=ResponseObject.get_response(id="0"))
        
        # if profile and profile.get("profile_type") not in ["SYSTEM_ADMIN", "INSTITUTION_ADMIN"]:
        #     filter_conditions &= Q(profile_unique_id=profile.get("profile_unique_id"))
        
        # if profile.get("profile_type")=="INSTITUTION_ADMIN":
        #     filter_conditions &= Q(profile_user_institution__institution_unique_id=profile.get("profile_institution_unique_id"))
        
        # if not filtering:
        #     return info.return_type.graphene_type(response=ResponseObject.get_response(id="7"))
        
        # if filtering.profile_unique_id:
        #     filter_conditions &= Q(profile_unique_id=filtering.profile_unique_id)
            
        # if filtering.profile_title:
        #     filter_conditions &= Q(profile_title=filtering.profile_title.value)
            
        # if filtering.profile_gender:
        #     filter_conditions &= Q(profile_gender=filtering.profile_gender.value)
            
        # if filtering.profile_type:
        #     filter_conditions &= Q(profile_type=filtering.profile_type.value)
        
        # if filtering.department_unit_unique_id:
        #     filter_conditions &= Q(profile_user_institution__department_instituion__department_unique_id=filtering.department_unit_unique_id)

        # if filtering.profile_role_unique_id:
        #     filter_conditions &= Q(profile_unique_id__in=list(UsersWithRoles.objects.filter(user_with_role_role__role_unique_id=filtering.profile_role_unique_id).values_list('user_with_role_user__profile_user__profile_unique_id', flat=True)))

        # response, page, data = get_paginated_data(UserProfile, filter_conditions, filtering.page_number, Account.get_user_profile_data, lookup="profile_unique_id", items_per_page=filtering.items_per_page)
            
        # return info.return_type.graphene_type(response=response, page=page, data=data)