"""
schema.py
----------
Root GraphQL schema. Wires Query and Mutation together.
Import this in urls.py.

Nothing else lives here. All types, queries, and mutations
are defined in their own files and imported here.
"""

import graphene
from accounts.schema import Query as AccountsQuery
from accounts.views import Mutation as AccountsMutation
from uaa.schema import Query as UaaQuery
from uaa.views import Mutation as UaaMutation

class Query( AccountsQuery, UaaQuery, graphene.ObjectType):
    pass

class Mutation( AccountsMutation, UaaMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
