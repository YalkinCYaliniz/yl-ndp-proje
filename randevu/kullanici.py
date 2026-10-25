"""Kullanıcı sınıf hiyerarşisi: soyut taban sınıf + kalıtım + çok biçimlilik."""
from abc import ABC, abstractmethod

from randevu.hatalar import YetkiHatasi


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

    def yetki_var_mi(self, islem: str) -> bool:
        return islem in self.yetkiler()

    def _yetki_kontrol(self, islem: str) -> None:
        """Alt sınıfların metotları işlem öncesi bunu çağırır."""
        if not self.yetki_var_mi(islem):
            raise YetkiHatasi(f"{self.rol()} '{islem}' işlemini yapamaz.")

    def __str__(self) -> str:
        return f"[{self.rol()}] {self.tam_ad}"


class Hasta(Kullanici):
    """Normal kullanıcı: randevu alır ve sadece kendi randevusunu iptal eder."""

    def rol(self) -> str:
        return "Hasta"

    def yetkiler(self) -> list[str]:
        return ["randevu_al", "randevu_iptal"]

    def randevu_al(self, sistem, hastane, klinik, doktor, hizmet, baslangic):
        self._yetki_kontrol("randevu_al")
        return sistem.randevu_olustur(self, hastane, klinik, doktor, hizmet, baslangic)

    def randevularim(self, sistem) -> list:
        """Hastanın kendi randevu geçmişi."""
        return sistem.hastanin_randevulari(self)

    def randevu_iptal(self, randevu) -> None:
        self._yetki_kontrol("randevu_iptal")
        if randevu.hasta is not self:
            raise YetkiHatasi("Başkasının randevusunu iptal edemezsiniz.")
        randevu.iptal()


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
        return ["musaitlik_tanimla"]

    def randevu_onayla(self, randevu) -> None:
        self._yetki_kontrol("randevu_onayla")
        if randevu.doktor is not self:
            raise YetkiHatasi("Sadece kendi randevularınızı onaylayabilirsiniz.")
        randevu.onayla()

    def randevu_reddet(self, randevu) -> None:
        self._yetki_kontrol("randevu_onayla")
        if randevu.doktor is not self:
            raise YetkiHatasi("Sadece kendi randevularınızı reddedebilirsiniz.")
        randevu.reddet()

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
        return super().yetkiler() + ["randevu_onayla", "recete_yaz"]


class Hemsire(SaglikPersoneli):
    """Randevu onaylayamaz; gelen hastayı kabul eder."""

    def rol(self) -> str:
        return "Hemşire"

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["hasta_kabul"]

    def hasta_kabul(self, randevu) -> str:
        self._yetki_kontrol("hasta_kabul")
        return f"{randevu.hasta.tam_ad} hasta kabulü yapıldı."


class Teknisyen(SaglikPersoneli):
    """Radyoloji/laboratuvar cihazını kullanır."""

    def __init__(self, ad, soyad, tc_no, uzmanlik: str, cihaz: str):
        super().__init__(ad, soyad, tc_no, uzmanlik)
        self.cihaz = cihaz

    def rol(self) -> str:
        return "Teknisyen"

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["tetkik_yap"]

    def tetkik_yap(self, randevu) -> str:
        self._yetki_kontrol("tetkik_yap")
        return f"{randevu.hasta.tam_ad} için {self.cihaz} ile {randevu.hizmet.ad} yapıldı."


class Yonetici(Kullanici):
    """Admin: hastane, klinik, doktor, hizmet ve randevu ekleyebilir."""

    def rol(self) -> str:
        return "Admin"

    def yetkiler(self) -> list[str]:
        return ["hastane_ekle", "klinik_ekle", "doktor_ekle", "hizmet_ekle", "randevu_ekle"]

    def hastane_ekle(self, kurum, hastane) -> None:
        self._yetki_kontrol("hastane_ekle")
        kurum.hastane_ekle(hastane)

    def klinik_ekle(self, hastane, klinik) -> None:
        self._yetki_kontrol("klinik_ekle")
        hastane.klinik_ekle(klinik)

    def doktor_ekle(self, klinik, doktor) -> None:
        self._yetki_kontrol("doktor_ekle")
        klinik.doktor_ekle(doktor)

    def hizmet_ekle(self, klinik, hizmet) -> None:
        self._yetki_kontrol("hizmet_ekle")
        klinik.hizmet_ekle(hizmet)

    def randevu_ekle(self, sistem, hasta, hastane, klinik, doktor, hizmet, baslangic):
        self._yetki_kontrol("randevu_ekle")
        return sistem.randevu_olustur(hasta, hastane, klinik, doktor, hizmet, baslangic)
