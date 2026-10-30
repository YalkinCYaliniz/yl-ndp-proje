"""Uygulamanın tüm verisini tek yerde tutar (kurum, randevu sistemi, kullanıcılar)."""
from randevu.guvenlik import Sifre
from randevu.hatalar import SistemHatasi
from randevu.kullanici import Hasta, Misafir, Doktor
from randevu.kurum import Kurum
from randevu.randevu import RandevuSistemi

VARSAYILAN_SIFRE = "123456"      # demo: tüm örnek kullanıcıların şifresi


class Uygulama:
    def __init__(self):
        self.kurum = Kurum("Yaşam Sağlık Grubu")
        self.sistem = RandevuSistemi()
        self.kullanicilar = []

    def kullanici_ekle(self, kullanici) -> None:
        for k in self.kullanicilar:
            if k.tc_no == kullanici.tc_no:
                raise SistemHatasi("Bu TC kimlik no ile kayıtlı bir kullanıcı var.")
            if k.kullanici_adi == kullanici.kullanici_adi:
                raise SistemHatasi("Bu kullanıcı adı zaten alınmış.")
            if k.eposta == kullanici.eposta:
                raise SistemHatasi("Bu e-posta ile kayıtlı bir kullanıcı var.")
        self.kullanicilar.append(kullanici)

    def kimlik_dogrula(self, kullanici_adi: str, sifre: str):
        """Kullanıcı adı ve şifre doğruysa kullanıcıyı döndürür."""
        for k in self.kullanicilar:
            if k.kullanici_adi == kullanici_adi.strip().lower() and k.sifre_dogru_mu(sifre):
                return k
        raise SistemHatasi("Kullanıcı adı veya şifre hatalı.")

    def hasta_kaydet(self, ad, soyad, tc, eposta, kullanici_adi, sifre, sifre_tekrar) -> Hasta:
        """Yeni hasta hesabı oluşturur (kayıt ol)."""
        if sifre != sifre_tekrar:
            raise SistemHatasi("Şifreler eşleşmiyor.")
        hasta = Hasta(ad, soyad, tc)
        hasta.kullanici_adi = kullanici_adi
        hasta.eposta = eposta
        hasta.sifre_belirle(Sifre.olustur(sifre))
        self.kullanici_ekle(hasta)
        return hasta

    def misafir_olustur(self, ad, soyad) -> Misafir:
        """Kayıt olmadan devam eden kişi için geçici hesap açar."""
        sira = len(self.kullanicilar)
        tc = "8" + str(sira).zfill(10)
        while any(k.tc_no == tc for k in self.kullanicilar):
            sira += 1
            tc = "8" + str(sira).zfill(10)
        misafir = Misafir(ad, soyad, tc)
        self.kullanici_ekle(misafir)
        return misafir

    def doktorlar(self) -> list:
        return [k for k in self.kullanicilar if isinstance(k, Doktor)]

    def kullanici_degistir(self, eski, yeni) -> None:
        """Kullanıcının rol nesnesini listedeki sırasını ve kimlik bilgilerini koruyarak günceller."""
        if eski not in self.kullanicilar:
            raise SistemHatasi("Kullanıcı sistemde kayıtlı değil.")
        eski.kimlik_aktar(yeni)
        self.kullanicilar[self.kullanicilar.index(eski)] = yeni
        for r in self.sistem.randevular:
            if r.hasta is eski:
                r.hasta = yeni
