# File: Desktop/Prime/resources/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import Resource, ResourceRating, ResourceCategory, ResourceTag


class ResourceForm(forms.ModelForm):
    """Form for creating and editing resources"""
    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'resource_type', 'category', 'difficulty',
            'url', 'file', 'thumbnail', 'tags', 'programming_languages', 'estimated_duration'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter resource title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the resource...'
            }),
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/resource'
            }),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 8
            }),
            'programming_languages': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python, Django, React (comma-separated)'
            }),
            'estimated_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duration in minutes',
                'min': 1
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        url = cleaned_data.get('url')
        file = cleaned_data.get('file')
        
        # Either URL or file must be provided
        if not url and not file:
            raise ValidationError('Either a URL or a file must be provided.')
        
        return cleaned_data
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 50MB)
            if file.size > 50 * 1024 * 1024:
                raise ValidationError('File size must not exceed 50MB.')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.zip', '.mp4', '.mp3']
            file_name = file.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise ValidationError('File type not allowed. Allowed: PDF, DOC, DOCX, PPT, PPTX, ZIP, MP4, MP3')
        
        return file


class ResourceFilterForm(forms.Form):
    """Form for filtering resources"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search resources...'
        })
    )
    
    resource_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Resource.RESOURCE_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=ResourceCategory.objects.all(),
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    difficulty = forms.ChoiceField(
        required=False,
        choices=[('', 'All Levels')] + Resource.DIFFICULTY_LEVELS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    tags = forms.ModelMultipleChoiceField(
        required=False,
        queryset=ResourceTag.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-average_rating', 'Highest Rated'),
            ('-views', 'Most Viewed'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A')
        ],
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ResourceRatingForm(forms.ModelForm):
    """Form for rating resources"""
    
    class Meta:
        model = ResourceRating
        fields = ['rating', 'review']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)]
            ),
            'review': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Share your thoughts about this resource...'
            })
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise ValidationError('Rating must be between 1 and 5.')
        return rating


class BulkResourceUploadForm(forms.Form):
    """Form for admins to bulk upload resources"""
    
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'
        }),
        help_text='Upload a CSV file with columns: title, description, resource_type, url, difficulty, programming_languages'
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            if not file.name.endswith('.csv'):
                raise ValidationError('Only CSV files are allowed.')
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('CSV file must not exceed 5MB.')
        
        return file