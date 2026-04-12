"""
Mavjud tg_ foydalanuvchilarning ismini Telegram dan qayta olish imkoni yo'q,
lekin username ni tozalash va first_name bo'sh bo'lsa username dan olish mumkin.
"""
from django.core.management.base import BaseCommand
from base.models import UserProfile


class Command(BaseCommand):
    help = "tg_ username li foydalanuvchilarni ko'rsatadi"

    def handle(self, *args, **options):
        profiles = UserProfile.objects.filter(
            telegram_id__isnull=False
        ).select_related("user")

        self.stdout.write(f"Telegram foydalanuvchilar: {profiles.count()} ta\n")
        for p in profiles:
            u = p.user
            self.stdout.write(
                f"  id={p.telegram_id} | username={u.username} | "
                f"first_name={u.first_name!r} | tg_username={p.telegram_username!r}"
            )
