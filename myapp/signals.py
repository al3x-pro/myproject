from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Entry, Category

@receiver([post_save, post_delete], sender=Entry)
def invalidate_entry_caches(sender, **kwargs):
    cache.delete('categories_with_counts')
    cache.delete('entry_author_count')

@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, **kwargs):
    cache.delete('categories_with_counts')