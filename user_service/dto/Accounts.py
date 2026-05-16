import graphene
from dto.UAA import UserRoleObjects
from dto.Response import PageObject, ResponseObject

#Profile
class UserProfileInputObject(graphene.InputObjectType):
    profile_unique_id = graphene.String()
    profile_organization = graphene.String()
    profile_firstname = graphene.String(required=True)
    profile_lastname = graphene.String(required=True)
    profile_email = graphene.String(required=True)
    profile_phone = graphene.String(required=True)
    profile_type = graphene.String()
    # role_unique_id = graphene.String(required=True)
    # profile_password = graphene.String(required=True)


class UserInputObjectType(graphene.InputObjectType):
    first_name = graphene.String()
    last_name = graphene.String()
    username = graphene.String()
    email = graphene.String()

class EmailDataInputObject(graphene.InputObjectType):
    email_type = graphene.String()
    email = graphene.String()
    user = UserInputObjectType()
    request_token = graphene.String()


class UserProfileObject(graphene.ObjectType):
    id = graphene.String()
    profile_unique_id = graphene.String()
    profile_organization = graphene.String()
    profile_firstname = graphene.String()
    profile_lastname = graphene.String()
    profile_email = graphene.String() 
    profile_phone = graphene.String()
    profile_type = graphene.String()
    user_roles = graphene.Field(UserRoleObjects)


class UserFilteringInputObject(graphene.InputObjectType):
    profile_unique_id = graphene.String()
    # role_unique_id = graphene.String()
    page_number = graphene.Int()
    items_per_page = graphene.Int()

class UserProfileResponseObject(graphene.ObjectType):
    data = graphene.List(UserProfileObject)
    response = graphene.Field(ResponseObject)
    page = graphene.Field(PageObject)


class SetPasswordFilteringInputObject(graphene.InputObjectType):
    request_token = graphene.String()
    user_password = graphene.String()

class ChangePasswordFilteringInputObject(graphene.InputObjectType):
    old_password = graphene.String()
    new_password = graphene.String()

class ForgotPasswordFilteringInputObject(graphene.InputObjectType):
    user_email = graphene.String()

class ActivateDeactivateFilteringInputObject(graphene.InputObjectType):
    profile_unique_id = graphene.String()
    profile_is_active = graphene.Boolean()
