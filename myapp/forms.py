from django import forms
from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['title', 'text', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your entry here...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }
