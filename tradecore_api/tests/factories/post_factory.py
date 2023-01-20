"""Factory for Post objects."""

import factory

from tradecore_api.models import Post
from tradecore_api.tests.factories.user_factory import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    """Builds saved posts, creating an author when none is supplied."""

    class Meta:
        model = Post
        skip_postgeneration_save = True

    author = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Post title {n}")
    description = factory.Faker("paragraph")
