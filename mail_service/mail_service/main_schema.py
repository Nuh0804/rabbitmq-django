import graphene
from mailer.views import Mutation 
from mailer.schema import Query

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    auto_camelcase=True,
)
