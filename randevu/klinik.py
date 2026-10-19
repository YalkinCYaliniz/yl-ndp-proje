"""Klinik, hizmet ve randevu modelleri."""
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Hizmet:
    ad: str
    sure_dk: int
    ucret: float


class Klinik:
    def __init__(self, ad: str, acilis: int = 8, kapanis: int = 17):
        self.ad = ad
        self.acilis, self.kapanis = acilis, kapanis
        self._bolumler: set[str] = set()
        self._hizmetler: dict[str, Hizmet] = {}
        self._personel: list = []

    def bolum_ekle(self, bolum: str) -> None:
        self._bolumler.add(bolum)

    def hizmet_ekle(self, hizmet: Hizmet) -> None:
        self._hizmetler[hizmet.ad] = hizmet

    def personel_ekle(self, personel) -> None:
        self._personel.append(personel)

    @property
    def hizmetler(self) -> dict:
        return dict(self._hizmetler)

    @property
    def personel(self) -> tuple:
        return tuple(self._personel)


class RandevuDurumu(Enum):
    BEKLIYOR = "Bekliyor"
    ONAYLANDI = "Onaylandı"
    IPTAL = "İptal"


class Randevu:
    def __init__(self, hasta, doktor, hizmet: Hizmet, gun: str, baslangic: int):
        self.hasta, self.doktor, self.hizmet = hasta, doktor, hizmet
        self.gun, self.baslangic = gun, baslangic
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
        return (self.doktor is diger.doktor and self.gun == diger.gun
                and self.baslangic < diger.bitis and diger.baslangic < self.bitis
                and RandevuDurumu.IPTAL not in (self.durum, diger.durum))

    def __str__(self) -> str:
        return (f"{self.gun} {self.baslangic}:00 | {self.hizmet.ad} | "
                f"{self.doktor.tam_ad} | {self.hasta.tam_ad} | "
                f"{self.hizmet.ucret} TL | {self.durum.value}")


class RandevuSistemi:
    def __init__(self, klinik: Klinik):
        self.klinik = klinik
        self._randevular: list[Randevu] = []

    def randevu_olustur(self, hasta, doktor, hizmet: Hizmet,
                        gun: str, baslangic: int) -> Randevu:
        yeni = Randevu(hasta, doktor, hizmet, gun, baslangic)
        if not doktor.musait_mi(gun, baslangic, int(-(-yeni.bitis // 1))):
            raise ValueError("Doktor bu zaman diliminde müsait değil.")
        if any(yeni.cakisiyor_mu(r) for r in self._randevular):
            raise ValueError("Randevu çakışması var.")
        self._randevular.append(yeni)
        return yeni
