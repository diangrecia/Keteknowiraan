from django.core.management.base import BaseCommand
from Website.models import UlosCharacteristic

class Command(BaseCommand):
    help = 'Seeds initial ulos characteristic data into the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to seed ulos characteristic data...'))

        characteristics_to_seed = [
            {
                'NAME': 'Harungguan',
                'garis': 'Didominasi dengan garis diagonal yang membentuk struktur utama kain.',
                'pola': 'Pola tradisional termasuk ornamen berbentuk garis lengkung, dan motif berbentuk tumbuhan.',
                'warna_dominasi': 'Terdapat banyak kombinasi warna, warna dasar cenderung lebih gelap dari motif ulos. Perpaduan warna kompleks.',
                'warna_aksen': 'Warna aksen (emas, putih, dan hitam) mempertegas garis atau pola dalam bentuk garis tipis atau motif kecil di sekitar pola utama.',
                'kontras_warna': 'Warna terang sebagai garis motif kontras dengan warna dasar Ulos yang cenderung gelap.',
            },
            {
                'NAME': 'Sadum',
                'garis': 'Garis horizontal digunakan untuk membagi pola dan struktur.',
                'pola': 'Pola simetris dan geometris, termasuk silang atau motif kecil yang tersebar merata.',
                'warna_dominasi': 'Setiap Ulos memiliki satu hingga dua warna utama, warna bingkai cenderung lebih gelap.',
                'warna_aksen': 'Warna aksen yang digunakan adalah emas, putih, atau hitam. Aksen membentuk garis-garis atau elemen detail pada kain.',
                'kontras_warna': 'Setiap Ulos memiliki kontras antara warna terang (kuning, putih) dan gelap (hitam, merah tua) untuk memperjelas pola.',
            },
            {
                'NAME': 'Puca',
                'garis': 'Motif tersusun secara horizontal yang membagi antara pola dan motif.',
                'pola': 'Motif geometris menjadi elemen utama, mengandung motif rumah adat / gorga, garis berulang, dan motif kopi.',
                'warna_dominasi': 'Warna dominan menjadi dasar keseluruhan kain, pada umumnya warna yang digunakan adalah merah, cream, dan biru.',
                'warna_aksen': 'Warna aksen seperti putih, hitam, emas, atau abu-abu digunakan untuk mempertegas motif atau garis. Aksen menonjolkan pola.',
                'kontras_warna': 'Kontras tinggi dicapai melalui kombinasi warna terang (kuning, putih) dan gelap (hitam, merah tua).',
            },
        ]

        for char_data in characteristics_to_seed:
            created = UlosCharacteristic.objects.update_or_create(
                NAME=char_data['NAME'],
                defaults=char_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {char_data['NAME']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Updated: {char_data['NAME']}"))