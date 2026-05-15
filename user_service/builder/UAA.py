from dto.UAA import GroupedPermissionsObjects, UserPermisionObjects, UserRoleObjects
from uaa.models import UserPermissionsGroup, UserRoles, UsersWithRoles


class UAABuilder:
    def get_group_permissions_data(id):
        pergroup=UserPermissionsGroup.objects.filter(permission_group_unique_id=id).first()

        perm_list = []
        for permision in pergroup.get_group_permisions():
            perm_list.append(UserPermisionObjects(
                id = permision.primary_key,
                permission_unique_id = permision.permission_unique_id,
                permission_name = permision.permission_name,
                permission_code = permision.permission_code
            ))

        return GroupedPermissionsObjects(
            id = pergroup.primary_key,
            permission_group_unique_id = pergroup.permission_group_unique_id,
            permission_group_name = pergroup.permission_group_name,
            permission_group_is_global = pergroup.permission_group_is_global,
            permissions = perm_list,
        )
    
    def get_role_data(id):
        try:
            role=UserRoles.objects.filter(role_unique_id = id).first()
            print("Role: ", role)
            permissions_list=[]
            for permision in role.get_role_permissions():
                permissions_list.append(
                    UserPermisionObjects(
                        id = permision.role_with_permission_permission.primary_key,
                        permission_unique_id = permision.role_with_permission_permission.permission_unique_id,
                        permission_name = permision.role_with_permission_permission.permission_name,
                        permission_code = permision.role_with_permission_permission.permission_code,
                    )
                )

            return UserRoleObjects(
                id = role.primary_key,
                role_unique_id = role.role_unique_id,
                role_name = role.role_name,
                role_description = role.role_description,
                role_permissions = permissions_list
            )
        except:
            return UserRoleObjects()

