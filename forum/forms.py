# File: Desktop/Prime/forum/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import ForumPost, ForumReply, ForumCategory, ForumTag


class ForumPostForm(forms.ModelForm):
    """Form for creating and editing forum posts"""
    
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
                'minlength': 10
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Provide details, context, and what you\'ve tried...',
                'minlength': 20
            }),
            'post_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 6
            }),
            'programming_languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Django, JavaScript (comma-separated)'
            })
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 10:
            raise ValidationError('Title must be at least 10 characters long.')
        return title
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content) < 20:
            raise ValidationError('Content must be at least 20 characters long.')
        return content


class ForumReplyForm(forms.ModelForm):
    """Form for replying to forum posts"""
    
    class Meta:
        model = ForumReply
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your answer or thoughts...',
                'minlength': 5
            })
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
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
    
    tags = forms.ModelMultipleChoiceField(
        required=False,
        queryset=ForumTag.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-last_activity', 'Recent Activity'),
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-views', 'Most Viewed'),
            ('-upvotes__count', 'Most Upvoted')
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
        widget=forms.RadioSelect
    )
    
    details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional details (optional)...'
        })
    )


class ModeratePostForm(forms.Form):
    """Form for moderating posts (admin only)"""
    
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve Post'),
            ('hide', 'Hide Post'),
            ('delete', 'Delete Post'),
            ('pin', 'Pin Post'),
            ('unpin', 'Unpin Post')
        ],
        widget=forms.RadioSelect
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for action (optional)...'
        })
    )