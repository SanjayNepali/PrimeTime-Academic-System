# File: groups/utils.py

from django.utils import timezone

def get_current_batch_year():
    """
    Get current batch year based on Nepali calendar logic
    Adjust this based on your institution's batch year calculation
    """
    current_year = timezone.now().year
    # Convert to Nepali year (approximately +57 years)
    nepali_year = current_year + 57
    
    # If you want to adjust based on month (e.g., batch starts in August)
    current_month = timezone.now().month
    if current_month < 8:  # Before August, previous batch year
        nepali_year -= 1
    
    return nepali_year


def get_batch_year_choices():
    """Get batch year choices for dropdowns (current +/- 5 years)"""
    current = get_current_batch_year()
    return [(year, f"Batch {year}") for year in range(current - 5, current + 2)]