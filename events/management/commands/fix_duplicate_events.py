# File: events/management/commands/fix_duplicate_events.py

from django.core.management.base import BaseCommand
from events.models import Event
from django.utils import timezone
import datetime
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix duplicate events on same day by moving them to next available dates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually making changes'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all active, non-cancelled events ordered by date
        events = Event.objects.filter(
            is_active=True, 
            is_cancelled=False
        ).order_by('start_datetime')
        
        seen_dates = set()
        events_to_fix = []
        
        self.stdout.write("=== Checking for duplicate events ===")
        
        # Find events with same date
        for event in events:
            event_date = event.start_datetime.date()
            
            if event_date in seen_dates:
                events_to_fix.append(event)
                self.stdout.write(
                    self.style.WARNING(f"  DUPLICATE: '{event.title}' on {event_date}")
                )
            else:
                seen_dates.add(event_date)
                self.stdout.write(
                    self.style.SUCCESS(f"  OK: '{event.title}' on {event_date}")
                )
        
        if not events_to_fix:
            self.stdout.write(self.style.SUCCESS("\n✓ No duplicate events found!"))
            return
        
        self.stdout.write(f"\nFound {len(events_to_fix)} duplicate event(s) to fix")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No changes will be made"))
            return
        
        self.stdout.write("\nFixing duplicate events...")
        
        fixed_count = 0
        with transaction.atomic():
            for event in events_to_fix:
                original_date = event.start_datetime.date()
                new_date = self.find_next_available_date(original_date, seen_dates)
                
                if new_date:
                    # Calculate time difference
                    time_delta = event.end_datetime - event.start_datetime
                    
                    # Update start datetime
                    event.start_datetime = event.start_datetime.replace(
                        year=new_date.year,
                        month=new_date.month,
                        day=new_date.day
                    )
                    
                    # Update end datetime (maintain same duration)
                    event.end_datetime = event.start_datetime + time_delta
                    
                    event.save()
                    seen_dates.add(new_date)
                    fixed_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Moved '{event.title}' from {original_date} to {new_date}")
                    )
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ Successfully fixed {fixed_count} duplicate events"))
    
    def find_next_available_date(self, date, seen_dates):
        """Find next date without an event"""
        next_date = date + datetime.timedelta(days=1)
        max_days = 30  # Maximum days to look ahead
        
        for _ in range(max_days):
            # Check if no event on this date AND it's not already in seen_dates
            if not Event.objects.filter(
                is_active=True,
                is_cancelled=False,
                start_datetime__date=next_date
            ).exists() and next_date not in seen_dates:
                return next_date
            next_date += datetime.timedelta(days=1)
        
        # If no date found within range, return None
        return None