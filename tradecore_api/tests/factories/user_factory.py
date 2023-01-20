"""Factory for User objects."""

import factory

from tradecore_api.models import User

DEFAULT_PASSWORD = "factory-pass-4821"


class UserFactory(factory.django.DjangoModelFactory):
    """Builds saved users with a correctly hashed password.

    Two details matter here.  The attributes are ``factory.Sequence`` /
    ``factory.Faker``, so they are evaluated per instance rather than once at
    import -- a plain ``faker.email()`` class attribute gives every user the
    same address and the second ``create()`` violates the unique constraint.
    And ``_create`` goes through ``create_user`` so the password is hashed:
    the default manager ``create()`` stores it as plain text, which silently
    makes every authentication test unable to log in.
    """

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    geolocation_data = factory.Dict({})
    joined_on_holiday = False

    class Params:
        password = DEFAULT_PASSWORD

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", DEFAULT_PASSWORD)
        return model_class.objects.create_user(*args, password=password, **kwargs)
