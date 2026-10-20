"""Kullanıcı sınıf hiyerarşisi: soyut taban sınıf + kalıtım + çok biçimlilik."""
from abc import ABC, abstractmethod


class Kullanici(ABC):
    """Tüm roller için soyut taban sınıf."""

    def __init__(self, ad: str, soyad: str, tc_no: str):
        self.ad = ad
        self.soyad = soyad
        self.__tc_no = None          # kapsülleme: özel alan
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
        self._hizmetler = []         # korumalı alan
        self._musaitlik = []         # (gun, baslangic_saat, bitis_saat)

    def rol(self) -> str:
        return "Sağlık Personeli"

    def yetkiler(self) -> list[str]:
        return ["randevu_onayla", "musaitlik_tanimla"]

    def hizmet_ekle(self, hizmet) -> None:
        if hizmet not in self._hizmetler:
            self._hizmetler.append(hizmet)

    @property
    def hizmetler(self) -> tuple:
        return tuple(self._hizmetler)   # dışarıya salt okunur görünüm

    def musaitlik_ekle(self, gun: str, baslangic: int, bitis: int) -> None:
        if not (0 <= baslangic < bitis <= 24):
            raise ValueError("Geçersiz saat aralığı.")
        self._musaitlik.append((gun, baslangic, bitis))

    def musait_mi(self, gun: str, baslangic: float, bitis: float) -> bool:
        for g, b, s in self._musaitlik:
            if g == gun and b <= baslangic and bitis <= s:
                return True
        return False


class Doktor(SaglikPersoneli):
    def rol(self) -> str:        # çok biçimlilik: method overriding
        return "Doktor"

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["recete_yaz"]


class Yonetici(Kullanici):
    def rol(self) -> str:
        return "Klinik Yöneticisi"

    def yetkiler(self) -> list[str]:
        return ["klinik_tanimla", "hizmet_tanimla", "personel_kaydet"]
