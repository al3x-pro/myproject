from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.core.cache import cache
from django.db.models import Count

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(default="", max_length=100, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class EntryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('author', 'category')
    
    def get_author_count(self):
        count = cache.get_or_set(
            'entry_author_count',
            lambda: self.values('author').distinct().count(),
            300  # 5 minutes
        )
        return count


class Entry(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True,
                                 related_name='entries')
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    objects = EntryManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['-created_at', 'author']),
            models.Index(fields=['category']),
            models.Index(fields=['author']),
        ]

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('entry-detail', kwargs={'pk': self.pk})

