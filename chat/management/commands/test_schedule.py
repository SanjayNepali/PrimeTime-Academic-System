from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User


class Command(BaseCommand):
    help = "Test supervisor schedule availability"

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 60)
        self.stdout.write("🔍 TESTING SUPERVISOR SCHEDULE")
        self.stdout.write("=" * 60)

        supervisor = User.objects.filter(role='supervisor').first()

        if not supervisor:
            self.stdout.write("❌ No supervisor found in database")
            return

        self.stdout.write(f"\n✅ Found supervisor: {supervisor.display_name}")
        self.stdout.write(f"   Username: {supervisor.username}")
        self.stdout.write(f"   Email: {supervisor.email}")

        self.stdout.write(f"\n📅 Schedule Settings:")
        self.stdout.write(f"   Enabled: {supervisor.schedule_enabled}")
        self.stdout.write(f"   Start: {supervisor.schedule_start_time}")
        self.stdout.write(f"   End: {supervisor.schedule_end_time}")
        self.stdout.write(f"   Days: {supervisor.schedule_days}")

        now = timezone.now()
        self.stdout.write(f"\n⏰ Current Time Check:")
        self.stdout.write(f"   Current time: {now.strftime('%I:%M %p')}")
        self.stdout.write(f"   Current day: {now.strftime('%A (%a)')}")

        is_available = supervisor.is_available_now()
        self.stdout.write(
            f"\n{'✅' if is_available else '❌'} IS AVAILABLE NOW: {is_available}"
        )

        if not is_available:
            self.stdout.write(f"   Reason: {supervisor.get_availability_message()}")

        self.stdout.write(f"\n📤 MESSAGE SENDING TEST:")
        if is_available:
            self.stdout.write("   ✅ Messages will be DELIVERED IMMEDIATELY")
        else:
            self.stdout.write("   ⏳ Messages will be QUEUED AS PENDING")

        self.stdout.write(f"\n💡 RECOMMENDATIONS:")
        if not supervisor.schedule_enabled:
            self.stdout.write("   ⚠️ Schedule is NOT enabled")
        elif not supervisor.schedule_start_time:
            self.stdout.write("   ⚠️ Start time is NOT set")
        elif not supervisor.schedule_days:
            self.stdout.write("   ⚠️ Days are NOT set")
        else:
            self.stdout.write("   ✅ Schedule is fully configured")

        self.stdout.write("\n" + "=" * 60)
