from abc import ABC, abstractmethod
from datetime import time

from randevu.hatalar import BulunamadiHatasi, SistemHatasi


def _para_yaz(val: float) -> str:
    if isinstance(val, (int, float)) and float(val).is_integer():
        return f"{int(val)} TL"
    return f"{val} TL"


class Hizmet(ABC):
    """Soyut hizmet: ad, süre ve taban ücret. Türler bu sınıftan türer."""

    def __init__(self, ad: str, sure_dk: int, taban_ucret: float):
        if not ad or not ad.strip():
            raise ValueError("Hizmet adı boş olamaz.")
        if sure_dk <= 0:
            raise ValueError("Hizmet süresi 0'dan büyük olmalıdır.")
        if taban_ucret < 0:
            raise ValueError("Hizmet ücreti negatif olamaz.")
        self.ad = ad.strip()
        self.sure_dk = sure_dk
        self._taban_ucret = taban_ucret      # Kapsülleme: dışarıdan değiştirilmez

    @property
    def taban_ucret(self) -> float:
        return self._taban_ucret

    @property
    def cihaz_ucreti(self) -> float:
        return 0.0

    @property
    def ek_ucret(self) -> float:
        return 0.0

    @abstractmethod
    def tur(self) -> str:
        """Hizmetin türü (alt sınıflar ezer)."""

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:
        """Aşırı yükleme (overloading) benzeri: ucret_hesapla() veya ucret_hesapla(0.1)."""
        return self._taban_ucret * (1 - indirim_orani)

    @property
    def ucret(self) -> float:
        return self.ucret_hesapla()

    @property
    def ucret_metni(self) -> str:
        """Kullanıcı arayüzünde gösterilecek ücret metni."""
        return _para_yaz(self.ucret)

    def sozluge(self) -> dict:
        """Kaydetmek için sözlüğe çevirir (alt sınıflar ekleme yapar)."""
        return {"tur": type(self).__name__, "ad": self.ad,
                "sure_dk": self.sure_dk, "taban_ucret": self._taban_ucret}


class Muayene(Hizmet):
    def tur(self) -> str:
        return "Muayene"


class Radyoloji(Hizmet):
    """Görüntüleme hizmeti: taban ücrete cihaz ücreti eklenir."""

    def __init__(self, ad, sure_dk, taban_ucret, cihaz_ucreti: float):
        super().__init__(ad, sure_dk, taban_ucret)
        if cihaz_ucreti < 0:
            raise ValueError("Cihaz ücreti negatif olamaz.")
        self._cihaz_ucreti = cihaz_ucreti

    @property
    def cihaz_ucreti(self) -> float:
        return self._cihaz_ucreti

    @property
    def ek_ucret(self) -> float:
        return self._cihaz_ucreti

    def tur(self) -> str:
        return "Radyoloji"

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["cihaz_ucreti"] = self._cihaz_ucreti
        return veri

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:   # overriding
        return (self._taban_ucret + self._cihaz_ucreti) * (1 - indirim_orani)

    @property
    def ucret_metni(self) -> str:      # overriding
        if self._cihaz_ucreti > 0:
            return f"{_para_yaz(self.ucret)} (+{_para_yaz(self._cihaz_ucreti)} ek ücret)"
        return _para_yaz(self.ucret)


class Laboratuvar(Hizmet):
    """Tahlil hizmeti: ücret, tahlil sayısıyla çarpılır."""

    def __init__(self, ad, sure_dk, taban_ucret, tahlil_sayisi: int = 1):
        super().__init__(ad, sure_dk, taban_ucret)
        if tahlil_sayisi < 1:
            raise ValueError("Tahlil sayısı en az 1 olmalıdır.")
        self._tahlil_sayisi = tahlil_sayisi

    @property
    def tahlil_sayisi(self) -> int:
        return self._tahlil_sayisi

    def tur(self) -> str:
        return "Laboratuvar"

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["tahlil_sayisi"] = self._tahlil_sayisi
        return veri

    def ucret_hesapla(self, indirim_orani: float = 0.0) -> float:   # overriding
        return self._taban_ucret * self._tahlil_sayisi * (1 - indirim_orani)

    @property
    def ucret_metni(self) -> str:      # overriding
        if self._tahlil_sayisi > 1:
            return f"{_para_yaz(self.ucret)} ({self._tahlil_sayisi} tahlil)"
        return _para_yaz(self.ucret)


class Klinik:
    """Hastane içindeki bölüm (Dahiliye, Kardiyoloji...). Hizmet ve doktorları tutar."""

    def __init__(self, ad: str):
        self.ad = ad
        self.hastane = None
        # Kapsülleme: listeler _ ile başlar, sadece metotlarla değişir
        self._hizmetler = []
        self._doktorlar = []
        self._personel = []         # doktor dışındaki personel (asistan, hemşire...)

    def hizmet_ekle(self, hizmet: Hizmet) -> None:
        for mevcut in self._hizmetler:
            if mevcut.ad == hizmet.ad:
                raise SistemHatasi(f"'{hizmet.ad}' hizmeti bu klinikte zaten var.")
        self._hizmetler.append(hizmet)

    def hizmet_cikar(self, hizmet: Hizmet) -> None:
        """Hizmeti klinikten kaldırır ve doktorları bilgilendirir."""
        if hizmet not in self._hizmetler:
            raise SistemHatasi(f"'{hizmet.ad}' hizmeti bu klinikte kayıtlı değil.")
        self._hizmetler.remove(hizmet)
        for doktor in self._doktorlar:
            doktor.hizmet_cikarildi(self, hizmet)

    def doktor_ekle(self, doktor) -> None:
        """Doktoru kliniğe ekler, doktora da kliniği bildirir (çoktan çoğa)."""
        if not doktor.klinige_uygun_mu(self):
            raise SistemHatasi(
                f"{doktor.tam_ad} ({doktor.uzmanlik}) sadece kendi uzmanlık kliniğine atanabilir, '{self.ad}' kliniğine atanamaz.")
        if doktor not in self._doktorlar:
            self._doktorlar.append(doktor)
            doktor.klinige_katil(self)

    def doktor_yukle(self, doktor) -> None:
        """Dosyadan yüklenirken doktoru ekler."""
        if doktor.klinige_uygun_mu(self) and doktor not in self._doktorlar:
            self._doktorlar.append(doktor)
            doktor.klinige_katil(self)

    def personel_ekle(self, personel) -> None:
        """Doktor dışı personeli kliniğe ekler (çoktan çoğa)."""
        if personel not in self._personel:
            self._personel.append(personel)
            personel.klinige_katil(self)

    @property
    def personeller(self) -> tuple:
        return tuple(self._personel)

    def kapat(self) -> None:
        """Klinik kapatılırken tüm doktor ve personelin bu kliniğe bağlantısı kaldırılır."""
        calisanlar = self._doktorlar + self._personel
        self._doktorlar = []
        self._personel = []
        for kisi in calisanlar:
            kisi.klinikten_ayril(self)

    @property
    def hizmetler(self) -> tuple:
        return tuple(self._hizmetler)

    @property
    def doktorlar(self) -> tuple:
        return tuple(self._doktorlar)


class Hastane:
    """Kurumun bir şubesi: çalışma saatleri ve klinikleri vardır."""

    def __init__(self, ad: str, acilis: time = time(8, 0), kapanis: time = time(17, 0)):
        self._klinikler = []
        self.duzenle(ad, acilis, kapanis)

    def duzenle(self, ad: str, acilis: time, kapanis: time) -> None:
        """Ad ve çalışma saatlerini doğrulayıp günceller (hata olursa hiçbir şey değişmez)."""
        if not ad or not ad.strip():
            raise ValueError("Hastane adı boş olamaz.")
        if acilis >= kapanis:
            raise ValueError("Açılış saati kapanış saatinden önce olmalıdır.")
        self.ad = ad.strip()
        self.acilis = acilis
        self.kapanis = kapanis

    def klinik_ekle(self, klinik: Klinik) -> None:
        """Klinik adı aynı hastane içinde benzersiz olmalı (yeniden yüklemede doğru klinik bulunsun)."""
        if any(k.ad.lower() == klinik.ad.lower() for k in self._klinikler):
            raise SistemHatasi(f"'{klinik.ad}' kliniği bu hastanede zaten var.")
        klinik.hastane = self
        self._klinikler.append(klinik)

    def klinik_cikar(self, klinik: Klinik) -> None:
        if klinik not in self._klinikler:
            raise BulunamadiHatasi(f"'{klinik.ad}' kliniği bu hastanede yok.")
        klinik.hastane = None
        self._klinikler.remove(klinik)

    def klinik_bul(self, ad: str) -> Klinik:
        for klinik in self._klinikler:
            if klinik.ad == ad:
                return klinik
        raise BulunamadiHatasi(f"'{ad}' kliniği bulunamadı.")

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
        """Hastane adı kurum içinde benzersiz olmalı."""
        if self.ad_kullanilmis_mi(hastane.ad):
            raise SistemHatasi(f"'{hastane.ad}' hastanesi kurumda zaten var.")
        self._hastaneler.append(hastane)

    def ad_kullanilmis_mi(self, ad: str, haric: Hastane = None) -> bool:
        """Verilen ad, 'haric' dışındaki bir hastanede kullanılıyor mu?"""
        return any(h is not haric and h.ad.lower() == ad.strip().lower() for h in self._hastaneler)

    def hastane_cikar(self, hastane: Hastane) -> None:
        if hastane not in self._hastaneler:
            raise BulunamadiHatasi(f"'{hastane.ad}' hastanesi kurumda yok.")
        self._hastaneler.remove(hastane)

    def hastane_bul(self, ad: str) -> Hastane:
        for hastane in self._hastaneler:
            if hastane.ad == ad:
                return hastane
        raise BulunamadiHatasi(f"'{ad}' hastanesi bulunamadı.")

    @property
    def hastaneler(self) -> tuple:
        return tuple(self._hastaneler)
