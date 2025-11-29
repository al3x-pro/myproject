from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class EmailOrUsernameModelBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using either their
    username or email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        
        try:
            user = user_model.objects.get(Q(username=username) | Q(email=username))
            if user.check_password(password):
                return user
        except user_model.DoesNotExist:
            return None

    def get_user(self, user_id):
        User = get_user_model()

        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None