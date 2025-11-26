# File: Desktop/Prime/resources/recommender.py

from django.db.models import Q, Count, Avg, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import numpy as np
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
import joblib
import os

from .models import Resource, ResourceRecommendation, ResourceViewHistory, ResourceRating
from projects.models import Project
from accounts.models import User

logger = logging.getLogger(__name__)


class ResourceRecommendationEngine:
    """Advanced ML-based resource recommendation system"""
    
    def __init__(self, user):
        self.user = user
        self.project = self._get_user_project()
        self.model_path = 'resources/ml_models/'
        os.makedirs(self.model_path, exist_ok=True)
    
    def _get_user_project(self):
        """Get user's current project with error handling"""
        try:
            return Project.objects.get(
                student=self.user,
                batch_year=timezone.now().year
            )
        except Project.DoesNotExist:
            logger.info(f"No project found for user {self.user.username}")
            return None
        except Project.MultipleObjectsReturned:
            logger.warning(f"Multiple projects found for user {self.user.username}")
            return Project.objects.filter(
                student=self.user,
                batch_year=timezone.now().year
            ).first()
    
    def generate_recommendations(self, limit=10, use_caching=True):
        """Generate personalized resource recommendations with caching"""
        
        # Check for cached recommendations
        if use_caching:
            cached_recommendations = self._get_cached_recommendations(limit)
            if cached_recommendations:
                return cached_recommendations
        
        recommendations = []
        
        try:
            # 1. Content-based filtering (highest priority)
            tech_based = self._get_technology_based_resources()
            recommendations.extend(tech_based[:6])
            
            # 2. Collaborative filtering
            collaborative = self._get_collaborative_resources()
            recommendations.extend(collaborative[:4])
            
            # 3. Trending and popular resources
            trending = self._get_trending_resources()
            recommendations.extend(trending[:3])
            
            # 4. User's viewing history based
            history_based = self._get_history_based_resources()
            recommendations.extend(history_based[:3])
            
            # 5. Fill with high-quality resources if needed
            if len(recommendations) < limit:
                quality_based = self._get_quality_based_resources()
                recommendations.extend(quality_based[:limit - len(recommendations)])
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            # Fallback to popular resources
            return self._get_fallback_recommendations(limit)
        
        # Score and rank recommendations
        scored_recommendations = self._score_recommendations(recommendations)
        
        # Remove duplicates and sort by score
        unique_recommendations = self._deduplicate_and_sort(scored_recommendations, limit)
        
        # Store recommendations
        self._save_recommendations(unique_recommendations)
        
        return unique_recommendations
    
    def _get_technology_based_resources(self):
        """Get resources matching project technologies using TF-IDF"""
        if not self.project or not self.project.languages_list:
            return Resource.objects.none()
        
        languages = self.project.languages_list
        
        # Create a TF-IDF vectorizer for better matching
        all_resources = Resource.objects.filter(is_approved=True)
        
        if not all_resources.exists():
            return Resource.objects.none()
        
        # Extract text features (title + description + programming_languages)
        resource_texts = [
            f"{res.title} {res.description} {res.programming_languages}" 
            for res in all_resources
        ]
        
        # Create project text for comparison
        project_text = " ".join(languages)
        
        # Calculate TF-IDF similarity
        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        try:
            tfidf_matrix = vectorizer.fit_transform(resource_texts + [project_text])
            project_vector = tfidf_matrix[-1]
            resource_vectors = tfidf_matrix[:-1]
            
            # Calculate cosine similarities
            similarities = cosine_similarity(project_vector, resource_vectors).flatten()
            
            # Get top matching resources
            top_indices = similarities.argsort()[-20:][::-1]  # Top 20
            resource_ids = [all_resources[i].id for i in top_indices if similarities[i] > 0.1]
            
            return Resource.objects.filter(id__in=resource_ids).order_by('-relevance_score', '-average_rating')
            
        except Exception as e:
            logger.warning(f"TF-IDF failed, using keyword matching: {e}")
            # Fallback to keyword matching
            return self._keyword_based_matching(languages)
    
    def _keyword_based_matching(self, languages):
        """Fallback keyword-based matching"""
        query = Q()
        for lang in languages[:3]:  # Limit to top 3 languages
            query |= Q(programming_languages__icontains=lang)
            query |= Q(tags__name__icontains=lang)
            query |= Q(title__icontains=lang)
        
        return Resource.objects.filter(query).distinct().order_by(
            '-relevance_score', 
            '-average_rating',
            '-views'
        )[:20]
    
    def _get_collaborative_resources(self):
        """Get resources using collaborative filtering"""
        if not self.project:
            return Resource.objects.none()
        
        # Find similar users based on project technologies and resource interactions
        similar_users = self._find_similar_users()
        
        if not similar_users:
            return Resource.objects.none()
        
        # Get resources liked by similar users that current user hasn't seen
        viewed_resources = ResourceViewHistory.objects.filter(
            user=self.user
        ).values_list('resource_id', flat=True)
        
        return Resource.objects.filter(
            likes__in=similar_users,
            is_approved=True
        ).exclude(
            id__in=viewed_resources
        ).annotate(
            similar_user_likes=Count('likes')
        ).order_by('-similar_user_likes', '-average_rating')[:15]
    
    def _find_similar_users(self, max_users=10):
        """Find users with similar interests"""
        # Users with similar project technologies
        tech_similar = User.objects.filter(
            projects__programming_languages__icontains=self.project.languages_list[0] if self.project.languages_list else '',
            projects__status__in=['approved', 'in_progress', 'completed']
        ).exclude(id=self.user.id).distinct()[:max_users]
        
        return tech_similar
    
    def _get_trending_resources(self):
        """Get trending resources from last 7 days"""
        last_week = timezone.now() - timedelta(days=7)
        
        return Resource.objects.filter(
            created_at__gte=last_week,
            is_approved=True
        ).annotate(
            engagement_score=Coalesce(F('views'), Value(0)) + Coalesce(F('likes__count'), Value(0)) * 2
        ).order_by('-engagement_score', '-created_at')[:10]
    
    def _get_history_based_resources(self):
        """Get resources based on user's viewing history"""
        viewed_resources = ResourceViewHistory.objects.filter(
            user=self.user
        ).select_related('resource').order_by('-viewed_at')[:5]
        
        if not viewed_resources:
            return Resource.objects.none()
        
        # Find similar resources to those viewed
        similar_resources = []
        for view in viewed_resources:
            similar = Resource.objects.filter(
                category=view.resource.category,
                is_approved=True
            ).exclude(
                id=view.resource.id
            ).exclude(
                resourceviewhistory__user=self.user  # Exclude already viewed
            )[:3]
            similar_resources.extend(similar)
        
        return similar_resources
    
    def _get_quality_based_resources(self):
        """Get high-quality resources based on ratings and engagement"""
        return Resource.objects.filter(
            is_approved=True,
            average_rating__gte=4.0,
            rating_count__gte=3
        ).order_by('-average_rating', '-views')[:10]
    
    def _get_fallback_recommendations(self, limit):
        """Fallback to popular and highly-rated resources"""
        return Resource.objects.filter(
            is_approved=True
        ).order_by(
            '-average_rating', 
            '-views', 
            '-created_at'
        )[:limit]
    
    def _score_recommendations(self, recommendations):
        """Score recommendations based on multiple factors"""
        scored = []
        
        for resource in recommendations:
            score = 0.0
            
            # Base score from resource quality
            score += resource.average_rating * 0.2
            score += min(resource.views / 1000, 1.0) * 0.1  # Normalize views
            
            # Technology relevance bonus
            if self.project and self._has_technology_overlap(resource):
                score += 0.3
            
            # Engagement bonus
            score += min(resource.like_count / 50, 0.2)  # Normalize likes
            
            # Recency bonus
            days_old = (timezone.now() - resource.created_at).days
            if days_old < 30:
                score += 0.2 * (1 - days_old / 30)
            
            scored.append((resource, score))
        
        return scored
    
    def _has_technology_overlap(self, resource):
        """Check if resource overlaps with project technologies"""
        if not self.project or not resource.programming_languages:
            return False
        
        resource_langs = [lang.strip().lower() for lang in resource.programming_languages.split(',')]
        project_langs = [lang.strip().lower() for lang in self.project.languages_list]
        
        return any(lang in resource_langs for lang in project_langs)
    
    def _deduplicate_and_sort(self, scored_recommendations, limit):
        """Remove duplicates and sort by score"""
        seen_ids = set()
        unique_recommendations = []
        
        for resource, score in sorted(scored_recommendations, key=lambda x: x[1], reverse=True):
            if resource.id not in seen_ids and len(unique_recommendations) < limit:
                seen_ids.add(resource.id)
                unique_recommendations.append(resource)
        
        return unique_recommendations
    
    def _save_recommendations(self, recommendations):
        """Save recommendations to database with proper scoring"""
        # Clear old recommendations for this user
        ResourceRecommendation.objects.filter(user=self.user).delete()
        
        for i, resource in enumerate(recommendations):
            score = max(0.1, 1.0 - (i * 0.08))  # Decreasing but not too steep
            
            ResourceRecommendation.objects.create(
                user=self.user,
                resource=resource,
                score=score,
                reason=self._get_recommendation_reason(resource),
                algorithm_version='v2.0'
            )
    
    def _get_recommendation_reason(self, resource):
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if self.project and self._has_technology_overlap(resource):
            overlapping_langs = []
            resource_langs = [lang.strip().lower() for lang in resource.programming_languages.split(',')]
            project_langs = [lang.strip().lower() for lang in self.project.languages_list]
            
            for lang in project_langs:
                if lang in resource_langs:
                    overlapping_langs.append(lang)
            
            if overlapping_langs:
                reasons.append(f"Matches your project technologies: {', '.join(overlapping_langs[:2])}")
        
        if resource.average_rating >= 4.5:
            reasons.append("Highly rated by other students")
        elif resource.average_rating >= 4.0:
            reasons.append("Well-rated resource")
        
        if resource.views > 500:
            reasons.append("Popular among students")
        
        if resource.is_featured:
            reasons.append("Featured resource")
        
        return " • ".join(reasons[:2]) if reasons else "Recommended based on your activity"
    
    def _get_cached_recommendations(self, limit):
        """Get cached recommendations if they're recent enough"""
        cache_duration = timedelta(hours=1)  # Cache for 1 hour
        cutoff_time = timezone.now() - cache_duration
        
        recent_recommendations = ResourceRecommendation.objects.filter(
            user=self.user,
            created_at__gte=cutoff_time
        ).select_related('resource').order_by('-score')[:limit]
        
        if recent_recommendations.count() >= limit:
            return [rec.resource for rec in recent_recommendations]
        
        return None


class BatchRecommendationEngine:
    """Generate recommendations for multiple users efficiently"""
    
    @classmethod
    def generate_batch_recommendations(cls, users, limit=5):
        """Generate recommendations for multiple users"""
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        results = {}
        lock = threading.Lock()
        
        def process_user(user):
            try:
                engine = ResourceRecommendationEngine(user)
                recommendations = engine.generate_recommendations(limit=limit, use_caching=True)
                with lock:
                    results[user.id] = recommendations
            except Exception as e:
                logger.error(f"Error generating recommendations for user {user.id}: {e}")
                with lock:
                    results[user.id] = []
        
        # Process users in parallel (limited to 5 threads to avoid overwhelming the DB)
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_user, users)
        
        return results