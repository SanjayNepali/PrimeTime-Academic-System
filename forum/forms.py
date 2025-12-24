# File: forum/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import ForumPost, ForumReply, ForumCategory, ForumTag


class ForumPostForm(forms.ModelForm):
    """Form for creating and editing forum posts"""
    
    tags = forms.ModelMultipleChoiceField(
        queryset=ForumTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select relevant tags (maximum 5)"
    )
    
    class Meta:
        model = ForumPost
        fields = [
            'title', 'content', 'post_type', 'category', 
            'tags', 'programming_languages'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your question or discussion topic...',
                'maxlength': 200,
                'required': True
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Provide details, context, and what you\'ve tried...',
                'required': True
            }),
            'post_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'programming_languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Django, JavaScript (comma-separated)'
            })
        }
        labels = {
            'title': 'Title',
            'content': 'Content',
            'post_type': 'Post Type',
            'category': 'Category',
            'tags': 'Tags',
            'programming_languages': 'Programming Languages / Technologies'
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 10:
            raise ValidationError('Title must be at least 10 characters long.')
        return title
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if len(content) < 20:
            raise ValidationError('Content must be at least 20 characters long.')
        return content
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        if tags and tags.count() > 5:
            raise ValidationError('You can select a maximum of 5 tags.')
        return tags


class ForumReplyForm(forms.ModelForm):
    """Form for replying to forum posts"""
    
    class Meta:
        model = ForumReply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your answer or thoughts...',
                'required': True
            })
        }
        labels = {
            'content': 'Your Reply'
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if len(content) < 5:
            raise ValidationError('Reply must be at least 5 characters long.')
        return content


class ForumSearchForm(forms.Form):
    """Form for searching forum posts"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search posts...'
        })
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=ForumCategory.objects.filter(is_active=True),
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    post_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + ForumPost.POST_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All'),
            ('open', 'Open'),
            ('solved', 'Solved'),
            ('pinned', 'Pinned')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-last_activity', 'Recent Activity'),
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-views', 'Most Viewed'),
        ],
        initial='-last_activity',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class FlagPostForm(forms.Form):
    """Form for flagging inappropriate posts"""
    
    reason = forms.ChoiceField(
        choices=[
            ('spam', 'Spam or Advertisement'),
            ('offensive', 'Offensive Content'),
            ('duplicate', 'Duplicate Post'),
            ('irrelevant', 'Off-Topic or Irrelevant'),
            ('other', 'Other')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional details (optional)...'
        })
    )