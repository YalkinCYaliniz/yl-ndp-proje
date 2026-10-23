"""Randevu sınıfları ve MHRS tarzı randevu alma akışı."""
from datetime import timedelta
from enum import Enum

from randevu.hatalar import RandevuHatasi


class RandevuDurumu(Enum):
    BEKLIYOR = "Bekliyor"
    ONAYLANDI = "Onaylandı"
    IPTAL = "İptal"


def tarih_saat_yaz(zaman) -> str:
    """datetime -> '14.10.2026 13:30'"""
    return zaman.strftime("%d.%m.%Y %H:%M")


class Randevu:
    """Tek bir randevu: hasta, hastane, klinik, doktor, hizmet ve tarih-saat."""

    def __init__(self, hasta, hastane, klinik, doktor, hizmet, baslangic):
        self.hasta = hasta
        self.hastane = hastane
        self.klinik = klinik
        self.doktor = doktor
        self.hizmet = hizmet
        self.baslangic = baslangic          # datetime
        self._durum = RandevuDurumu.BEKLIYOR

    @property
    def bitis(self):
        return self.baslangic + timedelta(minutes=self.hizmet.sure_dk)

    @property
    def durum(self) -> RandevuDurumu:
        return self._durum

    @property
    def aktif_mi(self) -> bool:
        """İptal edilmemiş randevu zamanı doldurur."""
        return self._durum != RandevuDurumu.IPTAL

    def onayla(self) -> None:
        self._durum = RandevuDurumu.ONAYLANDI

    def iptal(self) -> None:
        self._durum = RandevuDurumu.IPTAL

    def cakisiyor_mu(self, baslangic, bitis) -> bool:
        """Verilen zaman aralığıyla kesişiyor mu?"""
        return self.aktif_mi and self.baslangic < bitis and baslangic < self.bitis

    def __str__(self) -> str:
        return (f"{tarih_saat_yaz(self.baslangic)} | {self.hastane.ad} | {self.klinik.ad} | "
                f"{self.doktor.tam_ad} | {self.hizmet.ad} | {self.hasta.tam_ad} | "
                f"{self.hizmet.ucret} TL | {self.durum.value}")


class Slot:
    """Tablodaki tek bir saat kutusu. Boşsa yeşil, doluysa kırmızı gösterilecek."""

    def __init__(self, baslangic, dolu: bool):
        self.baslangic = baslangic
        self.dolu = dolu

    @property
    def renk(self) -> str:
        return "kırmızı" if self.dolu else "yeşil"

    def __str__(self) -> str:
        durum = "DOLU" if self.dolu else "BOŞ"
        return f"{tarih_saat_yaz(self.baslangic)} -> {durum} ({self.renk})"


class RandevuSistemi:
    """Randevuları oluşturur; müsaitlik ve çakışma kurallarını kontrol eder."""

    def __init__(self):
        self._randevular = []

    @property
    def randevular(self) -> tuple:
        return tuple(self._randevular)

    def _dolu_mu(self, doktor, baslangic, bitis) -> bool:
        for r in self._randevular:
            if r.doktor is doktor and r.cakisiyor_mu(baslangic, bitis):
                return True
        return False

    def saat_tablosu(self, hastane, doktor, hizmet, gun) -> list:
        """Doktorun o günkü tüm saatleri (boş/dolu). Frontend bunu tablo yapacak."""
        slotlar = []
        sure = timedelta(minutes=hizmet.sure_dk)
        for baslangic, bitis in doktor.musaitlik_listesi(gun):
            zaman = baslangic
            while zaman + sure <= bitis:
                if hastane.acik_mi(zaman, zaman + sure):
                    slotlar.append(Slot(zaman, self._dolu_mu(doktor, zaman, zaman + sure)))
                zaman += sure
        return slotlar

    def randevu_olustur(self, hasta, hastane, klinik, doktor, hizmet, baslangic) -> Randevu:
        yeni = Randevu(hasta, hastane, klinik, doktor, hizmet, baslangic)

        if klinik not in hastane.klinikler:
            raise RandevuHatasi("Bu klinik seçilen hastanede yok.")
        if doktor not in klinik.doktorlar:
            raise RandevuHatasi("Doktor bu klinikte çalışmıyor.")
        if hizmet not in klinik.hizmetler:
            raise RandevuHatasi("Bu hizmet seçilen klinikte verilmiyor.")
        if not hastane.acik_mi(yeni.baslangic, yeni.bitis):
            raise RandevuHatasi("Hastane bu saatte kapalı.")
        if not doktor.musait_mi(yeni.baslangic, yeni.bitis):
            raise RandevuHatasi("Doktor bu tarih/saatte müsait değil.")
        if self._dolu_mu(doktor, yeni.baslangic, yeni.bitis):
            raise RandevuHatasi("Randevu çakışması var.")

        self._randevular.append(yeni)
        return yeni
