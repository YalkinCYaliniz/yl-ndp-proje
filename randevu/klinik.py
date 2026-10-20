"""Klinik, hizmet ve randevu modelleri."""
from enum import Enum


class Hizmet:
    """Kurumun sunduğu bir sağlık hizmeti (ad, süre, ücret)."""

    def __init__(self, ad: str, sure_dk: int, ucret: float):
        self.ad = ad
        self.sure_dk = sure_dk
        self.ucret = ucret


class Klinik:
    """Bir klinik: çalışma saatleri, bölümler, hizmetler ve personel."""

    def __init__(self, ad: str, acilis: int = 8, kapanis: int = 17):
        self.ad = ad
        self.acilis = acilis
        self.kapanis = kapanis
        # Kapsülleme: listeler _ ile başlar, dışarıdan doğrudan değiştirilmez
        self._bolumler = []
        self._hizmetler = []
        self._personel = []

    def bolum_ekle(self, bolum: str) -> None:
        if bolum not in self._bolumler:
            self._bolumler.append(bolum)

    def hizmet_ekle(self, hizmet: Hizmet) -> None:
        self._hizmetler.append(hizmet)

    def personel_ekle(self, personel) -> None:
        self._personel.append(personel)

    @property
    def bolumler(self) -> tuple:
        return tuple(self._bolumler)

    @property
    def hizmetler(self) -> tuple:
        return tuple(self._hizmetler)

    @property
    def personel(self) -> tuple:
        return tuple(self._personel)


class Kurum:
    """Çok şubeli sağlık kuruluşu: birden fazla kliniği (şubeyi) yönetir."""

    def __init__(self, ad: str):
        self.ad = ad
        self._subeler = []          # Kapsülleme: şubeler metotla eklenir

    def sube_ekle(self, klinik: Klinik) -> None:
        self._subeler.append(klinik)

    def sube_bul(self, ad: str) -> Klinik:
        for klinik in self._subeler:
            if klinik.ad == ad:
                return klinik
        raise ValueError(f"'{ad}' adlı şube bulunamadı.")

    @property
    def subeler(self) -> tuple:
        return tuple(self._subeler)


class RandevuDurumu(Enum):
    BEKLIYOR = "Bekliyor"
    ONAYLANDI = "Onaylandı"
    IPTAL = "İptal"


class Randevu:
    """Tek bir randevu: hasta, doktor, hizmet, gün ve saat bilgisi."""

    def __init__(self, hasta, doktor, hizmet: Hizmet, gun: str, baslangic: float):
        self.hasta = hasta
        self.doktor = doktor
        self.hizmet = hizmet
        self.gun = gun
        self.baslangic = baslangic          # saat cinsinden, örn. 9 veya 9.5
        self._durum = RandevuDurumu.BEKLIYOR

    @property
    def bitis(self) -> float:
        return self.baslangic + self.hizmet.sure_dk / 60

    @property
    def durum(self) -> RandevuDurumu:
        return self._durum

    def onayla(self) -> None:
        self._durum = RandevuDurumu.ONAYLANDI

    def iptal(self) -> None:
        self._durum = RandevuDurumu.IPTAL

    def cakisiyor_mu(self, diger: "Randevu") -> bool:
        """Aynı doktor, aynı gün ve saat aralıkları kesişiyorsa True."""
        if self.durum == RandevuDurumu.IPTAL or diger.durum == RandevuDurumu.IPTAL:
            return False
        if self.doktor is not diger.doktor or self.gun != diger.gun:
            return False
        return self.baslangic < diger.bitis and diger.baslangic < self.bitis

    def __str__(self) -> str:
        return (f"{self.gun} {self.baslangic}:00 | {self.hizmet.ad} | "
                f"{self.doktor.tam_ad} | {self.hasta.tam_ad} | "
                f"{self.hizmet.ucret} TL | {self.durum.value}")


class RandevuSistemi:
    """Randevuları oluşturur ve kuralları (müsaitlik, çakışma) kontrol eder."""

    def __init__(self, klinik: Klinik):
        self.klinik = klinik
        self._randevular = []

    @property
    def randevular(self) -> tuple:
        return tuple(self._randevular)

    def randevu_olustur(self, hasta, doktor, hizmet: Hizmet,
                        gun: str, baslangic: float) -> Randevu:
        yeni = Randevu(hasta, doktor, hizmet, gun, baslangic)

        if not doktor.musait_mi(gun, yeni.baslangic, yeni.bitis):
            raise ValueError("Doktor bu zaman diliminde müsait değil.")

        for mevcut in self._randevular:
            if yeni.cakisiyor_mu(mevcut):
                raise ValueError("Randevu çakışması var.")

        self._randevular.append(yeni)
        return yeni
