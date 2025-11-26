# Generated migration for supervisor feedback and log sheets

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SupervisorFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('context', models.CharField(help_text='Brief context of the feedback session', max_length=200)),
                ('remarks', models.TextField(help_text='Detailed feedback and remarks')),
                ('sentiment_score', models.FloatField(blank=True, default=0.0, help_text='Calculated sentiment of remarks', null=True)),
                ('rating', models.IntegerField(blank=True, choices=[(1, '1 - Needs Significant Improvement'), (2, '2 - Below Expectations'), (3, '3 - Meets Expectations'), (4, '4 - Above Expectations'), (5, '5 - Excellent')], help_text='Overall performance rating', null=True)),
                ('action_required', models.BooleanField(default=False, help_text='Does this feedback require immediate action?')),
                ('follow_up_required', models.BooleanField(default=False, help_text='Does this require a follow-up?')),
                ('follow_up_date', models.DateField(blank=True, help_text='When to follow up', null=True)),
                ('is_visible_to_student', models.BooleanField(default=True, help_text='Should student see this feedback?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supervisor_feedback', to='projects.project')),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='received_feedback', to=settings.AUTH_USER_MODEL)),
                ('supervisor', models.ForeignKey(limit_choices_to={'role': 'supervisor'}, on_delete=django.db.models.deletion.CASCADE, related_name='given_feedback', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Supervisor Feedback',
                'verbose_name_plural': 'Supervisor Feedback',
                'ordering': ['-date', '-created_at'],
                'indexes': [
                    models.Index(fields=['student', 'date'], name='idx_student_date'),
                    models.Index(fields=['supervisor', 'date'], name='idx_supervisor_date'),
                    models.Index(fields=['project'], name='idx_project'),
                ],
            },
        ),
        migrations.AddField(
            model_name='supervisormeetinglog',
            name='feedback_provided',
            field=models.TextField(blank=True, help_text='Feedback provided during this meeting'),
        ),
        migrations.AddField(
            model_name='supervisormeetinglog',
            name='affects_progress',
            field=models.BooleanField(default=True, help_text='Does this meeting affect progress calculation?'),
        ),
        migrations.AddField(
            model_name='supervisormeetinglog',
            name='affects_stress',
            field=models.BooleanField(default=True, help_text='Does this meeting affect stress calculation?'),
        ),
    ]
