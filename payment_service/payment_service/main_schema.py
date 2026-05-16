import graphene
from Payment.views import Mutation 
from Payment.schema import Query

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    auto_camelcase=True,
)
