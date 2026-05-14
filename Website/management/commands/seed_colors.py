from django.core.management.base import BaseCommand
from Website.models import UlosColorThread

class Command(BaseCommand):
    help = 'Seeds initial ulos color thread data into the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to seed ulos color data...'))

        colors_to_seed = [
    ('C001', '0, 0, 0'),
    ('C002', '353, 51, 28'),
    ('C003', '18, 75, 44'),
    ('C004', '18, 77, 57'),
    ('C005', '18, 75, 44'),
    ('C006', '359, 91, 55'),
    ('C007', '351, 90, 73'),
    ('C008', '335, 94, 69'),
    ('C009', '348, 74, 73'),
    ('C010', '1, 88, 80'),
    ('C011', '0, 63, 77'),
    ('C012', '360, 47, 69'),
    ('C013', '331, 97, 92'),
    ('C014', '0, 77, 86'),
    ('C015', '10, 80, 97'),
    ('C016', '34, 84, 89'),
    ('C017', '45, 100, 69'),
    ('C018', '51, 100, 85'),
    ('C019', '56, 100, 100'),
    ('C020', '50, 26, 100'),
    ('C021', '30, 20, 100'),
    ('C022', '132, 100, 31'),
    ('C023', '168, 60, 45'),
    ('C024', '113, 48, 53'),
    ('C025', '140, 100, 60'),
    ('C026', '138, 100, 93'),
    ('C027', '69, 73, 79'),
    ('C028', '268, 57, 61'),
    ('C029', '226, 30, 32'),
    ('C030', '248, 68, 54'),
    ('C031', '225, 61, 70'),
    ('C032', '205, 60, 100'),
    ('C033', '200, 35, 100'),
    ('C034', '0, 0, 88'),
    ('C035', '0, 0, 100'),
        ]

        for code, hsv_value in colors_to_seed:
            ulos_color, created = UlosColorThread.objects.update_or_create(
                CODE=code,
                defaults={'hsv': hsv_value}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created: {code} - {hsv_value}'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated: {code} - {hsv_value}'))

        self.stdout.write(self.style.SUCCESS('Ulos color data seeding completed successfully!'))