"""
schema.py
----------
Root GraphQL schema. Wires Query and Mutation together.
Import this in urls.py.

Nothing else lives here. All types, queries, and mutations
are defined in their own files and imported here.
"""

import graphene
from .queries import Query
from .mutations import Mutation

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    # auto_camelcase=True is the default — GraphQL field names will be
    # camelCase (myOrders) even though Python uses snake_case (my_orders)
    auto_camelcase=True,
)
