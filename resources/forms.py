# File: Desktop/Prime/resources/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import Resource, ResourceRating, ResourceCategory, ResourceTag


class ResourceForm(forms.ModelForm):
    """Form for creating and editing resources"""
    
    # Free text input for tags
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'python, django, web development, tutorial'
        }),
        help_text="Enter comma-separated tags"
    )
    
    # Change to MultipleChoiceField for proper Select2 handling
    programming_languages = forms.MultipleChoiceField(
        required=False,
        choices=[],  # Will be populated in __init__
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control tech-select-multiple',
            'multiple': 'multiple',
        }),
        help_text="Type to search technologies, press Enter or click to select"
    )
    
    # Static list of technologies for Select2
    TECHNOLOGY_CHOICES = [
        ('Python', 'Python'),
        ('JavaScript', 'JavaScript'),
        ('Java', 'Java'),
        ('C++', 'C++'),
        ('C#', 'C#'),
        ('PHP', 'PHP'),
        ('Ruby', 'Ruby'),
        ('Go', 'Go'),
        ('Rust', 'Rust'),
        ('Swift', 'Swift'),
        ('Kotlin', 'Kotlin'),
        ('TypeScript', 'TypeScript'),
        ('Django', 'Django'),
        ('Flask', 'Flask'),
        ('FastAPI', 'FastAPI'),
        ('React', 'React'),
        ('Vue.js', 'Vue.js'),
        ('Angular', 'Angular'),
        ('Express.js', 'Express.js'),
        ('Spring Boot', 'Spring Boot'),
        ('Laravel', 'Laravel'),
        ('Ruby on Rails', 'Ruby on Rails'),
        ('HTML/CSS', 'HTML/CSS'),
        ('Bootstrap', 'Bootstrap'),
        ('Tailwind CSS', 'Tailwind CSS'),
        ('SASS/SCSS', 'SASS/SCSS'),
        ('jQuery', 'jQuery'),
        ('MySQL', 'MySQL'),
        ('PostgreSQL', 'PostgreSQL'),
        ('MongoDB', 'MongoDB'),
        ('SQLite', 'SQLite'),
        ('Redis', 'Redis'),
        ('Firebase', 'Firebase'),
        ('React Native', 'React Native'),
        ('Flutter', 'Flutter'),
        ('Android', 'Android'),
        ('iOS', 'iOS'),
        ('Xamarin', 'Xamarin'),
        ('AWS', 'AWS'),
        ('Docker', 'Docker'),
        ('Kubernetes', 'Kubernetes'),
        ('Azure', 'Azure'),
        ('Google Cloud', 'Google Cloud'),
        ('CI/CD', 'CI/CD'),
        ('Git', 'Git'),
        ('Linux', 'Linux'),
        ('Machine Learning', 'Machine Learning'),
        ('Data Science', 'Data Science'),
        ('TensorFlow', 'TensorFlow'),
        ('PyTorch', 'PyTorch'),
        ('Pandas', 'Pandas'),
        ('NumPy', 'NumPy'),
        ('R', 'R'),
        ('Tableau', 'Tableau'),
        ('Power BI', 'Power BI'),
        ('REST API', 'REST API'),
        ('GraphQL', 'GraphQL'),
        ('WebSockets', 'WebSockets'),
        ('Microservices', 'Microservices'),
        ('Blockchain', 'Blockchain'),
        ('IoT', 'IoT'),
        ('AR/VR', 'AR/VR'),
        ('Unity', 'Unity'),
        ('Unreal Engine', 'Unreal Engine'),
        ('Node.js', 'Node.js'),
        ('WordPress', 'WordPress'),
        ('Shopify', 'Shopify'),
        ('Figma', 'Figma'),
        ('Adobe XD', 'Adobe XD'),
        ('Photoshop', 'Photoshop'),
        ('Blender', 'Blender'),
        ('Jest', 'Jest'),
        ('Cypress', 'Cypress'),
        ('Selenium', 'Selenium'),
        ('JUnit', 'JUnit'),
        ('pytest', 'pytest')
    ]
    
    class Meta:
        model = Resource
        fields = [
            'title', 'description', 'resource_type', 'category', 'difficulty',
            'url', 'file', 'thumbnail', 'estimated_duration'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for your resource...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what this resource covers and how it helps students...'
            }),
            'resource_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
            }),
            'difficulty': forms.Select(attrs={
                'class': 'form-control',
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/your-resource'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a file to upload...'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Add a thumbnail image...'
            }),
            'estimated_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estimated time in minutes to complete',
                'min': 1
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholder texts to dropdowns
        self.fields['resource_type'].empty_label = 'Select resource type...'
        self.fields['category'].empty_label = 'Choose a category...'
        self.fields['difficulty'].empty_label = 'Select difficulty level...'
        
        # Set choices for programming_languages
        self.fields['programming_languages'].choices = self.TECHNOLOGY_CHOICES
        
        # Pre-populate tags_input for editing
        if self.instance and self.instance.pk:
            tag_names = [tag.name for tag in self.instance.tags.all()]
            self.fields['tags_input'].initial = ', '.join(tag_names)
            
            # Pre-populate programming_languages for editing
            if self.instance.programming_languages:
                # Convert comma-separated string to list for initial data
                tech_list = [tech.strip() for tech in self.instance.programming_languages.split(',') if tech.strip()]
                self.initial['programming_languages'] = tech_list
    
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
    
    def save(self, commit=True):
        # Get the tags data BEFORE saving
        tags_input = self.cleaned_data.get('tags_input', '')
        tag_names = []
        if tags_input:
            tag_names = [name.strip().lower() for name in tags_input.split(',') if name.strip()]
        
        # Get programming languages data
        programming_languages = self.cleaned_data.get('programming_languages', [])
        
        # Save the resource instance first
        resource = super().save(commit=False)
        
        # Set programming_languages as comma-separated string
        if programming_languages:
            resource.programming_languages = ', '.join(programming_languages)
        else:
            resource.programming_languages = ''
        
        if commit:
            # Save the resource to get an ID
            resource.save()
            
            # NOW handle tags after resource has been saved and has an ID
            if tag_names:
                # Clear existing tags (for editing existing resources)
                if self.instance and self.instance.pk:
                    resource.tags.clear()
                
                # Create/get tags and add them
                for tag_name in tag_names:
                    tag, created = ResourceTag.objects.get_or_create(name=tag_name)
                    resource.tags.add(tag)
            
            # Save many-to-many relationships
            self.save_m2m()
        
        return resource


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
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})  
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