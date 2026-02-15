from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Custom user model.
    Right now all users are gym owners.
    Later we can add roles (owner, staff, trainer).
    """
    pass