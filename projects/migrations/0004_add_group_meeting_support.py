# File: projects/migrations/0004_add_group_meeting_support.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_alter_projectactivity_action_studentprogressnote_and_more'),
        ('groups', '0001_initial'),
        ('events', '0004_event_late_submission_penalty_event_max_file_size_mb_and_more'),
    ]

    operations = [
        # Change SupervisorMeeting from project-based to group-based
        migrations.RemoveField(
            model_name='supervisormeeting',
            name='project',
        ),
        migrations.RemoveField(
            model_name='supervisormeeting',
            name='student_attended',
        ),
        
        # Add group field
        migrations.AddField(
            model_name='supervisormeeting',
            name='group',
            field=models.ForeignKey(
                help_text='Group this meeting is for',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='supervisor_meetings',
                to='groups.group',
                null=True  # Temporarily allow null for migration
            ),
            preserve_default=False,
        ),
        
        # Add attended_students many-to-many field
        migrations.AddField(
            model_name='supervisormeeting',
            name='attended_students',
            field=models.ManyToManyField(
                blank=True,
                help_text='Students who attended this meeting',
                related_name='attended_meetings',
                to='accounts.user'
            ),
        ),
        
        # Add event link
        migrations.AddField(
            model_name='supervisormeeting',
            name='event',
            field=models.OneToOneField(
                blank=True,
                help_text='Linked calendar event',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='supervisor_meeting',
                to='events.event'
            ),
        ),
        
        # Add group_meeting field to ProjectLogSheet
        migrations.AddField(
            model_name='projectlogsheet',
            name='group_meeting',
            field=models.ForeignKey(
                blank=True,
                help_text='Group meeting this logsheet is for',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='student_logsheets',
                to='projects.supervisormeeting'
            ),
        ),
        
        # Make group field non-nullable after data migration
        migrations.AlterField(
            model_name='supervisormeeting',
            name='group',
            field=models.ForeignKey(
                help_text='Group this meeting is for',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='supervisor_meetings',
                to='groups.group'
            ),
        ),
    ]