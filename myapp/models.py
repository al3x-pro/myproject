from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.core.cache import cache

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
        return super().get_queryset().select_related('author', 'category').prefetch_related('comments')
    
    def get_author_count(self):
        cache_key = 'entry_author_count'
        count = cache.get(cache_key)
        if count is None:
            count = self.values('author').distinct().count()
            cache.set(cache_key, count, 300)  # 5 minutes
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
        indexes = [
            models.Index(fields=['entry', 'parent', '-created_at']),
            models.Index(fields=['parent', 'created_at']),
        ]

    def __str__(self):
        return f'Comment by {self.author} on {self.entry}'
    
    @property
    def is_reply(self):
        return self.parent is not None