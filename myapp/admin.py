from django.contrib import admin
from .models import Entry, Comment

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'updated_at')
    list_filter = ('category', 'author', 'created_at')
    search_fields = ('title', 'text', 'author__username')
    ordering = ('-created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('entry', 'author', 'created_at', 'is_reply')
    list_filter = ('author', 'created_at')
    search_fields = ('text', 'author__username', 'entry__title')
    ordering = ('-created_at',)