"""Kullanıcı sınıf hiyerarşisi: soyut taban sınıf + kalıtım + çok biçimlilik."""
from abc import ABC, abstractmethod


class Kullanici(ABC):
    """Tüm roller için soyut taban sınıf."""

    def __init__(self, ad: str, soyad: str, tc_no: str):
        self.ad = ad
        self.soyad = soyad
        self.__tc_no = None          # Kapsülleme: özel alan
        self.tc_no = tc_no           # property üzerinden doğrulanır

    @property
    def tc_no(self) -> str:
        return self.__tc_no

    @tc_no.setter
    def tc_no(self, deger: str):
        if not (deger.isdigit() and len(deger) == 11):
            raise ValueError("TC kimlik no 11 haneli rakam olmalıdır.")
        self.__tc_no = deger

    @property
    def tam_ad(self) -> str:
        return f"{self.ad} {self.soyad}"

    @abstractmethod
    def rol(self) -> str:
        """Rolün adı (alt sınıflar ezer)."""

    @abstractmethod
    def yetkiler(self) -> list[str]:
        """Rolün yapabildiği işlemler (alt sınıflar ezer)."""

    def __str__(self) -> str:
        return f"[{self.rol()}] {self.tam_ad}"


class Hasta(Kullanici):
    def rol(self) -> str:
        return "Hasta"

    def yetkiler(self) -> list[str]:
        return ["randevu_al", "randevu_iptal"]


class SaglikPersoneli(Kullanici):
    """Doktor ve diğer sağlık çalışanları için ortak taban."""

    def __init__(self, ad, soyad, tc_no, uzmanlik: str):
        super().__init__(ad, soyad, tc_no)
        self.uzmanlik = uzmanlik
        self._klinikler = []     # bir personel birden fazla kliniğe bağlı olabilir
        self._musaitlik = []     # (baslangic datetime, bitis datetime)

    def rol(self) -> str:
        return "Sağlık Personeli"

    def yetkiler(self) -> list[str]:
        return ["randevu_onayla", "musaitlik_tanimla"]

    def klinige_katil(self, klinik) -> None:
        """Klinik.doktor_ekle() tarafından çağrılır."""
        if klinik not in self._klinikler:
            self._klinikler.append(klinik)

    @property
    def klinikler(self) -> tuple:
        return tuple(self._klinikler)    # dışarıya salt okunur

    @property
    def hizmetler(self) -> list:
        """Personelin sunduğu hizmetler = bağlı olduğu kliniklerin hizmetleri."""
        sonuc = []
        for klinik in self._klinikler:
            sonuc.extend(klinik.hizmetler)
        return sonuc

    def musaitlik_ekle(self, baslangic, bitis) -> None:
        """Çalışılan zaman aralığı (datetime). Örn: 14.10.2026 09:00 - 12:00"""
        if baslangic >= bitis:
            raise ValueError("Bitiş, başlangıçtan sonra olmalı.")
        self._musaitlik.append((baslangic, bitis))

    def musaitlik_listesi(self, gun) -> list:
        """Verilen günün (date) (baslangic, bitis) aralıkları."""
        return [(b, s) for b, s in self._musaitlik if b.date() == gun]

    def musait_mi(self, baslangic, bitis) -> bool:
        for b, s in self._musaitlik:
            if b <= baslangic and bitis <= s:
                return True
        return False


class Doktor(SaglikPersoneli):
    def rol(self) -> str:        # Çok biçimlilik: method overriding
        return "Doktor"

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["recete_yaz"]


class Yonetici(Kullanici):
    def rol(self) -> str:
        return "Klinik Yöneticisi"

    def yetkiler(self) -> list[str]:
        return ["klinik_tanimla", "hizmet_tanimla", "personel_kaydet"]
