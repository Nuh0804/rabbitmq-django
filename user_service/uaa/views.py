import graphene
from graphql import build_schema

from dto.Response import ResponseObject
from dto.UAA import UserRoleObjects, UserRolesInputObjects
from builder.UAA import UAABuilder
from uaa.models import UserPermissions, UserRoles, UserRolesWithPermissions
from utils.UserUtils import UserUtils


class CreateUserRolesMutation(graphene.Mutation):
    class Arguments:
        input = UserRolesInputObjects(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(UserRoleObjects)
    
    @classmethod
    # @has_mutation_access(permissions=['can_manage_settings'])
    def mutate(self, root, info,  input):
        try:
            # if UserRoles.objects.filter(role_name=input.role_name, role_is_active = True).exists():
            #     return self(ResponseObject.get_response(id="17"))
            
            # profile = UserUtils.get_user(info.context.headers)
            # institution_unique_id = profile.get("profile_institution_unique_id")
            # if institution_unique_id is None:
            #     return self(ResponseObject.get_response(id="8"))
            
            # institution = Institution.objects.filter(institution_unique_id=institution_unique_id).first()

            created_role = UserRoles.objects.create(
                role_name=input.role_name, 
                role_description=input.role_description,
            )
            print("data",input)

            for permision in input.role_permissions:
                UserRolesWithPermissions.objects.create(
                    role_with_permission_role_id=created_role.primary_key,
                    role_with_permission_permission=UserPermissions.objects.filter(permission_unique_id=permision).first(),
                )

            role=UAABuilder.get_role_data(created_role.role_unique_id)    

            return self(ResponseObject.get_response(id="1"), data=role)
        
        except Exception as e:
            print(e)
            return self(ResponseObject.get_response(id="8"),data=None)


class UpdateUserRolesMutation(graphene.Mutation):
    class Arguments:
        input = UserRolesInputObjects(required=True)

    response = graphene.Field(ResponseObject)
    data = graphene.Field(UserRoleObjects)

    @classmethod
    def mutate(self, root, info,  input):
        try:
            profile = UserUtils.get_user(info.context.headers)
            institution_unique_id = profile.get("profile_institution_unique_id")
            
            if institution_unique_id is None:
                return self (ResponseObject.get_response(id="8"))
            # institution = Institution.objects.filter(institution_unique_id=institution_unique_id).first()
            
            role = UserRoles.objects.filter(role_unique_id=input.role_unique_id).first()
            role.role_name = input.role_name
            role.role_description = input.role_description
            # role.role_institution = institution
            role.save()
            
            UserRolesWithPermissions.objects.filter(role_with_permission_role=role).delete()

            for permision in input.role_permissions:
                UserRolesWithPermissions.objects.create(
                    role_with_permission_role=role,
                    role_with_permission_permission=UserPermissions.objects.filter(permission_unique_id=permision).first(),
                )

            role=UAABuilder.get_role_data(role.role_unique_id)
            
            return UpdateUserRolesMutation(ResponseObject.get_response(id="1"),data=role)
        except Exception as e:
            return UpdateUserRolesMutation(ResponseObject.get_response(id="8"),data=None)


class DeleteUserRolesMutation(graphene.Mutation):
    class Arguments: 
        role_unique_id = graphene.String(required=True)
    
    response = graphene.Field(ResponseObject)

    @classmethod
    # @has_mutation_access(permissions=['can_manage_institution_settings'])
    def mutate(self, root, info,  role_unique_id):
        try:
            UserRoles.objects.filter(role_unique_id=role_unique_id).delete()

            return DeleteUserRolesMutation(ResponseObject.get_response(id="1"))
        except Exception as e:
            return DeleteUserRolesMutation(ResponseObject.get_response(id="8"))

class Mutation(graphene.ObjectType):
    create_user_roles = CreateUserRolesMutation.Field()
    update_user_roles = UpdateUserRolesMutation.Field()
    delete_user_roles = DeleteUserRolesMutation.Field()
