import graphene
# from tanrail_dto.Response import ResponseObject

class UserPermisionInputObjects(graphene.InputObjectType):
    group = graphene.String()
    name = graphene.String()
    code = graphene.String()


class UserRolesInputObjects(graphene.InputObjectType):
    role_unique_id = graphene.String()
    institution_unique_id = graphene.String()
    role_name = graphene.String()
    role_description = graphene.String()
    role_permissions = graphene.List(graphene.String)


class UserPermisionObjects(graphene.ObjectType):
    id = graphene.String()
    permission_unique_id = graphene.String()
    permission_name = graphene.String()
    permission_code = graphene.String()


class GroupedPermissionsObjects(graphene.ObjectType):
    id = graphene.String()
    permission_group_unique_id = graphene.String()
    permission_group_name = graphene.String()
    permission_group_is_global = graphene.Boolean()
    permissions = graphene.List(UserPermisionObjects)


class GroupedPermissionsResponseObject(graphene.ObjectType):
    # response = graphene.Field(ResponseObject)
    data = graphene.List(GroupedPermissionsObjects)


class PermisionFilteringInputObjects(graphene.InputObjectType):
    group_is_global = graphene.Boolean()
    permission_group_unique_id = graphene.String()


class UserRoleObjects(graphene.ObjectType):
    id = graphene.String()
    role_unique_id = graphene.String()
    role_name = graphene.String()
    role_description = graphene.String()
    role_permissions = graphene.List(UserPermisionObjects)


class UserRoleResponseObject(graphene.ObjectType):
    # response = graphene.Field(ResponseObject)
    data = graphene.List(UserRoleObjects)


