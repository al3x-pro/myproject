from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.defaultfilters import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.db.models import Count
import uuid
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError

User = get_user_model()


class EntryManager(models.Manager):
    def get_queryset(self):
            return (
            super().get_queryset()
            .select_related('author__profile')
            .annotate(total_comments=Count('comments', distinct=True)
            ) 
        )
    

class Entry(models.Model):

    class Category(models.TextChoices):
        STUDY = "ST", "Education"
        LIFESTYLE = "LS", "Lifestyle"
        HEALTH = "HE", "Health & Wellness"

    id = models.BigAutoField(primary_key=True)

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    title = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(4)]
    )

    category = models.CharField(
        max_length=2,
        choices=Category.choices,
    )

    text = models.TextField()

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    favorites = models.ManyToManyField(
        User,
        related_name="favorite_entries",
        blank=True
    )

    likes = models.ManyToManyField(
        User,
        related_name="liked_entries",
        blank=True
    )

    is_published = models.BooleanField(default=False)

    published = EntryManager()
    objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_published", "-created_at"]),
            models.Index(fields=["author", "is_published"]),
            models.Index(fields=["category", "is_published"]),
        ]

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("myapp:entry-detail", kwargs={"public_id": self.public_id})
    
    

class Comment(MPTTModel):
    MAX_DEPTH = 5

    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    text = models.TextField(
        validators=[MinLengthValidator(2)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_published = models.BooleanField(default=False)

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class MPTTMeta:
        order_insertion_by = ["created_at"]

    class Meta:
        indexes = [
            models.Index(fields=["entry", "is_published", "created_at"]),
            models.Index(fields=["author", "is_published"]),
        ]

    def clean(self):
        super().clean()
        if self.parent_id and self.pk and self.parent_id == self.pk:
            raise ValidationError("A comment cannot be its own parent.")
        if self.parent and self.parent.level >= self.MAX_DEPTH:
            raise ValidationError(f"Comments cannot exceed depth {self.MAX_DEPTH}.")

    def __str__(self):
        return f"{self.author} on '{self.entry}': {self.text[:40]}"
