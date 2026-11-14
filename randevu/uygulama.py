from randevu.guvenlik import Sifre
from randevu.hatalar import SistemHatasi
from randevu.kullanici import Hasta, Misafir, Doktor, SaglikPersoneli
from randevu.kurum import Kurum
from randevu.randevu import RandevuSistemi

VARSAYILAN_SIFRE = "123456"      # demo: tüm örnek kullanıcıların şifresi

VARSAYILAN_GOREVLER = {
    "doktor": [
        "Dahiliye", "Kardiyoloji", "Göz Hastalıkları", "Radyoloji", "Ortopedi",
        "Çocuk Sağlığı", "Laboratuvar", "Nöroloji", "Kulak Burun Boğaz",
        "Genel Cerrahi", "Dermatoloji", "Üroloji", "Kadın Hastalıkları",
        "Psikiyatri", "Göğüs Hastalıkları", "Fizik Tedavi", "Endokrinoloji",
        "Gastroenteroloji"
    ],
    "asistan": ["Asistan"],
    "hemsire": ["Hemşirelik"],
    "teknisyen": ["Radyoloji", "Laboratuvar"],
}


class Uygulama:
    def __init__(self):
        self.kurum = Kurum("Yaşam Sağlık Grubu")
        self.sistem = RandevuSistemi()
        self.kullanicilar = []
        self.gorevler = {tur: list(liste) for tur, liste in VARSAYILAN_GOREVLER.items()}

    def gorev_ekle(self, tur: str, ad: str) -> None:
        """Belirtilen personel türüne yeni bir uzmanlık veya görev adı ekler."""
        tur_anahtar = tur.strip().lower()
        if tur_anahtar not in self.gorevler:
            raise SistemHatasi(f"Geçersiz personel türü: {tur}")
        ad_temiz = ad.strip()
        if not ad_temiz:
            raise ValueError("Uzmanlık / görev adı boş olamaz.")
        if any(g.lower() == ad_temiz.lower() for g in self.gorevler[tur_anahtar]):
            raise SistemHatasi(f"'{ad_temiz}' bu personel türü için zaten tanımlı.")
        self.gorevler[tur_anahtar].append(ad_temiz)

    def gorevler_listesi(self, tur: str) -> list:
        return list(self.gorevler.get(tur.strip().lower(), []))

    def kullanici_ekle(self, kullanici) -> None:
        for k in self.kullanicilar:
            if k.tc_no == kullanici.tc_no:
                raise SistemHatasi("Bu TC kimlik no ile kayıtlı bir kullanıcı var.")
            if k.kullanici_adi == kullanici.kullanici_adi:
                raise SistemHatasi("Bu kullanıcı adı zaten alınmış.")
            if k.eposta == kullanici.eposta:
                raise SistemHatasi("Bu e-posta ile kayıtlı bir kullanıcı var.")
        if kullanici.kayitli_mi and not kullanici.sifre_var_mi:
            # Yönetici panelinden eklenen personel hemen giriş yapabilsin: ilk şifre atanır
            kullanici.sifre_belirle(Sifre.olustur(VARSAYILAN_SIFRE))
        # Doktor uzmanlığını otomatik olarak görev listesine ekle
        if isinstance(kullanici, Doktor) and kullanici.uzmanlik:
            if not any(g.lower() == kullanici.uzmanlik.lower() for g in self.gorevler.get("doktor", [])):
                self.gorevler["doktor"].append(kullanici.uzmanlik)
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
                r.hasta = yeni

    # ---- Hastane / klinik düzenleme ve silme ----
    def hastane_guncelle(self, hastane, ad, acilis, kapanis) -> None:
        """Hastane adı ve çalışma saatlerini günceller; gelecekteki randevuları bozmamalıdır."""
        if hastane not in self.kurum.hastaneler:
            raise SistemHatasi("Hastane kurumda kayıtlı değil.")
        if self.kurum.ad_kullanilmis_mi(ad, haric=hastane):
            raise SistemHatasi(f"'{ad.strip()}' adlı başka bir hastane zaten var.")
        simdi = self.sistem.simdi()
        for r in self.sistem.randevular:
            disarida = not (acilis <= r.baslangic.time() and r.bitis.time() <= kapanis)
            if r.hastane is hastane and r.aktif_mi and r.bitis > simdi and disarida:
                raise SistemHatasi(
                    "Yeni çalışma saatleri dışında kalan aktif randevu var; önce o randevuları iptal edin.")
        hastane.duzenle(ad, acilis, kapanis)

    def klinik_sil(self, hastane, klinik) -> None:
        """Kliniği kapatır: personel bağlantıları kalkar, o kliniğe ait randevu kayıtları silinir."""
        if klinik not in hastane.klinikler:
            raise SistemHatasi("Klinik bu hastaneye ait değil.")
        if self.sistem.gelecek_aktif_randevu_var_mi(lambda r: r.klinik is klinik):
            raise SistemHatasi("Bu klinikte aktif randevu var; önce randevuları iptal/reddedin.")
        self._klinik_kapat(hastane, klinik)

    def hastane_sil(self, hastane) -> None:
        """Hastaneyi tüm klinikleriyle birlikte kaldırır."""
        if hastane not in self.kurum.hastaneler:
            raise SistemHatasi("Hastane kurumda kayıtlı değil.")
        if self.sistem.gelecek_aktif_randevu_var_mi(lambda r: r.hastane is hastane):
            raise SistemHatasi("Bu hastanede aktif randevu var; önce randevuları iptal/reddedin.")
        for klinik in hastane.klinikler:
            self._klinik_kapat(hastane, klinik)
        self.kurum.hastane_cikar(hastane)
        for kisi in self.kullanicilar:
            kisi.birim_kaldirildi(hastane)

    def hizmet_sil(self, hastane, klinik, hizmet) -> None:
        """Kliniğe ait bir hizmeti siler."""
        if hastane not in self.kurum.hastaneler:
            raise SistemHatasi("Hastane kurumda kayıtlı değil.")
        if klinik not in hastane.klinikler:
            raise SistemHatasi("Klinik bu hastaneye ait değil.")
        if hizmet not in klinik.hizmetler:
            raise SistemHatasi("Hizmet bu klinikte kayıtlı değil.")
        if self.sistem.gelecek_aktif_randevu_var_mi(lambda r: r.klinik is klinik and r.hizmet is hizmet):
            raise SistemHatasi("Bu hizmet için aktif randevu var; önce randevuları iptal/reddedin.")
        klinik.hizmet_cikar(hizmet)
        self.sistem.randevulari_sil(lambda r: r.klinik is klinik and r.hizmet is hizmet)

    def _klinik_kapat(self, hastane, klinik) -> None:
        self.sistem.randevulari_sil(lambda r: r.klinik is klinik)
        hastane.klinik_cikar(klinik)
        klinik.kapat()
        for kisi in self.kullanicilar:
            kisi.birim_kaldirildi(klinik)
