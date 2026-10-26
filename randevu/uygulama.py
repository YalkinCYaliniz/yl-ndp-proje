"""Uygulamanın tüm verisini tek yerde tutar ve örnek veri üretir."""
from datetime import datetime, time

from randevu.kullanici import Hasta, Doktor, Yonetici
from randevu.kurum import Kurum, Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.randevu import RandevuSistemi


class Uygulama:
    def __init__(self):
        self.kurum = Kurum("Yaşam Sağlık Grubu")
        self.sistem = RandevuSistemi()
        self.kullanicilar = []

    def kullanici_ekle(self, kullanici) -> None:
        self.kullanicilar.append(kullanici)

    def doktorlar(self) -> list:
        return [k for k in self.kullanicilar if isinstance(k, Doktor)]


def ornek_veri() -> Uygulama:
    uyg = Uygulama()

    admin = Yonetici("Mehmet", "Kaya", "11111111111")
    ali = Hasta("Ali", "Demir", "10987654321")
    veli = Hasta("Veli", "Can", "22222222222")
    ayse = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
    for k in (admin, ali, veli, ayse):
        uyg.kullanici_ekle(k)

    merkez = Hastane("Merkez Hastane", time(8, 0), time(17, 0))
    kadikoy = Hastane("Kadıköy Hastane", time(9, 0), time(18, 0))
    dahiliye = Klinik("Dahiliye")
    kardiyoloji = Klinik("Kardiyoloji")

    admin.hastane_ekle(uyg.kurum, merkez)
    admin.hastane_ekle(uyg.kurum, kadikoy)
    admin.klinik_ekle(merkez, dahiliye)
    admin.klinik_ekle(merkez, kardiyoloji)
    admin.hizmet_ekle(dahiliye, Muayene("Genel Muayene", 30, 500.0))
    admin.hizmet_ekle(kardiyoloji, Radyoloji("EKG", 30, 400.0, cihaz_ucreti=300.0))
    admin.hizmet_ekle(kardiyoloji, Laboratuvar("Kolesterol Tahlili", 15, 100.0, tahlil_sayisi=3))
    admin.doktor_ekle(dahiliye, ayse)
    admin.doktor_ekle(kardiyoloji, ayse)

    # 3 gün boyunca 09:00-12:00 ve 13:00-16:00 çalışıyor
    for gun in (28, 29, 30):
        ayse.musaitlik_ekle(datetime(2026, 10, gun, 9, 0), datetime(2026, 10, gun, 12, 0))
        ayse.musaitlik_ekle(datetime(2026, 10, gun, 13, 0), datetime(2026, 10, gun, 16, 0))
    return uyg
