from django.contrib import admin
from .models import Entry, Comment
from mptt.admin import MPTTModelAdmin


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'updated_at')
    list_filter = ('category', 'author', 'created_at')
    search_fields = ('title', 'text', 'author__username')
    ordering = ('-created_at',)

admin.site.register(Comment, MPTTModelAdmin)