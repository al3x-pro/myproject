from django import forms
from .models import Entry, Comment, Category
from mptt.forms import TreeNodeChoiceField


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['title', 'text', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter title'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your entry here...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }


class CommentForm(forms.ModelForm):
    """Form for creating comments"""
    
    class Meta:
        model = Comment
        fields = ['text', 'entry', 'parent']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add a comment',
                'rows': 3
            }),
            'entry': forms.HiddenInput(),
            'parent': forms.HiddenInput()
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entry'].required = True
        self.fields['parent'].required = False



class EntrySearchForm(forms.Form):
    q = forms.CharField()
    c = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['c'].required = False
        self.fields['q'].widget.attrs.update(
            {'data-bs-toggle': 'dropdown',
             'class': 'form-control menudd',}
        )