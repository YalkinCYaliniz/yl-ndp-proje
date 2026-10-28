"""Kullanıcı sınıf hiyerarşisi: soyut taban sınıf + kalıtım + çok biçimlilik."""
import re
from abc import ABC, abstractmethod

from randevu.guvenlik import Sifre
from randevu.hatalar import RandevuHatasi, SistemHatasi, YetkiHatasi

_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


class Kullanici(ABC):
    """Tüm roller için soyut taban sınıf."""

    def __init__(self, ad: str, soyad: str, tc_no: str):
        self.ad = ad
        self.soyad = soyad
        self.__tc_no = None          # Kapsülleme: özel alan
        self.tc_no = tc_no           # property üzerinden doğrulanır
        self.__sifre = None          # Sifre nesnesi; düz şifre hiçbir yerde tutulmaz
        self.__kullanici_adi = None
        self.__eposta = None
        self.kullanici_adi = f"{ad}.{soyad}".translate(_TR).lower().replace(" ", "")
        self.eposta = f"{self.kullanici_adi}@hastane.com"

    @property
    def kullanici_adi(self) -> str:
        return self.__kullanici_adi

    @kullanici_adi.setter
    def kullanici_adi(self, deger: str):
        deger = deger.strip().lower()
        if not re.fullmatch(r"[a-z0-9._]{3,30}", deger):
            raise ValueError("Kullanıcı adı 3-30 karakter olmalı; harf, rakam, nokta ve alt çizgi içerebilir.")
        self.__kullanici_adi = deger

    @property
    def eposta(self) -> str:
        return self.__eposta

    @eposta.setter
    def eposta(self, deger: str):
        deger = deger.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", deger):
            raise ValueError("Geçerli bir e-posta adresi girin.")
        self.__eposta = deger

    @property
    def kayitli_mi(self) -> bool:
        """Misafir bunu ezer; kayıtlı kullanıcılar giriş yapabilir."""
        return True

    def sifre_belirle(self, sifre: Sifre) -> None:
        self.__sifre = sifre

    def sifre_dogru_mu(self, duz_sifre: str) -> bool:
        return self.__sifre is not None and self.__sifre.dogru_mu(duz_sifre)

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

    def sozluge(self) -> dict:
        """Kaydetmek için sözlüğe çevirir (alt sınıflar ekleme yapar)."""
        return {"tur": type(self).__name__, "ad": self.ad,
                "soyad": self.soyad, "tc_no": self.tc_no,
                "kullanici_adi": self.kullanici_adi, "eposta": self.eposta,
                "sifre": self.__sifre.sozluge() if self.__sifre else None}

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


class Misafir(Hasta):
    """Kayıt olmadan ilerleyen hasta: randevu alır ama giriş yapamaz ve eski randevularını göremez."""

    def __init__(self, ad: str, soyad: str, tc_no: str):
        super().__init__(ad, soyad, tc_no)
        self.kullanici_adi = f"misafir{tc_no}"
        self.eposta = f"{self.kullanici_adi}@misafir.local"

    def rol(self) -> str:
        return "Misafir"

    @property
    def kayitli_mi(self) -> bool:
        return False


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

    def klinige_ata(self, klinik) -> None:
        """Personeli kliniğe atar. Doktor bunu ezerek doktor listesine ekler (çok biçimlilik)."""
        klinik.personel_ekle(self)

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

    @property
    def musaitlik(self) -> tuple:
        return tuple(self._musaitlik)

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["uzmanlik"] = self.uzmanlik
        veri["musaitlik"] = [[b.isoformat(), s.isoformat()] for b, s in self._musaitlik]
        return veri

    def musaitlik_ekle(self, baslangic, bitis) -> None:
        """Çalışılan zaman aralığı (datetime). Örn: 14.10.2026 09:00 - 12:00"""
        if baslangic >= bitis:
            raise ValueError("Bitiş, başlangıçtan sonra olmalı.")
        for b, s in self._musaitlik:
            if baslangic < s and b < bitis:
                raise ValueError("Bu aralık mevcut bir müsaitlikle çakışıyor.")
        self._musaitlik.append((baslangic, bitis))

    def musaitlik_yukle(self, baslangic, bitis) -> None:
        """Dosyadan okunan müsaitliği kontrol yapmadan ekler."""
        self._musaitlik.append((baslangic, bitis))

    def musaitlik_sil(self, sira: int, randevular) -> None:
        """Müsaitliği siler. İçinde aktif randevu varsa silinemez.

        randevular: bu personelin randevu listesi.
        """
        self._yetki_kontrol("musaitlik_tanimla")
        baslangic, bitis = self._musaitlik[sira]
        for r in randevular:
            if r.aktif_mi and baslangic <= r.baslangic and r.bitis <= bitis:
                raise RandevuHatasi(
                    "Bu aralıkta aktif randevu var; önce randevuyu iptal/reddedin.")
        del self._musaitlik[sira]

    def musaitlik_listesi(self, gun) -> list:
        """Verilen günün (date) (baslangic, bitis) aralıkları."""
        return [(b, s) for b, s in self._musaitlik if b.date() == gun]

    def musait_mi(self, baslangic, bitis) -> bool:
        for b, s in self._musaitlik:
            if b <= baslangic and bitis <= s:
                return True
        return False


class Doktor(SaglikPersoneli):
    MAX_ASISTAN = 3         # bir doktora en fazla bu kadar asistan bağlanabilir

    def __init__(self, ad, soyad, tc_no, uzmanlik: str):
        super().__init__(ad, soyad, tc_no, uzmanlik)
        self._asistanlar = []

    def rol(self) -> str:        # Çok biçimlilik: method overriding
        return "Doktor"

    def klinige_ata(self, klinik) -> None:     # overriding: doktorlar ayrı listede tutulur
        klinik.doktor_ekle(self)

    @property
    def asistanlar(self) -> tuple:
        return tuple(self._asistanlar)

    @property
    def asistan_kapasitesi_dolu_mu(self) -> bool:
        return len(self._asistanlar) >= self.MAX_ASISTAN

    @property
    def asistan_metni(self) -> str:
        """Ekranda göstermek için: 'Asistan: Elif Aydın' ya da boş."""
        if not self._asistanlar:
            return ""
        return "Asistan: " + ", ".join(a.tam_ad for a in self._asistanlar)

    def _asistan_baglandi(self, asistan) -> None:
        """Asistan.doktora_bagla() tarafından çağrılır."""
        if asistan not in self._asistanlar:
            self._asistanlar.append(asistan)

    def _asistan_ayrildi(self, asistan) -> None:
        if asistan in self._asistanlar:
            self._asistanlar.remove(asistan)

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["randevu_onayla", "recete_yaz"]


class Asistan(SaglikPersoneli):
    """Bir doktora bağlı çalışır; doktor değiştirilebilir."""

    def __init__(self, ad, soyad, tc_no, uzmanlik: str = "Asistan"):
        super().__init__(ad, soyad, tc_no, uzmanlik)
        self._doktor = None

    def rol(self) -> str:
        return "Asistan"

    def yetkiler(self) -> list[str]:
        return super().yetkiler() + ["hasta_hazirla"]

    @property
    def doktor(self):
        return self._doktor

    def doktora_bagla(self, doktor) -> None:
        """Asistanı doktora bağlar; önceki doktordan otomatik ayrılır."""
        if doktor is self._doktor:
            return
        ortak = [k for k in self._klinikler if doktor in k.doktorlar]
        if not ortak:
            raise SistemHatasi("Asistan ve doktor ortak bir klinikte olmalı.")
        if doktor.asistan_kapasitesi_dolu_mu:      # önce kontrol: hata olursa eski bağlantı bozulmaz
            raise SistemHatasi(
                f"{doktor.tam_ad} en fazla {Doktor.MAX_ASISTAN} asistana sahip olabilir.")
        self.doktordan_ayril()
        doktor._asistan_baglandi(self)
        self._doktor = doktor

    def doktordan_ayril(self) -> None:
        if self._doktor is not None:
            self._doktor._asistan_ayrildi(self)
            self._doktor = None

    def hasta_hazirla(self, randevu) -> str:
        self._yetki_kontrol("hasta_hazirla")
        if randevu.doktor is not self._doktor:
            raise YetkiHatasi("Sadece bağlı olduğunuz doktorun hastalarını hazırlayabilirsiniz.")
        return f"{randevu.hasta.tam_ad} muayeneye hazırlandı."

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["doktor"] = self._doktor.tc_no if self._doktor else None
        return veri


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

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["cihaz"] = self.cihaz
        return veri

    def tetkik_yap(self, randevu) -> str:
        self._yetki_kontrol("tetkik_yap")
        return f"{randevu.hasta.tam_ad} için {self.cihaz} ile {randevu.hizmet.ad} yapıldı."


class Yonetici(Kullanici):
    """Admin: hastane, klinik, doktor, hizmet ve randevu ekleyebilir."""

    def rol(self) -> str:
        return "Admin"

    def yetkiler(self) -> list[str]:
        return ["hastane_ekle", "klinik_ekle", "doktor_ekle", "hizmet_ekle", "randevu_ekle",
                "personel_kaydet", "personel_ata", "asistan_bagla"]

    def personel_kaydet(self, uygulama, personel) -> None:
        self._yetki_kontrol("personel_kaydet")
        uygulama.kullanici_ekle(personel)

    def personel_ata(self, klinik, personel) -> None:
        """Her personel türünü kliniğe atar (doktor/asistan/hemşire...)."""
        self._yetki_kontrol("personel_ata")
        personel.klinige_ata(klinik)

    def asistan_bagla(self, asistan, doktor) -> None:
        """Asistanı doktora bağlar veya başka doktora taşır."""
        self._yetki_kontrol("asistan_bagla")
        asistan.doktora_bagla(doktor)

    def asistan_ayir(self, asistan) -> None:
        """Asistanı bağlı olduğu doktordan ayırır."""
        self._yetki_kontrol("asistan_bagla")
        asistan.doktordan_ayril()

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
