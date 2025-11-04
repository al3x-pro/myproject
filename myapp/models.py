from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Entry(models.Model):
    class Category(models.TextChoices):
        LEARNING = 'LE', 'Learning'
        LIFESTYLE = 'LI', 'Lifestyle'
        MEAL = 'ME', 'Meal'

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=2, choices=Category.choices,
         default=Category.LIFESTYLE)
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
