# File: Desktop/Prime/resources/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.utils import timezone
import csv

from .models import (
    Resource, ResourceCategory, ResourceTag, ResourceRating,
    ResourceRecommendation, ResourceViewHistory, ResourceLike 
)
from .forms import ResourceForm, ResourceFilterForm, ResourceRatingForm, BulkResourceUploadForm
from .recommender import ResourceRecommendationEngine
from accounts.models import User


@login_required
def resource_list(request):
    """List all resources with filtering and search"""
    
    # Get filter parameters
    filter_form = ResourceFilterForm(request.GET)
    
    # Base queryset
    resources = Resource.objects.filter(is_approved=True).select_related(
        'author', 'category'
    ).prefetch_related('tags')
    
    # Apply filters
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        resource_type = filter_form.cleaned_data.get('resource_type')
        category = filter_form.cleaned_data.get('category')
        difficulty = filter_form.cleaned_data.get('difficulty')
        tags = filter_form.cleaned_data.get('tags')
        sort_by = filter_form.cleaned_data.get('sort_by') or '-created_at'
        
        if search:
            resources = resources.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(programming_languages__icontains=search)
            )
        
        if resource_type:
            resources = resources.filter(resource_type=resource_type)
        
        if category:
            resources = resources.filter(category=category)
        
        if difficulty:
            resources = resources.filter(difficulty=difficulty)
        
        if tags:
            # Use __in for OR logic, or chain filters for AND logic
            resources = resources.filter(tags__in=tags).distinct()
        
        resources = resources.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(resources, 20)
    page = request.GET.get('page')
    resources_page = paginator.get_page(page)
    
    # Get categories with annotated counts for sidebar
    categories = ResourceCategory.objects.annotate(
        total_resources=Count('resource', filter=Q(resource__is_approved=True))
    ).order_by('order', 'name')
    
    popular_tags = ResourceTag.objects.annotate(
        resource_count=Count('resource')
    ).order_by('-resource_count')[:15]
    
    context = {
        'resources': resources_page,
        'filter_form': filter_form,
        'categories': categories,  # This now has total_resources
        'popular_tags': popular_tags,
        'title': 'Learning Resources - PrimeTime'
    }
    return render(request, 'resources/resource_list.html', context)


def resource_detail(request, pk):
    """
    Display a single resource with all details, ratings, and similar resources.
    """
    # Get the resource or return 404
    resource = get_object_or_404(Resource, pk=pk)
    
    # Increment view count (only once per session)
    resource.increment_view(request)
    
    # Get all ratings for this resource with user data
    ratings = ResourceRating.objects.filter(resource=resource).select_related('user').order_by('-created_at')
    
    # Check if current user has rated this resource
    user_rating = None
    if request.user.is_authenticated:
        user_rating = ResourceRating.objects.filter(
            resource=resource, 
            user=request.user
        ).first()
    
    # Check if current user has liked this resource
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = resource.user_has_liked(request.user)
    
    # Get similar resources (same category, excluding current resource)
    similar_resources = Resource.objects.filter(
        category=resource.category
    ).exclude(pk=resource.pk).select_related('author', 'category')[:6]
    
    # If not enough similar resources from same category, get from same tags
    if similar_resources.count() < 3 and resource.tags.exists():
        similar_from_tags = Resource.objects.filter(
            tags__in=resource.tags.all()
        ).exclude(pk=resource.pk).distinct().select_related('author', 'category')[:6]
        similar_resources = list(similar_resources) + list(similar_from_tags)
        similar_resources = similar_resources[:6]
    
    # Calculate rating distribution
    rating_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for rating in ratings:
        if rating.rating in rating_distribution:
            rating_distribution[rating.rating] += 1
    
    # Calculate percentages for the rating bars
    total_ratings = ratings.count()
    rating_percentages = {}
    for stars, count in rating_distribution.items():
        if total_ratings > 0:
            rating_percentages[stars] = (count / total_ratings) * 100
        else:
            rating_percentages[stars] = 0
    
    # Check if user can edit/delete this resource
    can_edit = False
    can_delete = False
    if request.user.is_authenticated:
        can_edit = (request.user == resource.author or 
                   request.user.is_superuser or 
                   request.user.is_admin)
        can_delete = can_edit
    
    # Prepare context
    context = {
        'resource': resource,
        'ratings': ratings,
        'user_rating': user_rating,
        'user_has_liked': user_has_liked,
        'similar_resources': similar_resources,
        'rating_distribution': rating_distribution,
        'rating_percentages': rating_percentages,
        'total_ratings': total_ratings,
        'can_edit': can_edit,
        'can_delete': can_delete,
    }
    
    return render(request, 'resources/resource_detail.html', context)
@login_required
def resource_create(request):
    """Create a new resource"""
    
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.author = request.user
            
            # Auto-approve for admins and supervisors
            if request.user.role in ['admin', 'supervisor']:
                resource.is_approved = True
            else:
                resource.is_approved = False  # Students need approval
            
            resource.save()
            form.save_m2m()  # Save tags
            
            messages.success(request, 'Resource created successfully!')
            return redirect('resources:resource_detail', pk=resource.pk)
    else:
        form = ResourceForm()
    
    context = {
        'form': form,
        'title': 'Share a Resource'
    }
    return render(request, 'resources/resource_form.html', context)


@login_required
def resource_update(request, pk):
    """Update a resource"""
    
    resource = get_object_or_404(Resource, pk=pk)
    
    # Check permissions
    if request.user != resource.author and request.user.role != 'admin':
        messages.error(request, "You don't have permission to edit this resource")
        return redirect('resources:resource_detail', pk=pk)
    
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resource updated successfully!')
            return redirect('resources:resource_detail', pk=pk)
    else:
        form = ResourceForm(instance=resource)
    
    context = {
        'form': form,
        'resource': resource,
        'title': f'Edit: {resource.title}'
    }
    return render(request, 'resources/resource_form.html', context)


@login_required
def resource_delete(request, pk):
    """Delete a resource"""
    
    resource = get_object_or_404(Resource, pk=pk)
    
    # Check permissions
    if request.user != resource.author and request.user.role != 'admin':
        messages.error(request, "You don't have permission to delete this resource")
        return redirect('resources:resource_detail', pk=pk)
    
    if request.method == 'POST':
        resource_title = resource.title
        resource.delete()
        messages.success(request, f'Resource "{resource_title}" deleted successfully')
        return redirect('resources:resource_list')
    
    return render(request, 'resources/resource_confirm_delete.html', {'resource': resource})


@login_required
def resource_rate(request, pk):
    """Rate a resource"""
    
    resource = get_object_or_404(Resource, pk=pk)
    
    if request.method == 'POST':
        form = ResourceRatingForm(request.POST)
        if form.is_valid():
            rating, created = ResourceRating.objects.update_or_create(
                user=request.user,
                resource=resource,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'review': form.cleaned_data['review']
                }
            )
            
            # Update resource average rating
            avg_rating = resource.ratings.aggregate(Avg('rating'))['rating__avg'] or 0
            resource.average_rating = avg_rating
            resource.rating_count = resource.ratings.count()
            resource.save()
            
            action = 'updated' if not created else 'submitted'
            messages.success(request, f'Rating {action} successfully!')
            return redirect('resources:resource_detail', pk=pk)
    
    return redirect('resources:resource_detail', pk=pk)


@login_required
def resource_like(request, pk):
    """
    Toggle like/unlike for a resource.
    POST request toggles the like status.
    """
    resource = get_object_or_404(Resource, pk=pk)
    
    if request.method == 'POST':
        # Check if user already liked this resource
        existing_like = ResourceLike.objects.filter(
            resource=resource, 
            user=request.user
        ).first()
        
        if existing_like:
            # Unlike: remove the like
            existing_like.delete()
            messages.success(request, 'Removed like from resource.')
        else:
            # Like: create new like
            ResourceLike.objects.create(
                resource=resource,
                user=request.user
            )
            messages.success(request, 'Liked the resource!')
    
    # Redirect back to the resource detail page
    return redirect('resources:resource_detail', pk=resource.pk)
@login_required
def resource_download(request, pk):
    """Download a resource file"""
    
    resource = get_object_or_404(Resource, pk=pk)
    
    if not resource.file:
        messages.error(request, 'This resource has no downloadable file')
        return redirect('resources:resource_detail', pk=pk)
    
    # Increment download count
    resource.increment_downloads()
    
    # Return file
    response = FileResponse(resource.file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{resource.file.name}"'
    return response


@login_required
def my_resources(request):
    """View user's uploaded resources"""
    
    resources = Resource.objects.filter(author=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(resources, 15)
    page = request.GET.get('page')
    resources_page = paginator.get_page(page)
    
    context = {
        'resources': resources_page,
        'title': 'My Resources'
    }
    return render(request, 'resources/my_resources.html', context)


@login_required
def recommended_resources(request):
    """View AI-recommended resources for the user"""
    
    if request.user.role != 'student':
        messages.info(request, 'Recommendations are currently only available for students')
        return redirect('resources:resource_list')
    
    # Generate recommendations
    engine = ResourceRecommendationEngine(request.user)
    recommendations = engine.generate_recommendations(limit=20)
    
    # Get recommendation objects with reasons
    recommendation_data = []
    for resource in recommendations:
        try:
            rec = ResourceRecommendation.objects.get(user=request.user, resource=resource)
            recommendation_data.append({
                'resource': resource,
                'reason': rec.reason,
                'score': rec.score
            })
        except ResourceRecommendation.DoesNotExist:
            recommendation_data.append({
                'resource': resource,
                'reason': 'Recommended for you',
                'score': 0.5
            })
    
    context = {
        'recommendations': recommendation_data,
        'title': 'Recommended Resources'
    }
    return render(request, 'resources/recommended_resources.html', context)


@login_required
def resource_categories(request):
    """View resources by category"""
    
    # Use a different name for the annotated count to avoid property conflict
    categories = ResourceCategory.objects.annotate(
        total_resources=Count('resource', filter=Q(resource__is_approved=True))
    ).order_by('order', 'name')
    
    context = {
        'categories': categories,
        'title': 'Resource Categories'
    }
    return render(request, 'resources/categories.html', context)

@login_required
def category_resources(request, category_id):
    """View resources in a specific category"""
    
    category = get_object_or_404(ResourceCategory, pk=category_id)
    resources = Resource.objects.filter(
        category=category,
        is_approved=True
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(resources, 20)
    page = request.GET.get('page')
    resources_page = paginator.get_page(page)
    
    context = {
        'category': category,
        'resources': resources_page,
        'title': f'{category.name} Resources'
    }
    return render(request, 'resources/category_resources.html', context)


# AJAX endpoints

@login_required
def mark_recommendation_clicked(request, pk):
    """Mark a recommendation as clicked"""
    
    if request.method == 'POST':
        try:
            rec = ResourceRecommendation.objects.get(
                user=request.user,
                resource_id=pk
            )
            rec.mark_clicked()
            return JsonResponse({'success': True})
        except ResourceRecommendation.DoesNotExist:
            return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# Admin views

@login_required
def bulk_resource_upload(request):
    """Bulk upload resources from CSV (admin only)"""
    
    if request.user.role != 'admin':
        messages.error(request, 'Admin access required')
        return redirect('resources:resource_list')
    
    if request.method == 'POST':
        form = BulkResourceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Process CSV
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            created_count = 0
            errors = []
            
            for row in reader:
                try:
                    resource = Resource.objects.create(
                        title=row['title'],
                        description=row['description'],
                        resource_type=row.get('resource_type', 'link'),
                        url=row.get('url', ''),
                        difficulty=row.get('difficulty', 'beginner'),
                        programming_languages=row.get('programming_languages', ''),
                        author=request.user,
                        is_approved=True
                    )
                    created_count += 1
                except Exception as e:
                    errors.append(f"Row error: {str(e)}")
            
            messages.success(request, f'{created_count} resources created successfully')
            if errors:
                for error in errors[:5]:  # Show first 5 errors
                    messages.warning(request, error)
            
            return redirect('resources:resource_list')
    else:
        form = BulkResourceUploadForm()
    
    context = {
        'form': form,
        'title': 'Bulk Upload Resources'
    }
    return render(request, 'resources/bulk_upload.html', context)


@login_required
def pending_resources(request):
    """View pending resources for approval (admin only)"""
    
    if request.user.role != 'admin':
        messages.error(request, 'Admin access required')
        return redirect('resources:resource_list')
    
    resources = Resource.objects.filter(is_approved=False).order_by('-created_at')
    
    context = {
        'resources': resources,
        'title': 'Pending Resources'
    }
    return render(request, 'resources/pending_resources.html', context)


@login_required
def approve_resource(request, pk):
    """Approve a pending resource (admin only)"""
    
    if request.user.role != 'admin':
        messages.error(request, 'Admin access required')
        return redirect('resources:resource_detail', pk=pk)
    
    resource = get_object_or_404(Resource, pk=pk)
    resource.is_approved = True
    resource.save()
    
    messages.success(request, f'Resource "{resource.title}" approved')
    return redirect('resources:resource_detail', pk=pk)