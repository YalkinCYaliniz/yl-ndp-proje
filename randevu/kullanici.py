"""Kullanıcı sınıf hiyerarşisi: soyut taban sınıf + kalıtım + çok biçimlilik."""
import re
from abc import ABC, abstractmethod

from randevu.guvenlik import Sifre
from randevu.hatalar import RandevuHatasi, SistemHatasi, YetkiHatasi
from randevu.recete import Recete

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

    def kimlik_aktar(self, hedef: "Kullanici"):
        """Rol değişiminde kullanıcı adı, e-posta ve şifre özetini yeni nesneye aktarır."""
        hedef.kullanici_adi = self.kullanici_adi
        hedef.eposta = self.eposta
        if self.__sifre is not None:
            hedef.sifre_belirle(self.__sifre)
        return hedef

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

    def receteli_randevularim(self, sistem) -> list:
        """Reçete yazılmış randevular (en yeni üstte)."""
        liste = [r for r in self.randevularim(sistem) if r.recete is not None]
        return sorted(liste, key=lambda r: r.recete.tarih, reverse=True)

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
        self._uzmanlik = None
        self.uzmanlik = uzmanlik
        self._klinikler = []     # bir personel birden fazla kliniğe bağlı olabilir

    @property
    def uzmanlik(self) -> str:
        return self._uzmanlik

    @uzmanlik.setter
    def uzmanlik(self, deger: str):
        if not deger or not deger.strip():
            raise ValueError("Uzmanlık alanı boş olamaz.")
        self._uzmanlik = deger.strip()

    def rol(self) -> str:
        return "Sağlık Personeli"

    def yetkiler(self) -> list[str]:
        return []

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
    def klinik_metni(self) -> str:
        """Personelin bağlı olduğu kliniklerin kısa metni."""
        if not self._klinikler:
            return "Klinik atanmadı"
        return ", ".join(k.ad for k in self._klinikler)

    @property
    def hizmetler(self) -> list:
        """Personelin sunduğu hizmetler = bağlı olduğu kliniklerin hizmetleri."""
        sonuc = []
        for klinik in self._klinikler:
            sonuc.extend(klinik.hizmetler)
        return sonuc

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["uzmanlik"] = self.uzmanlik
        return veri


class Doktor(SaglikPersoneli):
    MAX_ASISTAN = 3         # bir doktora en fazla bu kadar asistan bağlanabilir

    def __init__(self, ad, soyad, tc_no, uzmanlik: str):
        super().__init__(ad, soyad, tc_no, uzmanlik)
        self._musaitlik = []            # (baslangic datetime, bitis datetime) — sadece doktora özel
        self._asistanlar = []
        self._klinik_hizmetleri = {}    # klinik -> doktorun o klinikte verdiği hizmetler

    def rol(self) -> str:        # Çok biçimlilik: method overriding
        return "Doktor"

    def klinige_ata(self, klinik) -> None:     # overriding: doktorlar ayrı listede tutulur
        klinik.doktor_ekle(self)

    def klinige_uygun_mu(self, klinik) -> bool:
        """Doktor sadece kendi uzmanlık alanındaki kliniklerde hasta bakabilir."""
        return self.uzmanlik.lower() == klinik.ad.lower()

    @property
    def musaitlik(self) -> tuple:
        return tuple(self._musaitlik)

    def musaitlik_ekle(self, baslangic, bitis) -> None:
        """Çalışılan zaman aralığı (datetime). Örn: 14.10.2026 09:00 - 12:00"""
        self._yetki_kontrol("musaitlik_tanimla")
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
        """Müsaitliği siler. İçinde aktif randevu varsa silinemez."""
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

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["musaitlik"] = [[b.isoformat(), s.isoformat()] for b, s in self._musaitlik]
        return veri

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
        return ["musaitlik_tanimla", "randevu_onayla", "recete_yaz", "hizmet_sec", "asistan_ekle"]

    def asistan_ekle(self, asistan) -> None:
        """Doktor kendi kliniğindeki bir asistanı (en fazla 3) kendisine bağlar."""
        self._yetki_kontrol("asistan_ekle")
        asistan.doktora_bagla(self)

    # ---- Doktorun sunduğu hizmetler (kliniğin hizmetlerinden seçilir) ----
    def hizmet_tanimla(self, klinik, hizmetler) -> None:
        """Doktorun bu klinikte vereceği hizmetleri belirler."""
        if klinik not in self._klinikler:
            raise SistemHatasi("Doktor bu klinikte çalışmıyor.")
        hizmetler = list(hizmetler)
        if not hizmetler:
            raise SistemHatasi("En az bir hizmet seçilmelidir.")
        for hizmet in hizmetler:
            if hizmet not in klinik.hizmetler:
                raise SistemHatasi(f"'{hizmet.ad}' bu kliniğin hizmeti değil.")
        self._klinik_hizmetleri[klinik] = tuple(hizmetler)

    def hizmetlerimi_sec(self, klinik, hizmetler) -> None:
        """Doktorun kendi hizmetlerini seçmesi (yetki kontrollü)."""
        self._yetki_kontrol("hizmet_sec")
        self.hizmet_tanimla(klinik, hizmetler)

    def ozel_hizmetler(self, klinik):
        """Seçim yapıldıysa o klinikteki seçili hizmetler, yapılmadıysa None."""
        return self._klinik_hizmetleri.get(klinik)

    def sunulan_hizmetler(self, klinik) -> list:
        """Seçim yoksa kliniğin tüm hizmetleri; varsa sadece seçilenler."""
        ozel = self._klinik_hizmetleri.get(klinik)
        if ozel is None:
            return list(klinik.hizmetler)
        return [h for h in klinik.hizmetler if h in ozel]

    def hizmet_sunar_mi(self, klinik, hizmet) -> bool:
        return hizmet in self.sunulan_hizmetler(klinik)

    @property
    def hizmetler(self) -> list:        # overriding: tüm kliniklerde sunduğu hizmetler
        sonuc = []
        for klinik in self._klinikler:
            sonuc.extend(self.sunulan_hizmetler(klinik))
        return sonuc

    def recete_yaz(self, randevu, ilaclar, doktor_notu: str = "") -> Recete:
        """Kendi onaylı randevusu için reçete yazar (varsa günceller)."""
        self._yetki_kontrol("recete_yaz")
        if randevu.doktor is not self:
            raise YetkiHatasi("Sadece kendi hastalarınız için reçete yazabilirsiniz.")
        recete = Recete(ilaclar, doktor_notu)
        randevu.recete_ekle(recete)
        return recete


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
    """Genel Admin: kurumdaki tüm hastane, klinik, personel ve randevuları yönetir."""

    def rol(self) -> str:
        return "Admin"

    def yetkiler(self) -> list[str]:
        return ["hastane_ekle", "klinik_ekle", "doktor_ekle", "hizmet_ekle", "randevu_ekle",
                "randevu_yonet", "personel_kaydet", "personel_ata", "asistan_bagla",
                "doktor_hizmet_tanimla", "hastane_yoneticisi_ata", "klinik_yoneticisi_ata"]

    @property
    def kapsam_etiketi(self) -> str:
        """Yöneticinin sorumlu olduğu birimin kısa metni (alt sınıflar ezer)."""
        return "Tüm Kurum"

    def yonetilen_hastaneler(self, kurum) -> tuple:
        """Yöneticinin görebildiği ve yönetebildiği hastaneler."""
        return kurum.hastaneler

    def yonetilen_klinikler(self, kurum) -> list:
        """Yöneticinin yönetebildiği (hastane, klinik) çiftleri."""
        return [(h, k) for h in kurum.hastaneler for k in h.klinikler]

    def yonetilen_randevular(self, sistem) -> list:
        """Yöneticinin kapsamındaki randevular."""
        return list(sistem.randevular)

    def _hastane_kontrol(self, hastane) -> None:
        """Alt sınıflar ezerek sadece kendi hastanelerine izin verir."""

    def _klinik_kontrol(self, klinik) -> None:
        """Alt sınıflar ezerek sadece kendi kliniklerine izin verir."""

    def _asistan_baglanti_kontrol(self, asistan, doktor=None) -> None:
        """Alt sınıflar ezerek sadece kendi kapsamındaki doktor/asistana izin verir."""

    def doktor_hizmet_tanimla(self, doktor, klinik, hizmetler) -> None:
        """Doktorun bir klinikte vereceği hizmetleri belirler."""
        self._yetki_kontrol("doktor_hizmet_tanimla")
        self._klinik_kontrol(klinik)
        doktor.hizmet_tanimla(klinik, hizmetler)

    def personel_kaydet(self, uygulama, personel) -> None:
        self._yetki_kontrol("personel_kaydet")
        uygulama.kullanici_ekle(personel)

    def personel_ata(self, klinik, personel) -> None:
        """Her personel türünü kliniğe atar (doktor/asistan/hemşire...)."""
        self._yetki_kontrol("personel_ata")
        self._klinik_kontrol(klinik)
        personel.klinige_ata(klinik)

    def asistan_bagla(self, asistan, doktor) -> None:
        """Asistanı doktora bağlar veya başka doktora taşır."""
        self._yetki_kontrol("asistan_bagla")
        self._asistan_baglanti_kontrol(asistan, doktor)
        asistan.doktora_bagla(doktor)

    def asistan_ayir(self, asistan) -> None:
        """Asistanı bağlı olduğu doktordan ayırır."""
        self._yetki_kontrol("asistan_bagla")
        self._asistan_baglanti_kontrol(asistan, asistan.doktor)
        asistan.doktordan_ayril()

    def hastane_ekle(self, kurum, hastane) -> None:
        self._yetki_kontrol("hastane_ekle")
        kurum.hastane_ekle(hastane)

    def klinik_ekle(self, hastane, klinik) -> None:
        self._yetki_kontrol("klinik_ekle")
        self._hastane_kontrol(hastane)
        hastane.klinik_ekle(klinik)

    def doktor_ekle(self, klinik, doktor) -> None:
        self._yetki_kontrol("doktor_ekle")
        self._klinik_kontrol(klinik)
        klinik.doktor_ekle(doktor)

    def hizmet_ekle(self, klinik, hizmet) -> None:
        self._yetki_kontrol("hizmet_ekle")
        self._klinik_kontrol(klinik)
        klinik.hizmet_ekle(hizmet)

    def randevu_ekle(self, sistem, hasta, hastane, klinik, doktor, hizmet, baslangic):
        self._yetki_kontrol("randevu_ekle")
        self._hastane_kontrol(hastane)
        self._klinik_kontrol(klinik)
        return sistem.randevu_olustur(hasta, hastane, klinik, doktor, hizmet, baslangic)

    def randevu_onayla(self, randevu) -> None:
        """Yönetici kendi kapsamındaki bekleyen randevuyu onaylar."""
        self._yetki_kontrol("randevu_yonet")
        self._hastane_kontrol(randevu.hastane)
        self._klinik_kontrol(randevu.klinik)
        randevu.onayla()

    def randevu_reddet(self, randevu) -> None:
        """Yönetici kendi kapsamındaki bekleyen randevuyu reddeder."""
        self._yetki_kontrol("randevu_yonet")
        self._hastane_kontrol(randevu.hastane)
        self._klinik_kontrol(randevu.klinik)
        randevu.reddet()

    def randevu_iptal(self, randevu) -> None:
        """Yönetici kendi kapsamındaki aktif randevuyu iptal eder."""
        self._yetki_kontrol("randevu_yonet")
        self._hastane_kontrol(randevu.hastane)
        self._klinik_kontrol(randevu.klinik)
        randevu.iptal()

    # ---- Yönetici Atama ve Rol Değiştirme (Çok Biçimlilik) ----
    def yonetilebilir_kullanicilar(self, uygulama) -> list:
        """Bu yöneticinin rolünü değiştirebileceği kullanıcılar (sira, kullanici)."""
        return [(sira, k) for sira, k in enumerate(uygulama.kullanicilar)
                if type(k) in (Hasta, HastaneYoneticisi, KlinikYoneticisi) and k.kayitli_mi]

    def _aday_kontrol(self, kisi) -> None:
        if not (type(kisi) in (Hasta, HastaneYoneticisi, KlinikYoneticisi) and kisi.kayitli_mi):
            raise SistemHatasi("Sadece normal kullanıcılar veya hastane/klinik yöneticileri seçilebilir.")

    def hastane_yoneticisi_ata(self, uygulama, kisi, hastane):
        """Normal kullanıcıyı veya alt yöneticiyi verilen hastaneye Hastane Yöneticisi yapar."""
        self._yetki_kontrol("hastane_yoneticisi_ata")
        self._aday_kontrol(kisi)
        self._hastane_kontrol(hastane)
        yeni = HastaneYoneticisi(kisi.ad, kisi.soyad, kisi.tc_no, hastane)
        uygulama.kullanici_degistir(kisi, yeni)
        return yeni

    def klinik_yoneticisi_ata(self, uygulama, kisi, hastane, klinik):
        """Normal kullanıcıyı veya alt yöneticiyi verilen kliniğe Klinik Yöneticisi yapar."""
        self._yetki_kontrol("klinik_yoneticisi_ata")
        self._aday_kontrol(kisi)
        self._hastane_kontrol(hastane)
        self._klinik_kontrol(klinik)
        yeni = KlinikYoneticisi(kisi.ad, kisi.soyad, kisi.tc_no, hastane, klinik)
        uygulama.kullanici_degistir(kisi, yeni)
        return yeni

    def yoneticilik_kaldir(self, uygulama, kisi):
        """Hastane veya klinik yöneticisini tekrar normal kullanıcı (Hasta) rolüne döndürür."""
        if isinstance(kisi, HastaneYoneticisi):
            self._yetki_kontrol("hastane_yoneticisi_ata")
        elif isinstance(kisi, KlinikYoneticisi):
            self._yetki_kontrol("klinik_yoneticisi_ata")
            self._aday_kontrol(kisi)
        else:
            raise SistemHatasi("Bu kullanıcı zaten yönetici değil.")
        yeni = Hasta(kisi.ad, kisi.soyad, kisi.tc_no)
        uygulama.kullanici_degistir(kisi, yeni)
        return yeni

    def rol_degistir(self, uygulama, kisi, yeni_rol: str, hastane=None, klinik=None):
        """Seçilen hedefe göre kullanıcının rolünü değiştirir."""
        if yeni_rol == "hastane_yoneticisi":
            return self.hastane_yoneticisi_ata(uygulama, kisi, hastane)
        if yeni_rol == "klinik_yoneticisi":
            return self.klinik_yoneticisi_ata(uygulama, kisi, hastane, klinik)
        if yeni_rol == "hasta":
            return self.yoneticilik_kaldir(uygulama, kisi)
        raise SistemHatasi("Geçersiz rol seçimi.")


class HastaneYoneticisi(Yonetici):
    """Sadece sorumlu olduğu hastaneyi yönetir; diğer hastanelere müdahale edemez."""

    def __init__(self, ad: str, soyad: str, tc_no: str, hastane=None):
        super().__init__(ad, soyad, tc_no)
        self._hastane = hastane

    @property
    def hastane(self):
        return self._hastane

    def hastane_ata(self, hastane) -> None:
        self._hastane = hastane

    def rol(self) -> str:
        return "Hastane Yöneticisi"

    def yetkiler(self) -> list[str]:
        return [y for y in super().yetkiler() if y not in ("hastane_ekle", "hastane_yoneticisi_ata")]

    def yonetilebilir_kullanicilar(self, uygulama) -> list:
        """Hastane yöneticisi sadece normal kullanıcıları ve kendi hastanesindeki klinik yöneticilerini seçebilir."""
        return [(sira, k) for sira, k in enumerate(uygulama.kullanicilar)
                if k.kayitli_mi and (type(k) is Hasta
                                     or (type(k) is KlinikYoneticisi and k.hastane is self._hastane))]

    def _aday_kontrol(self, kisi) -> None:
        super()._aday_kontrol(kisi)
        if isinstance(kisi, HastaneYoneticisi):
            raise YetkiHatasi("Hastane yöneticisi başka bir hastane yöneticisini değiştiremez.")
        if isinstance(kisi, KlinikYoneticisi) and kisi.hastane is not self._hastane:
            raise YetkiHatasi("Sadece kendi hastanenizdeki klinik yöneticilerini değiştirebilirsiniz.")

    @property
    def kapsam_etiketi(self) -> str:
        return self._hastane.ad if self._hastane else "Hastane atanmadı"

    def yonetilen_hastaneler(self, kurum) -> tuple:
        return (self._hastane,) if self._hastane else ()

    def yonetilen_klinikler(self, kurum) -> list:
        if self._hastane is None:
            return []
        return [(self._hastane, k) for k in self._hastane.klinikler]

    def yonetilen_randevular(self, sistem) -> list:
        return [r for r in sistem.randevular if r.hastane is self._hastane]

    def _hastane_kontrol(self, hastane) -> None:
        if self._hastane is None or hastane is not self._hastane:
            raise YetkiHatasi("Sadece sorumlu olduğunuz hastaneyi yönetebilirsiniz.")

    def _klinik_kontrol(self, klinik) -> None:
        if self._hastane is None or klinik not in self._hastane.klinikler:
            raise YetkiHatasi("Sadece sorumlu olduğunuz hastanedeki klinikleri yönetebilirsiniz.")

    def _asistan_baglanti_kontrol(self, asistan, doktor=None) -> None:
        if self._hastane is None:
            raise YetkiHatasi("Sorumlu olduğunuz bir hastane tanımlı değil.")
        if doktor is not None:
            ortak = [k for k in self._hastane.klinikler
                     if asistan in k.personeller and doktor in k.doktorlar]
            if not ortak:
                raise YetkiHatasi(
                    "Asistan ve doktor sorumlu olduğunuz hastanenin ortak bir kliniğinde olmalı.")
        elif not any(asistan in k.personeller for k in self._hastane.klinikler):
            raise YetkiHatasi("Sadece sorumlu olduğunuz hastanedeki asistanları yönetebilirsiniz.")

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["hastane"] = self._hastane.ad if self._hastane else None
        return veri


class KlinikYoneticisi(Yonetici):
    """Sadece sorumlu olduğu klinikteki doktor, personel, hizmet ve randevuları yönetir."""

    def __init__(self, ad: str, soyad: str, tc_no: str, hastane=None, klinik=None):
        super().__init__(ad, soyad, tc_no)
        self._hastane = None
        self._klinik = None
        if hastane is not None and klinik is not None:
            self.klinik_ata(hastane, klinik)

    @property
    def hastane(self):
        return self._hastane

    @property
    def klinik(self):
        return self._klinik

    def klinik_ata(self, hastane, klinik) -> None:
        if klinik not in hastane.klinikler:
            raise SistemHatasi("Klinik bu hastaneye ait değil.")
        self._hastane = hastane
        self._klinik = klinik

    def rol(self) -> str:
        return "Klinik Yöneticisi"

    def yetkiler(self) -> list[str]:
        return [y for y in super().yetkiler()
                if y not in ("hastane_ekle", "klinik_ekle", "hastane_yoneticisi_ata", "klinik_yoneticisi_ata")]

    def yonetilebilir_kullanicilar(self, uygulama) -> list:
        return []

    @property
    def kapsam_etiketi(self) -> str:
        if self._hastane and self._klinik:
            return f"{self._hastane.ad} / {self._klinik.ad}"
        return "Klinik atanmadı"

    def yonetilen_hastaneler(self, kurum) -> tuple:
        return (self._hastane,) if self._hastane else ()

    def yonetilen_klinikler(self, kurum) -> list:
        if self._hastane is None or self._klinik is None:
            return []
        return [(self._hastane, self._klinik)]

    def yonetilen_randevular(self, sistem) -> list:
        return [r for r in sistem.randevular if r.klinik is self._klinik]

    def _hastane_kontrol(self, hastane) -> None:
        if self._hastane is None or hastane is not self._hastane:
            raise YetkiHatasi("Sadece sorumlu olduğunuz kliniğin hastanesinde işlem yapabilirsiniz.")

    def _klinik_kontrol(self, klinik) -> None:
        if self._klinik is None or klinik is not self._klinik:
            raise YetkiHatasi("Sadece sorumlu olduğunuz kliniği yönetebilirsiniz.")

    def _asistan_baglanti_kontrol(self, asistan, doktor=None) -> None:
        if self._klinik is None or asistan not in self._klinik.personeller:
            raise YetkiHatasi("Sadece sorumlu olduğunuz klinikteki asistanları yönetebilirsiniz.")
        if doktor is not None and doktor not in self._klinik.doktorlar:
            raise YetkiHatasi("Sadece sorumlu olduğunuz klinikteki doktorları yönetebilirsiniz.")

    def sozluge(self) -> dict:
        veri = super().sozluge()
        veri["hastane"] = self._hastane.ad if self._hastane else None
        veri["klinik"] = self._klinik.ad if self._klinik else None
        return veri
