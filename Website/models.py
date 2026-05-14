from django.db import models
from django.contrib.auth.models import User
import colorsys

class Motif(models.Model):
    user = models.CharField(max_length=100, blank=True, null=True)
    raw_url = models.CharField(max_length=255, blank=True, null=True)
    edit_url = models.CharField(max_length=255, blank=True, null=True)
    Urutan = models.CharField(max_length=255, blank=True, null=True)  # Sesuaikan dengan database
    jenis = models.CharField(max_length=50, blank=True, null=True)
    jmlBaris = models.CharField(max_length=20, blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Motif by {self.user} - {self.time}"



class MotifForm(models.Model):
    imgBefore = models.TextField()
    imgAfter  = models.TextField()
    urutanLidi = models.TextField()

class MotifForm1(models.Model):
    imgBefore = models.TextField(blank=True, null=True)
    imgAfter = models.TextField(blank=True, null=True)
    urutanLidi = models.TextField(blank=True, null=True)
    jenisGenerate = models.TextField(blank=True, null=True)
    jmlBaris = models.TextField(blank=True, null=True)
    user = models.TextField(blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)
    slice = models.TextField(blank=True, null=True)
    coloredImage = models.TextField(blank=True, null=True)
    coloredImagecombined = models.TextField(blank=True, null=True)
    sliceColoredImage = models.TextField(blank=True, null=True)
    urutanLidiAsal = models.TextField(blank=True, null=True)
    jenisKain = models.TextField(blank=True, null=True)  # Tambahkan field ini
    jenisProduk = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'website_motifform1'
    def __str__(self):
        return f"Motif by {self.user} - {self.time}" 

class Post(models.Model):
    title= models.TextField()
    content= models.TextField()

class UlosColorThread(models.Model):
    CODE = models.CharField(max_length=10, primary_key=True)
    hsv = models.CharField(max_length=50)
    
    def get_hex_color(self):
        try:
            h_str, s_str, v_str = self.hsv.split(',')
            h = float(h_str)
            s = float(s_str) / 100.0
            v = float(v_str) / 100.0
                         
            r, g, b = colorsys.hsv_to_rgb(h / 360.0, s, v)
        
            r_int = int(r * 255)
            g_int = int(g * 255)
            b_int = int(b * 255)
                         
            return '#%02x%02x%02x' % (r_int, g_int, b_int)
        except (ValueError, IndexError):
            return '#FFFFFF'
      
    def __str__(self):
        return self.CODE
     
    class Meta:
        verbose_name = "Ulos Color Thread"
        verbose_name_plural = "Ulos Color Threads"
        db_table = 'ulos_color_thread'

class UlosCharacteristic(models.Model):
    NAME = models.CharField(max_length=50, primary_key=True)
    garis = models.TextField()
    pola = models.TextField()
    warna_dominasi = models.TextField()
    warna_aksen = models.TextField()
    kontras_warna = models.TextField()
     
    def __str__(self):
        return self.NAME
     
    class Meta:
        verbose_name = "Ulos Characteristic"
        verbose_name_plural = "Ulos Characteristics"
        db_table = 'ulos_characteristic'
