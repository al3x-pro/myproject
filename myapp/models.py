from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse

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

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('entry-detail', kwargs={'pk': self.pk})


class Comment(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE,
                               related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True,
                                on_delete=models.CASCADE, related_name='replies')
    
    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f'Comment by {self.author} on {self.entry}'
    
    @property
    def is_reply(self):
        return self.parent is not None