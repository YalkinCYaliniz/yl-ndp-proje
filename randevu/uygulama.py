"""Uygulamanın tüm verisini tek yerde tutar ve örnek veri üretir."""
from datetime import datetime, time

from randevu.hatalar import SistemHatasi
from randevu.guvenlik import Sifre
from randevu.kullanici import (Hasta, Misafir, Doktor, Yonetici, Asistan, Hemsire,
                               Teknisyen)

VARSAYILAN_SIFRE = "123456"      # demo: tüm örnek kullanıcıların şifresi
from randevu.kurum import Kurum, Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.randevu import RandevuSistemi


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


def calisma_ekle(doktor, gunler, bloklar=((9, 12), (13, 16))):
    """Doktora Ekim 2026'daki verilen günler için çalışma blokları ekler."""
    for gun in gunler:
        for baslangic, bitis in bloklar:
            doktor.musaitlik_ekle(datetime(2026, 10, gun, baslangic, 0),
                                  datetime(2026, 10, gun, bitis, 0))


def ornek_veri() -> Uygulama:
    uyg = Uygulama()

    # ---------------- Kullanıcılar ----------------
    # İlk yedi kişinin sırası sabit (testler ve alışkanlık için)
    admin = Yonetici("Mehmet", "Kaya", "11111111111")
    ali = Hasta("Ali", "Demir", "10987654321")
    veli = Hasta("Veli", "Can", "22222222222")
    ayse = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
    can = Doktor("Can", "Öztürk", "55555555555", "Kardiyoloji")
    elif_ = Asistan("Elif", "Aydın", "66666666666")
    zeynep = Hemsire("Zeynep", "Acar", "77777777777", "Hemşirelik")

    seda = Yonetici("Seda", "Güler", "90000000001")
    # Doktorlar
    selin = Doktor("Selin", "Karaca", "90000000002", "Göz Hastalıkları")
    murat = Doktor("Murat", "Yıldız", "90000000003", "Radyoloji")
    deniz = Doktor("Deniz", "Arslan", "90000000004", "Dahiliye")
    burcu = Doktor("Burcu", "Kaya", "90000000005", "Ortopedi")
    emre = Doktor("Emre", "Çelik", "90000000006", "Çocuk Sağlığı")
    hakan = Doktor("Hakan", "Demirci", "90000000007", "Kardiyoloji")
    aylin = Doktor("Aylin", "Tekin", "90000000008", "Nöroloji")
    # Asistanlar
    burak = Asistan("Burak", "Şen", "90000000009")
    gizem = Asistan("Gizem", "Aksoy", "90000000010")
    okan = Asistan("Okan", "Polat", "90000000011")
    # Hemşire ve teknisyenler
    merve = Hemsire("Merve", "Koç", "90000000012", "Hemşirelik")
    hatice = Hemsire("Hatice", "Uslu", "90000000013", "Hemşirelik")
    can_er = Teknisyen("Can", "Er", "90000000014", "Radyoloji", "MR Cihazı")
    ece = Teknisyen("Ece", "Sönmez", "90000000015", "Laboratuvar", "Analiz Cihazı")
    # Hastalar
    ayten = Hasta("Ayten", "Yurt", "90000000016")
    kemal = Hasta("Kemal", "Tunç", "90000000017")
    selma = Hasta("Selma", "Bulut", "90000000018")
    oguz = Hasta("Oğuz", "Eren", "90000000019")
    derya = Asistan("Derya", "Kurt", "90000000020")     # Can'ın ikinci asistanı

    demo_sifre = Sifre.olustur(VARSAYILAN_SIFRE)    # herkes için aynı (demo)
    for k in (admin, ali, veli, ayse, can, elif_, zeynep, seda, selin, murat, deniz, burcu,
              emre, hakan, aylin, burak, gizem, okan, merve, hatice, can_er, ece,
              ayten, kemal, selma, oguz, derya):
        k.sifre_belirle(demo_sifre)
        uyg.kullanici_ekle(k)

    # ---------------- Hastaneler ve klinikler ----------------
    merkez = Hastane("Merkez Hastane", time(8, 0), time(17, 0))
    kadikoy = Hastane("Kadıköy Hastane", time(9, 0), time(18, 0))
    anadolu = Hastane("Anadolu Tıp Merkezi", time(7, 0), time(20, 0))
    for h in (merkez, kadikoy, anadolu):
        admin.hastane_ekle(uyg.kurum, h)

    def klinik(hastane, ad):
        k = Klinik(ad)
        admin.klinik_ekle(hastane, k)
        return k

    dahiliye = klinik(merkez, "Dahiliye")
    kardiyoloji = klinik(merkez, "Kardiyoloji")
    goz = klinik(merkez, "Göz Hastalıkları")
    radyoloji = klinik(merkez, "Radyoloji")
    k_dahiliye = klinik(kadikoy, "Dahiliye")
    ortopedi = klinik(kadikoy, "Ortopedi")
    cocuk = klinik(kadikoy, "Çocuk Sağlığı")
    lab = klinik(kadikoy, "Laboratuvar")
    a_kardiyoloji = klinik(anadolu, "Kardiyoloji")
    noroloji = klinik(anadolu, "Nöroloji")
    a_radyoloji = klinik(anadolu, "Radyoloji")

    # ---------------- Hizmetler (kliniğe bağlı) ----------------
    hizmetler = [
        (dahiliye, Muayene("Genel Muayene", 30, 500.0)),
        (kardiyoloji, Radyoloji("EKG", 30, 400.0, cihaz_ucreti=300.0)),
        (kardiyoloji, Laboratuvar("Kolesterol Tahlili", 15, 100.0, tahlil_sayisi=3)),
        (goz, Muayene("Göz Muayenesi", 20, 450.0)),
        (goz, Radyoloji("Görme Alanı Testi", 20, 150.0, cihaz_ucreti=100.0)),
        (radyoloji, Radyoloji("Röntgen", 15, 200.0, cihaz_ucreti=150.0)),
        (radyoloji, Radyoloji("Ultrason", 30, 300.0, cihaz_ucreti=200.0)),
        (radyoloji, Radyoloji("MR", 45, 800.0, cihaz_ucreti=1200.0)),
        (k_dahiliye, Muayene("Genel Muayene", 30, 450.0)),
        (ortopedi, Muayene("Ortopedi Muayenesi", 30, 600.0)),
        (ortopedi, Radyoloji("Röntgen", 15, 200.0, cihaz_ucreti=150.0)),
        (cocuk, Muayene("Çocuk Muayenesi", 20, 400.0)),
        (cocuk, Muayene("Aşı Takibi", 15, 250.0)),
        (lab, Laboratuvar("Tam Kan Tahlili", 15, 100.0, tahlil_sayisi=3)),
        (lab, Laboratuvar("İdrar Tahlili", 10, 60.0, tahlil_sayisi=1)),
        (a_kardiyoloji, Muayene("Kardiyoloji Muayenesi", 30, 700.0)),
        (a_kardiyoloji, Radyoloji("Efor Testi", 45, 500.0, cihaz_ucreti=400.0)),
        (noroloji, Muayene("Nöroloji Muayenesi", 30, 650.0)),
        (noroloji, Radyoloji("EEG", 40, 400.0, cihaz_ucreti=500.0)),
        (a_radyoloji, Radyoloji("BT", 30, 600.0, cihaz_ucreti=900.0)),
        (a_radyoloji, Radyoloji("MR", 45, 800.0, cihaz_ucreti=1200.0)),
    ]
    for kl, hizmet in hizmetler:
        admin.hizmet_ekle(kl, hizmet)

    # ---------------- Personel -> klinik atamaları ----------------
    atamalar = [
        (dahiliye, [ayse, elif_, zeynep]),
        (kardiyoloji, [ayse, can, burak, derya]),
        (goz, [selin]),
        (radyoloji, [murat, can_er]),
        (k_dahiliye, [deniz]),
        (ortopedi, [burcu, gizem]),
        (cocuk, [emre, merve]),
        (lab, [ece]),
        (a_kardiyoloji, [can, hakan, hatice]),
        (noroloji, [aylin, okan]),
        (a_radyoloji, [murat]),
    ]
    for kl, kisiler in atamalar:
        for kisi in kisiler:
            admin.personel_ata(kl, kisi)

    # ---------------- Asistan -> doktor bağlantıları ----------------
    for asistan, doktor in ((elif_, ayse), (burak, can), (derya, can), (gizem, burcu),
                           (okan, aylin)):
        admin.asistan_bagla(asistan, doktor)

    # ---------------- Doktor çalışma günleri ----------------
    calisma_ekle(ayse, (28, 29, 30))
    calisma_ekle(can, (28, 29, 30), ((10, 14),))
    calisma_ekle(selin, (28, 29, 30, 31), ((9, 12), (13, 15)))
    calisma_ekle(murat, (28, 29, 30), ((9, 13), (14, 17)))
    calisma_ekle(deniz, (28, 29, 30), ((10, 13), (14, 17)))
    calisma_ekle(burcu, (28, 29, 30, 31))
    calisma_ekle(emre, (28, 29, 30), ((9, 12), (13, 17)))
    calisma_ekle(hakan, (28, 29, 30), ((8, 12), (14, 18)))
    calisma_ekle(aylin, (29, 30, 31), ((9, 12), (13, 16)))
    return uyg
