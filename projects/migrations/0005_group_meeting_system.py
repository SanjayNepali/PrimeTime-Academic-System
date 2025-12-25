# File: projects/migrations/0005_group_meeting_system.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_add_group_meeting_support'),
        ('groups', '0001_initial'),
        ('events', '0004_event_late_submission_penalty_event_max_file_size_mb_and_more'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        # ========== RENAME SupervisorMeeting to GroupMeeting ==========
        migrations.RenameModel(
            old_name='SupervisorMeeting',
            new_name='GroupMeeting',
        ),
        
        # ========== CREATE MeetingAttendance MODEL ==========
        migrations.CreateModel(
            name='MeetingAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attended', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('log_sheet_submitted', models.BooleanField(default=False)),
                ('meeting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='projects.groupmeeting')),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='meeting_attendances', to='accounts.user')),
            ],
            options={
                'unique_together': {('meeting', 'student')},
                'ordering': ['student__full_name'],
            },
        ),
        
        # ========== UPDATE ProjectLogSheet ==========
        # Already has group_meeting field from previous migration
        
        # ========== UPDATE ProjectActivity CHOICES ==========
        migrations.AlterField(
            model_name='projectactivity',
            name='action',
            field=models.CharField(
                choices=[
                    ('created', 'Project Created'),
                    ('submitted', 'Submitted for Review'),
                    ('approved', 'Project Approved'),
                    ('rejected', 'Project Rejected'),
                    ('meeting_scheduled', 'Meeting Scheduled'),
                    ('meeting_completed', 'Meeting Completed'),
                    ('logsheet_submitted', 'Log Sheet Submitted'),
                    ('logsheet_approved', 'Log Sheet Approved'),
                ],
                max_length=30
            ),
        ),
    ]