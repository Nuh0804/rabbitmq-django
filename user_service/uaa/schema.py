from graphene import ObjectType
import graphene
from builder.UAA import UAABuilder
from dto.Response import ResponseObject, get_paginated_data


from dto.UAA import UserRoleObjects,UserRoleResponseObject,UserRolesInputObjects
from uaa.models import UserRoles, UsersWithRoles

from utils.UserUtils import UserUtils

from django.db.models import Q

class Query(ObjectType):
    get_user_roles = graphene.Field(UserRoleResponseObject)

    def resolve_get_user_roles(self, info,**kwargs):
        try:
            roles=UserRoles.objects.filter().all()

            role_list = []

            for role in roles:
                role_list.append(UAABuilder.get_role_data(role.role_unique_id))
            
            return info.return_type.graphene_type(response=ResponseObject.get_response(id="1"),data=role_list)
        
        except:
            return info.return_type.graphene_type(response=ResponseObject.get_response(id="4"))

  
