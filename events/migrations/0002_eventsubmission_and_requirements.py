# Generated migration for event submissions with approval workflow

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add submission requirements to Event model
        migrations.AddField(
            model_name='event',
            name='requires_submission',
            field=models.BooleanField(default=False, help_text='Does this event require file submission?'),
        ),
        migrations.AddField(
            model_name='event',
            name='submission_file_type',
            field=models.CharField(blank=True, help_text='Expected file type (e.g., PDF, DOCX, PPTX)', max_length=50),
        ),
        migrations.AddField(
            model_name='event',
            name='submission_instructions',
            field=models.TextField(blank=True, help_text='Instructions for students on what to submit'),
        ),
        migrations.AddField(
            model_name='event',
            name='late_submission_penalty',
            field=models.FloatField(default=10.0, help_text='Percentage penalty for late submissions'),
        ),
        migrations.AddField(
            model_name='event',
            name='max_file_size_mb',
            field=models.IntegerField(default=10, help_text='Maximum file size in MB'),
        ),

        # Create EventSubmission model
        migrations.CreateModel(
            name='EventSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_file', models.FileField(help_text='Uploaded file (PDF, DOCX, PPT, etc.)', upload_to='event_submissions/%Y/%m/')),
                ('file_type', models.CharField(blank=True, max_length=50)),
                ('submission_notes', models.TextField(blank=True, help_text="Student's notes about submission")),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending Review'),
                    ('supervisor_review', 'Under Supervisor Review'),
                    ('supervisor_approved', 'Supervisor Approved'),
                    ('supervisor_rejected', 'Supervisor Rejected'),
                    ('admin_review', 'Under Admin Review'),
                    ('admin_approved', 'Admin Approved - Final'),
                    ('admin_rejected', 'Admin Rejected - Final'),
                    ('resubmitted', 'Resubmitted'),
                ], default='pending', max_length=30)),
                ('submission_date', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('supervisor_reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('supervisor_remarks', models.TextField(blank=True)),
                ('supervisor_rating', models.IntegerField(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], help_text='1-5 rating', null=True)),
                ('admin_reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('admin_remarks', models.TextField(blank=True)),
                ('admin_rating', models.IntegerField(blank=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], help_text='1-5 rating', null=True)),
                ('grade_impact', models.FloatField(default=0.0, help_text='How this submission affects overall grade')),
                ('late_submission', models.BooleanField(default=False)),
                ('late_penalty', models.FloatField(default=0.0, help_text='Penalty for late submission')),
                ('version', models.IntegerField(default=1)),
                ('event', models.ForeignKey(limit_choices_to={'event_type': 'deadline'}, on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='events.event')),
                ('parent_submission', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resubmissions', to='events.eventsubmission')),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='event_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submission_date'],
                'indexes': [
                    models.Index(fields=['event', 'student'], name='idx_event_student'),
                    models.Index(fields=['status', 'submission_date'], name='idx_status_date'),
                ],
                'unique_together': {('event', 'student', 'version')},
            },
        ),
    ]
