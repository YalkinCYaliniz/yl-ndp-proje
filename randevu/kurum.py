"""Kurum yapısı: Kurum -> Hastane (şube) -> Klinik (bölüm) -> Doktorlar."""
from datetime import time


class Hizmet:
    """Kliniğin sunduğu bir sağlık hizmeti (ad, süre, ücret)."""

    def __init__(self, ad: str, sure_dk: int, ucret: float):
        self.ad = ad
        self.sure_dk = sure_dk
        self.ucret = ucret


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
