# File: analytics/calculators.py

from django.db.models import Avg, Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
import numpy as np


class ProgressCalculator:
    """Calculate project progress metrics"""

    @staticmethod
    def calculate_project_progress(project):
        """
        Calculate comprehensive project progress based on multiple factors:
        - Deliverables completion (50%)
        - Marks obtained (30%)
        - Meeting/logsheet completion (20%)
        """
        if not project:
            return 0

        # 1. Deliverables Progress (50%)
        deliverables = project.deliverables.all()
        total_deliverables = deliverables.count()

        if total_deliverables > 0:
            completed_deliverables = deliverables.filter(is_approved=True).count()
            deliverable_progress = (completed_deliverables / total_deliverables) * 50
        else:
            deliverable_progress = 0

        # 2. Marks Progress (30%)
        total_marks_obtained = deliverables.aggregate(total=Sum('marks'))['total'] or 0
        max_possible_marks = total_deliverables * 100  # Assuming 100 marks per deliverable

        if max_possible_marks > 0:
            marks_progress = (total_marks_obtained / max_possible_marks) * 30
        else:
            marks_progress = 0

        # 3. Meeting/Activity Progress (20%)
        # Check if project has recent activity
        recent_activity = project.activities.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).exists()

        activity_progress = 20 if recent_activity else 0

        # Total progress
        total_progress = deliverable_progress + marks_progress + activity_progress

        return min(100, max(0, total_progress))

    @staticmethod
    def calculate_group_progress(group):
        """Calculate average progress for all students in a group"""
        from projects.models import Project

        members = group.members.filter(is_active=True)
        if not members.exists():
            return 0

        progress_scores = []
        for membership in members:
            try:
                project = Project.objects.get(student=membership.student)
                progress = ProgressCalculator.calculate_project_progress(project)
                progress_scores.append(progress)
            except Project.DoesNotExist:
                pass

        if progress_scores:
            return np.mean(progress_scores)
        return 0


class StressCalculator:
    """Calculate stress levels for students"""

    @staticmethod
    def get_latest_stress_level(user):
        """Get the most recent stress level for a user"""
        from analytics.models import StressLevel

        try:
            return StressLevel.objects.filter(student=user).latest('calculated_at')
        except StressLevel.DoesNotExist:
            return None

    @staticmethod
    def get_stress_trend(user, days=30):
        """Get stress trend over specified days"""
        from analytics.models import StressLevel

        since = timezone.now() - timedelta(days=days)
        stress_records = StressLevel.objects.filter(
            student=user,
            timestamp=since
        ).order_by('timestamp')

        if not stress_records.exists():
            return {'trend': 'stable', 'average': 0, 'records': []}

        levels = list(stress_records.values_list('level', flat=True))
        average = np.mean(levels)

        # Calculate trend (increasing, decreasing, stable)
        if len(levels) >= 3:
            recent_avg = np.mean(levels[-3:])
            earlier_avg = np.mean(levels[:3])

            if recent_avg > earlier_avg + 10:
                trend = 'increasing'
            elif recent_avg < earlier_avg - 10:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'average': average,
            'current': levels[-1] if levels else 0,
            'records': list(stress_records.values('timestamp', 'level'))
        }

    @staticmethod
    def get_high_stress_students(threshold=70):
        """Get list of students with high stress levels"""
        from analytics.models import StressLevel

        # Get latest stress level for each student
        latest_stress = StressLevel.objects.filter(
            level__gte=threshold
        ).order_by('student', '-timestamp').distinct('student')

        return latest_stress


class PerformanceCalculator:
    """Calculate performance metrics"""

    @staticmethod
    def calculate_student_performance(student):
        """Calculate comprehensive student performance score"""
        from projects.models import Project

        try:
            project = Project.objects.get(student=student)
        except Project.DoesNotExist:
            return {'overall_score': 0, 'breakdown': {}}

        # Components of performance
        components = {
            'progress': ProgressCalculator.calculate_project_progress(project),
            'deliverable_quality': PerformanceCalculator._calculate_deliverable_quality(project),
            'consistency': PerformanceCalculator._calculate_consistency(project),
            'timeliness': PerformanceCalculator._calculate_timeliness(project)
        }

        # Weighted average
        weights = {
            'progress': 0.40,
            'deliverable_quality': 0.30,
            'consistency': 0.15,
            'timeliness': 0.15
        }

        overall_score = sum(components[key] * weights[key] for key in components)

        return {
            'overall_score': overall_score,
            'breakdown': components,
            'grade': PerformanceCalculator._get_letter_grade(overall_score)
        }

    @staticmethod
    def _calculate_deliverable_quality(project):
        """Calculate quality based on marks received"""
        deliverables = project.deliverables.filter(is_approved=True)

        if not deliverables.exists():
            return 0

        avg_marks = deliverables.aggregate(avg=Avg('marks'))['avg'] or 0
        return min(100, avg_marks)  # Normalize to 100

    @staticmethod
    def _calculate_consistency(project):
        """Calculate consistency based on regular activity"""
        activities = project.activities.all().order_by('timestamp')

        if activities.count() < 2:
            return 0

        # Check for regular activity (at least weekly)
        total_weeks = max(1, (timezone.now() - project.created_at).days / 7)
        activity_weeks = activities.values('timestamp__week').distinct().count()

        consistency = min(100, (activity_weeks / total_weeks) * 100)
        return consistency

    @staticmethod
    def _calculate_timeliness(project):
        """Calculate timeliness based on deliverable submission dates"""
        deliverables = project.deliverables.all()

        if not deliverables.exists():
            return 0

        # Simple timeliness calculation
        # In a real system, you'd compare submission_date with deadline
        timely_submissions = deliverables.filter(submitted_at__isnull=False).count()
        total_submissions = deliverables.count()

        if total_submissions > 0:
            return (timely_submissions / total_submissions) * 100
        return 0

    @staticmethod
    def _get_letter_grade(score):
        """Convert numeric score to letter grade"""
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        else:
            return 'F'


class AnalyticsDashboard:
    """Generate dashboard analytics"""

    @staticmethod
    def get_supervisor_analytics(supervisor):
        """Get analytics for a supervisor's groups"""
        from groups.models import Group
        from projects.models import Project

        groups = Group.objects.filter(supervisor=supervisor, is_active=True)

        analytics = {
            'total_groups': groups.count(),
            'total_students': 0,
            'average_progress': 0,
            'high_stress_students': [],
            'low_performing_students': [],
            'group_summaries': []
        }

        all_progress = []
        all_students = []

        for group in groups:
            members = group.members.filter(is_active=True)
            group_progress = []

            for membership in members:
                student = membership.student
                all_students.append(student)

                # Get project
                try:
                    project = Project.objects.get(student=student)
                    progress = ProgressCalculator.calculate_project_progress(project)
                    group_progress.append(progress)
                    all_progress.append(progress)

                    # Check stress level
                    stress = StressCalculator.get_latest_stress_level(student)
                    if stress and stress.level >= 70:
                        analytics['high_stress_students'].append({
                            'student': student,
                            'stress_level': stress.level,
                            'group': group.name
                        })

                    # Check performance
                    if progress < 50:
                        analytics['low_performing_students'].append({
                            'student': student,
                            'progress': progress,
                            'group': group.name
                        })

                except Project.DoesNotExist:
                    pass

            analytics['group_summaries'].append({
                'group': group,
                'student_count': members.count(),
                'average_progress': np.mean(group_progress) if group_progress else 0
            })

        analytics['total_students'] = len(all_students)
        analytics['average_progress'] = np.mean(all_progress) if all_progress else 0

        return analytics

    @staticmethod
    def get_admin_analytics():
        """Get system-wide analytics for admin"""
        from accounts.models import User
        from projects.models import Project
        from groups.models import Group

        total_students = User.objects.filter(role='student', is_active=True).count()
        total_projects = Project.objects.count()
        total_groups = Group.objects.filter(is_active=True).count()

        # Project status distribution
        status_distribution = Project.objects.values('status').annotate(count=Count('id'))

        # Average progress
        all_projects = Project.objects.all()
        progress_scores = [ProgressCalculator.calculate_project_progress(p) for p in all_projects]
        avg_progress = np.mean(progress_scores) if progress_scores else 0

        # High stress count
        high_stress = StressCalculator.get_high_stress_students(threshold=70).count()

        return {
            'total_students': total_students,
            'total_projects': total_projects,
            'total_groups': total_groups,
            'average_progress': avg_progress,
            'high_stress_students': high_stress,
            'status_distribution': list(status_distribution),
            'completion_rate': (status_distribution.filter(status='completed').count() / total_projects * 100) if total_projects > 0 else 0
        }

