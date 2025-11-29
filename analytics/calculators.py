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
            calculated_at__gte=since
        ).order_by('calculated_at')

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
            'records': list(stress_records.values('calculated_at', 'level'))
        }

    @staticmethod
    def get_high_stress_students(threshold=70):
        """Get list of students with high stress levels - SQLite compatible"""
        from analytics.models import StressLevel
        from accounts.models import User

        # Get all high stress records
        high_stress_records = StressLevel.objects.filter(
            level__gte=threshold
        ).select_related('student').order_by('student_id', '-calculated_at')

        # Group by student and take the latest record for each using Python
        students_seen = set()
        latest_high_stress = []
        
        for record in high_stress_records:
            if record.student_id not in students_seen:
                latest_high_stress.append(record)
                students_seen.add(record.student_id)

        return latest_high_stress


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
        
        # Use date-based grouping for SQLite compatibility
        activity_dates = activities.values_list('timestamp', flat=True)
        unique_weeks = set()
        for date in activity_dates:
            # Get ISO week number
            year, week, _ = date.isocalendar()
            unique_weeks.add(f"{year}-{week}")
        
        activity_weeks = len(unique_weeks)

        consistency = min(100, (activity_weeks / total_weeks) * 100)
        return consistency

    @staticmethod
    def _calculate_timeliness(project):
        """Calculate timeliness based on deliverable submission dates"""
        deliverables = project.deliverables.all()

        if not deliverables.exists():
            return 0

        # Simple timeliness calculation
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
        """Get system-wide analytics for admin WITH REAL CHART DATA"""
        from accounts.models import User
        from projects.models import Project
        from groups.models import Group
        from analytics.models import StressLevel
        from datetime import timedelta

        total_students = User.objects.filter(role='student', is_active=True).count()
        total_projects = Project.objects.count()
        total_groups = Group.objects.filter(is_active=True).count()

        # Project status distribution
        status_distribution = Project.objects.values('status').annotate(count=Count('id'))

        # Average progress
        all_projects = Project.objects.all()
        progress_scores = []
        for project in all_projects:
            progress = ProgressCalculator.calculate_project_progress(project)
            progress_scores.append(progress)
        
        avg_progress = np.mean(progress_scores) if progress_scores else 0

        # High stress count
        high_stress_list = StressCalculator.get_high_stress_students(threshold=70)
        high_stress_count = len(high_stress_list)

        # NEW: REAL CHART DATA
        progress_trend_data = AnalyticsDashboard._get_progress_trend_data()
        stress_distribution_data = AnalyticsDashboard._get_stress_distribution_data()
        department_performance_data = AnalyticsDashboard._get_department_performance_data()

        return {
            'total_students': total_students,
            'total_projects': total_projects,
            'total_groups': total_groups,
            'average_progress': avg_progress,
            'high_stress_students': high_stress_count,
            'status_distribution': list(status_distribution),
            'completion_rate': AnalyticsDashboard._calculate_completion_rate(status_distribution, total_projects),
            # REAL CHART DATA
            'progress_trend_data': progress_trend_data,
            'stress_distribution_data': stress_distribution_data,
            'department_performance_data': department_performance_data,
        }

    @staticmethod
    def _get_progress_trend_data():
        """Get REAL progress trend data for the last 6 weeks"""
        from projects.models import Project
        from datetime import timedelta
        
        weekly_progress = []
        labels = []
        
        # Calculate progress for each of the last 6 weeks
        for week in range(6):
            week_start = timezone.now() - timedelta(weeks=(6 - week))
            week_end = week_start + timedelta(weeks=1)
            
            # Get projects that existed at this point in time
            projects_in_week = Project.objects.filter(
                created_at__lte=week_end
            )
            
            # Calculate average progress for that week
            progress_scores = []
            for project in projects_in_week:
                progress = ProgressCalculator.calculate_project_progress(project)
                progress_scores.append(progress)
            
            avg_progress = np.mean(progress_scores) if progress_scores else 0
            weekly_progress.append(round(avg_progress, 1))
            labels.append(f"W{week+1}")
        
        return {
            'labels': labels,
            'actual_progress': weekly_progress,
            'target_progress': [17, 33, 50, 67, 83, 100]  # Theoretical targets
        }

    @staticmethod
    def _get_stress_distribution_data():
        """Get REAL stress level distribution from database"""
        from analytics.models import StressLevel
        from accounts.models import User
        
        # Get latest stress level for each student
        students = User.objects.filter(role='student', is_active=True)
        stress_levels = []
        
        for student in students:
            latest_stress = StressLevel.objects.filter(
                student=student
            ).order_by('-calculated_at').first()
            
            if latest_stress:
                stress_levels.append(latest_stress.level)
        
        # Categorize based on actual student stress levels
        low_count = len([s for s in stress_levels if s < 30])
        moderate_count = len([s for s in stress_levels if 30 <= s < 60])
        high_count = len([s for s in stress_levels if 60 <= s < 80])
        critical_count = len([s for s in stress_levels if s >= 80])
        
        return {
            'labels': ['Low (0-30)', 'Moderate (30-60)', 'High (60-80)', 'Critical (80-100)'],
            'data': [low_count, moderate_count, high_count, critical_count]
        }

    @staticmethod
    def _get_department_performance_data():
        """Get REAL performance data by department"""
        from accounts.models import User
        from projects.models import Project
        
        departments = User.objects.filter(
            role='student', 
            department__isnull=False
        ).values_list('department', flat=True).distinct()
        
        dept_performance = []
        
        for dept in departments[:5]:  # Limit to top 5 departments
            students = User.objects.filter(role='student', department=dept)
            dept_progress = []
            
            for student in students:
                try:
                    project = Project.objects.get(student=student)
                    progress = ProgressCalculator.calculate_project_progress(project)
                    dept_progress.append(progress)
                except Project.DoesNotExist:
                    continue
            
            avg_performance = np.mean(dept_progress) if dept_progress else 0
            dept_performance.append({
                'department': dept or 'Unknown',
                'performance': round(avg_performance, 1)
            })
        
        # Sort by performance and get top 5
        dept_performance.sort(key=lambda x: x['performance'], reverse=True)
        
        return {
            'labels': [dept['department'] for dept in dept_performance[:5]],
            'data': [dept['performance'] for dept in dept_performance[:5]]
        }

    @staticmethod
    def _calculate_completion_rate(status_distribution, total_projects):
        """Calculate actual completion rate"""
        completed_count = 0
        for status in status_distribution:
            if status['status'] == 'completed':
                completed_count = status['count']
                break
        
        return (completed_count / total_projects * 100) if total_projects > 0 else 0


# NEW: DashboardCalculator class for dashboard-specific analytics
class DashboardCalculator:
    """Calculator for dashboard-specific analytics"""
    
    @staticmethod
    def get_weekly_activity_data():
        """Get REAL weekly activity data for dashboard"""
        from accounts.models import User
        from projects.models import Project
        from datetime import timedelta
        
        # Get last 7 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=6)
        
        days = []
        new_users_data = []
        project_submissions_data = []
        
        # Calculate data for each of the last 7 days
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            day_name = current_date.strftime('%a')  # Mon, Tue, etc.
            days.append(day_name)
            
            # Count new users for this day
            new_users_count = User.objects.filter(
                created_at__date=current_date
            ).count()
            new_users_data.append(new_users_count)
            
            # Count project submissions for this day
            project_submissions_count = Project.objects.filter(
                submitted_at__date=current_date
            ).count()
            project_submissions_data.append(project_submissions_count)
        
        return {
            'labels': days,
            'new_users': new_users_data,
            'project_submissions': project_submissions_data
        }
    
    @staticmethod
    def get_user_distribution_data():
        """Get REAL user distribution data"""
        from accounts.models import User
        
        students_count = User.objects.filter(role='student').count()
        supervisors_count = User.objects.filter(role='supervisor').count()
        admins_count = User.objects.filter(role='admin').count()
        
        return {
            'students': students_count,
            'supervisors': supervisors_count,
            'admins': admins_count
        }
    
    @staticmethod
    def get_system_health_metrics():
        """Get REAL system health metrics"""
        from projects.models import Project
        from accounts.models import User
        from analytics.models import StressLevel
        
        # Calculate average project progress
        projects = Project.objects.all()
        total_progress = 0
        project_count = projects.count()
        
        for project in projects:
            progress = ProgressCalculator.calculate_project_progress(project)
            total_progress += progress
        
        avg_progress = total_progress / project_count if project_count > 0 else 0
        
        # Calculate stress statistics
        stress_levels = StressLevel.objects.all()
        total_stress = 0
        stress_count = stress_levels.count()
        
        for stress in stress_levels:
            total_stress += stress.level
        
        avg_stress = total_stress / stress_count if stress_count > 0 else 0
        
        # Calculate user engagement (users active in last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        active_users = User.objects.filter(
            last_login_at__gte=week_ago
        ).count()
        
        total_users = User.objects.count()
        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        return {
            'average_progress': round(avg_progress, 1),
            'average_stress': round(avg_stress, 1),
            'engagement_rate': round(engagement_rate, 1),
            'active_users': active_users,
            'total_users': total_users
        }