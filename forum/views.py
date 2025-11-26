# File: Desktop/Prime/forum/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone

from .models import ForumPost, ForumReply, ForumCategory, ForumTag, ForumNotification
from .forms import ForumPostForm, ForumReplyForm, ForumSearchForm, FlagPostForm, ModeratePostForm
from analytics.sentiment import InappropriateContentDetector
from accounts.models import User


@login_required
def forum_home(request):
    """Forum home page with recent posts"""
    
    # Get filter form
    search_form = ForumSearchForm(request.GET)
    
    # Base queryset - exclude hidden posts
    posts = ForumPost.objects.filter(is_hidden=False).select_related(
        'author', 'category'
    ).prefetch_related('tags', 'upvotes')
    
    # Apply filters
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        category = search_form.cleaned_data.get('category')
        post_type = search_form.cleaned_data.get('post_type')
        status = search_form.cleaned_data.get('status')
        tags = search_form.cleaned_data.get('tags')
        sort_by = search_form.cleaned_data.get('sort_by') or '-last_activity'
        
        if search:
            posts = posts.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(programming_languages__icontains=search)
            )
        
        if category:
            posts = posts.filter(category=category)
        
        if post_type:
            posts = posts.filter(post_type=post_type)
        
        if status:
            if status == 'open':
                posts = posts.filter(status='open')
            elif status == 'solved':
                posts = posts.filter(is_solved=True)
            elif status == 'pinned':
                posts = posts.filter(is_pinned=True)
        
        if tags:
            for tag in tags:
                posts = posts.filter(tags=tag)
        
        posts = posts.order_by(sort_by)
    else:
        posts = posts.order_by('-is_pinned', '-last_activity')
    
    # Pagination
    paginator = Paginator(posts, 20)
    page = request.GET.get('page')
    posts_page = paginator.get_page(page)
    
    # Get categories and popular tags
    categories = ForumCategory.objects.filter(is_active=True)
    popular_tags = ForumTag.objects.annotate(
        post_count=Count('forumpost')
    ).order_by('-post_count')[:15]
    
    # Get statistics
    stats = {
        'total_posts': ForumPost.objects.filter(is_hidden=False).count(),
        'total_replies': ForumReply.objects.filter(is_hidden=False).count(),
        'solved_posts': ForumPost.objects.filter(is_solved=True).count(),
        'active_users': User.objects.filter(forum_posts__isnull=False).distinct().count()
    }
    
    context = {
        'posts': posts_page,
        'search_form': search_form,
        'categories': categories,
        'popular_tags': popular_tags,
        'stats': stats,
        'title': 'Community Forum - PrimeTime'
    }
    return render(request, 'forum/forum_home.html', context)


@login_required
def post_detail(request, pk):
    """View a forum post with replies"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    # Check if post is hidden and user is not admin
    if post.is_hidden and request.user.role != 'admin':
        messages.error(request, 'This post is not available')
        return redirect('forum:forum_home')
    
    # Increment views
    post.increment_views()
    
    # Handle reply submission
    if request.method == 'POST' and 'reply_submit' in request.POST:
        reply_form = ForumReplyForm(request.POST)
        if reply_form.is_valid():
            # Check for inappropriate content
            detector = InappropriateContentDetector()
            analysis = detector.analyze_content(reply_form.cleaned_data['content'], content_type='forum')
            
            if analysis['is_inappropriate']:
                messages.error(
                    request,
                    f'Your reply contains inappropriate content: {", ".join(analysis["inappropriate_issues"])}'
                )
            else:
                reply = reply_form.save(commit=False)
                reply.post = post
                reply.author = request.user
                reply.save()
                
                # Flag suspicious content
                if analysis['is_suspicious']:
                    messages.warning(
                        request,
                        'Your reply has been submitted but flagged for review due to suspicious content.'
                    )
                
                # Notify post author
                if post.author != request.user:
                    ForumNotification.objects.create(
                        user=post.author,
                        notification_type='reply',
                        post=post,
                        reply=reply,
                        actor=request.user
                    )
                
                # Notify followers
                for follower in post.followers.exclude(pk__in=[request.user.pk, post.author.pk]):
                    ForumNotification.objects.create(
                        user=follower,
                        notification_type='reply',
                        post=post,
                        reply=reply,
                        actor=request.user
                    )
                
                messages.success(request, 'Reply posted successfully!')
                return redirect('forum:post_detail', pk=pk)
    else:
        reply_form = ForumReplyForm()
    
    # Get replies
    replies = post.replies.filter(is_hidden=False).select_related(
        'author'
    ).prefetch_related('upvotes').order_by('created_at')
    
    # Check if user has upvoted
    user_has_upvoted = post.upvotes.filter(pk=request.user.pk).exists()
    user_is_following = post.followers.filter(pk=request.user.pk).exists()
    
    # Get reply upvote status
    reply_upvotes = {}
    for reply in replies:
        reply_upvotes[reply.id] = reply.upvotes.filter(pk=request.user.pk).exists()
    
    context = {
        'post': post,
        'replies': replies,
        'reply_form': reply_form,
        'user_has_upvoted': user_has_upvoted,
        'user_is_following': user_is_following,
        'reply_upvotes': reply_upvotes,
        'can_moderate': request.user.role == 'admin',
        'can_mark_solved': request.user == post.author or request.user.role == 'admin',
        'title': post.title
    }
    return render(request, 'forum/post_detail.html', context)


@login_required
def post_create(request):
    """Create a new forum post"""
    
    if request.method == 'POST':
        form = ForumPostForm(request.POST)
        if form.is_valid():
            # Check for inappropriate content
            detector = InappropriateContentDetector()
            content_to_check = f"{form.cleaned_data['title']} {form.cleaned_data['content']}"
            analysis = detector.analyze_content(content_to_check, content_type='forum')
            
            if analysis['is_inappropriate']:
                messages.error(
                    request,
                    f'Your post contains inappropriate content: {", ".join(analysis["inappropriate_issues"])}'
                )
            else:
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                form.save_m2m()  # Save tags
                
                # Flag suspicious content
                if analysis['is_suspicious']:
                    post.is_flagged = True
                    post.flag_reason = f"Auto-flagged: {', '.join(analysis['suspicious_issues'])}"
                    post.save()
                    messages.warning(
                        request,
                        'Your post has been submitted but flagged for review due to suspicious content.'
                    )
                
                messages.success(request, 'Post created successfully!')
                return redirect('forum:post_detail', pk=post.pk)
    else:
        form = ForumPostForm()
    
    context = {
        'form': form,
        'title': 'Create New Post'
    }
    return render(request, 'forum/post_form.html', context)


@login_required
def post_update(request, pk):
    """Update a forum post"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    # Check permissions
    if request.user != post.author and request.user.role != 'admin':
        messages.error(request, "You don't have permission to edit this post")
        return redirect('forum:post_detail', pk=pk)
    
    if request.method == 'POST':
        form = ForumPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('forum:post_detail', pk=pk)
    else:
        form = ForumPostForm(instance=post)
    
    context = {
        'form': form,
        'post': post,
        'title': f'Edit: {post.title}'
    }
    return render(request, 'forum/post_form.html', context)


@login_required
def post_delete(request, pk):
    """Delete a forum post"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    # Check permissions
    if request.user != post.author and request.user.role != 'admin':
        messages.error(request, "You don't have permission to delete this post")
        return redirect('forum:post_detail', pk=pk)
    
    if request.method == 'POST':
        post_title = post.title
        post.delete()
        messages.success(request, f'Post "{post_title}" deleted successfully')
        return redirect('forum:forum_home')
    
    return render(request, 'forum/post_confirm_delete.html', {'post': post})


@login_required
def post_upvote(request, pk):
    """Upvote/remove upvote from a post"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    if post.upvotes.filter(pk=request.user.pk).exists():
        post.upvotes.remove(request.user)
        upvoted = False
    else:
        post.upvotes.add(request.user)
        upvoted = True
        
        # Notify post author
        if post.author != request.user:
            ForumNotification.objects.create(
                user=post.author,
                notification_type='upvote',
                post=post,
                actor=request.user
            )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'upvoted': upvoted,
            'upvote_count': post.upvote_count
        })
    
    return redirect('forum:post_detail', pk=pk)


@login_required
def reply_upvote(request, pk):
    """Upvote/remove upvote from a reply"""
    
    reply = get_object_or_404(ForumReply, pk=pk)
    
    if reply.upvotes.filter(pk=request.user.pk).exists():
        reply.upvotes.remove(request.user)
        upvoted = False
    else:
        reply.upvotes.add(request.user)
        upvoted = True
        
        # Notify reply author
        if reply.author != request.user:
            ForumNotification.objects.create(
                user=reply.author,
                notification_type='upvote',
                post=reply.post,
                reply=reply,
                actor=request.user
            )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'upvoted': upvoted,
            'upvote_count': reply.upvote_count
        })
    
    return redirect('forum:post_detail', pk=reply.post.pk)


@login_required
def post_follow(request, pk):
    """Follow/unfollow a post"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    if post.followers.filter(pk=request.user.pk).exists():
        post.followers.remove(request.user)
        following = False
    else:
        post.followers.add(request.user)
        following = True
        
        # Notify post author
        if post.author != request.user:
            ForumNotification.objects.create(
                user=post.author,
                notification_type='follow',
                post=post,
                actor=request.user
            )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'following': following,
            'follower_count': post.follower_count
        })
    
    return redirect('forum:post_detail', pk=pk)


@login_required
def mark_solved(request, pk, reply_id=None):
    """Mark a post as solved"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    # Check permissions
    if request.user != post.author and request.user.role != 'admin':
        messages.error(request, "Only the post author can mark it as solved")
        return redirect('forum:post_detail', pk=pk)
    
    if reply_id:
        reply = get_object_or_404(ForumReply, pk=reply_id, post=post)
        post.mark_solved(reply)
        
        # Notify reply author
        if reply.author != request.user:
            ForumNotification.objects.create(
                user=reply.author,
                notification_type='solution',
                post=post,
                reply=reply,
                actor=request.user
            )
        
        messages.success(request, 'Post marked as solved!')
    else:
        post.is_solved = True
        post.status = 'solved'
        post.save()
        messages.success(request, 'Post marked as solved!')
    
    return redirect('forum:post_detail', pk=pk)


@login_required
def my_posts(request):
    """View user's own posts"""
    
    posts = ForumPost.objects.filter(author=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(posts, 20)
    page = request.GET.get('page')
    posts_page = paginator.get_page(page)
    
    context = {
        'posts': posts_page,
        'title': 'My Posts'
    }
    return render(request, 'forum/my_posts.html', context)


@login_required
def notifications(request):
    """View forum notifications"""
    
    notifications = request.user.forum_notifications.all()[:50]
    
    # Mark as read if requested
    if request.GET.get('mark_all_read'):
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read')
        return redirect('forum:notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
        'title': 'Forum Notifications'
    }
    return render(request, 'forum/notifications.html', context)


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    
    notification = get_object_or_404(ForumNotification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    
    # Redirect to the post
    if notification.post:
        return redirect('forum:post_detail', pk=notification.post.pk)
    
    return redirect('forum:notifications')


# Admin actions

@login_required
def flag_post(request, pk):
    """Flag a post as inappropriate"""
    
    post = get_object_or_404(ForumPost, pk=pk)
    
    if request.method == 'POST':
        form = FlagPostForm(request.POST)
        if form.is_valid():
            post.is_flagged = True
            post.flag_reason = f"{form.cleaned_data['reason']}: {form.cleaned_data.get('details', '')}"
            post.flagged_by.add(request.user)
            post.save()
            
            messages.success(request, 'Post has been flagged for review')
            return redirect('forum:post_detail', pk=pk)
    else:
        form = FlagPostForm()
    
    context = {
        'form': form,
        'post': post,
        'title': 'Flag Post'
    }
    return render(request, 'forum/flag_post.html', context)


@login_required
def flagged_posts(request):
    """View flagged posts (admin only)"""
    
    if request.user.role != 'admin':
        messages.error(request, 'Admin access required')
        return redirect('forum:forum_home')
    
    posts = ForumPost.objects.filter(is_flagged=True).order_by('-created_at')
    
    context = {
        'posts': posts,
        'title': 'Flagged Posts'
    }
    return render(request, 'forum/flagged_posts.html', context)


# AJAX endpoints

@login_required
def get_unread_notifications(request):
    """AJAX endpoint for unread notifications"""
    
    unread_count = request.user.forum_notifications.filter(is_read=False).count()
    notifications = list(
        request.user.forum_notifications.filter(is_read=False)[:5].values(
            'id', 'notification_type', 'created_at'
        )
    )
    
    return JsonResponse({
        'unread_count': unread_count,
        'notifications': notifications
    })