"""Kurum yapısı: Kurum -> Hastane (şube) -> Klinik (bölüm) -> Doktorlar."""
from abc import ABC, abstractmethod
from datetime import time


class Hizmet(ABC):
    """Soyut hizmet: ad, süre ve taban ücret. Türler bu sınıftan türer."""

    def __init__(self, ad: str, sure_dk: int, taban_ucret: float):
        self.ad = ad
        self.sure_dk = sure_dk
        self._taban_ucret = taban_ucret      # Kapsülleme: dışarıdan değiştirilmez

    @abstractmethod
    def tur(self) -> str:
        """Hizmetin türü (alt sınıflar ezer)."""

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:
        """Aşırı yükleme (overloading) benzeri: ucret_hesapla() veya ucret_hesapla(0.1)."""
        return self._taban_ucret * (1 - indirim_orani)

    @property
    def ucret(self) -> float:
        return self.ucret_hesapla()


class Muayene(Hizmet):
    def tur(self) -> str:
        return "Muayene"


class Radyoloji(Hizmet):
    """Görüntüleme hizmeti: taban ücrete cihaz ücreti eklenir."""

    def __init__(self, ad, sure_dk, taban_ucret, cihaz_ucreti: float):
        super().__init__(ad, sure_dk, taban_ucret)
        self._cihaz_ucreti = cihaz_ucreti

    def tur(self) -> str:
        return "Radyoloji"

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:   # overriding
        return (self._taban_ucret + self._cihaz_ucreti) * (1 - indirim_orani)


class Laboratuvar(Hizmet):
    """Tahlil hizmeti: ücret, tahlil sayısıyla çarpılır."""

    def __init__(self, ad, sure_dk, taban_ucret, tahlil_sayisi: int = 1):
        super().__init__(ad, sure_dk, taban_ucret)
        self._tahlil_sayisi = tahlil_sayisi

    def tur(self) -> str:
        return "Laboratuvar"

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:   # overriding
        return self._taban_ucret * self._tahlil_sayisi * (1 - indirim_orani)


class Klinik:
    """Hastane içindeki bölüm (Dahiliye, Kardiyoloji...). Hizmet ve doktorları tutar."""

    def __init__(self, ad: str):
        self.ad = ad
        # Kapsülleme: listeler _ ile başlar, sadece metotlarla değişir
        self._hizmetler = []
        self._doktorlar = []

    def hizmet_ekle(self, hizmet: Hizmet) -> None:
        self._hizmetler.append(hizmet)

    def doktor_ekle(self, doktor) -> None:
        """Doktoru kliniğe ekler, doktora da kliniği bildirir (çoktan çoğa)."""
        if doktor not in self._doktorlar:
            self._doktorlar.append(doktor)
            doktor.klinige_katil(self)

    @property
    def hizmetler(self) -> tuple:
        return tuple(self._hizmetler)

    @property
    def doktorlar(self) -> tuple:
        return tuple(self._doktorlar)


class Hastane:
    """Kurumun bir şubesi: çalışma saatleri ve klinikleri vardır."""

    def __init__(self, ad: str, acilis: time = time(8, 0), kapanis: time = time(17, 0)):
        self.ad = ad
        self.acilis = acilis
        self.kapanis = kapanis
        self._klinikler = []

    def klinik_ekle(self, klinik: Klinik) -> None:
        self._klinikler.append(klinik)

    def klinik_bul(self, ad: str) -> Klinik:
        for klinik in self._klinikler:
            if klinik.ad == ad:
                return klinik
        raise ValueError(f"'{ad}' kliniği bulunamadı.")

    def acik_mi(self, baslangic, bitis) -> bool:
        """baslangic ve bitis datetime; saat kısmı çalışma saatleri içinde mi?"""
        return self.acilis <= baslangic.time() and bitis.time() <= self.kapanis

    @property
    def klinikler(self) -> tuple:
        return tuple(self._klinikler)


class Kurum:
    """Çok şubeli sağlık kuruluşu: birden fazla hastaneyi yönetir."""

    def __init__(self, ad: str):
        self.ad = ad
        self._hastaneler = []

    def hastane_ekle(self, hastane: Hastane) -> None:
        self._hastaneler.append(hastane)

    def hastane_bul(self, ad: str) -> Hastane:
        for hastane in self._hastaneler:
            if hastane.ad == ad:
                return hastane
        raise ValueError(f"'{ad}' hastanesi bulunamadı.")

    @property
    def hastaneler(self) -> tuple:
        return tuple(self._hastaneler)
