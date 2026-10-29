"""Örnek veri: 6 hastane, her birinde 10 klinik, her klinikte en az 2 doktor."""
from datetime import date, datetime, time, timedelta

from randevu.guvenlik import Sifre
from randevu.kullanici import Hasta, Doktor, Yonetici, Asistan, Hemsire, Teknisyen
from randevu.kurum import Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.uygulama import Uygulama, VARSAYILAN_SIFRE

ADLAR = ["Ahmet", "Mehmet", "Mustafa", "Hasan", "Hüseyin", "İbrahim", "Ömer", "Yusuf", "Murat", "Emre",
         "Burak", "Kemal", "Serkan", "Tolga", "Volkan", "Barış", "Cem", "Onur", "Kaan", "Arda",
         "Ayşe", "Fatma", "Zeynep", "Elif", "Merve", "Esra", "Büşra", "Selin", "Derya", "Gamze",
         "Pınar", "Seda", "Tuğba", "Yasemin", "Ebru", "Nur", "Hande", "Ceren", "Dilara", "Melis"]
SOYADLAR = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Aydın", "Özdemir", "Arslan", "Doğan",
            "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek", "Polat", "Korkmaz",
            "Erdoğan", "Güneş", "Aksoy", "Avcı", "Türk", "Yavuz", "Bulut", "Tekin", "Acar", "Uçar",
            "Sezer", "Taş", "Bayrak", "Ersoy", "Karaca", "Gül", "Tuna", "Çakır", "Er", "Ateş"]

# (hastane adı, açılış, kapanış, [klinikler])
HASTANELER = [
    ("Merkez Hastane", time(8, 0), time(17, 0),
     ["Dahiliye", "Kardiyoloji", "Göz Hastalıkları", "Radyoloji", "Ortopedi", "Nöroloji",
      "Kulak Burun Boğaz", "Genel Cerrahi", "Dermatoloji", "Üroloji"]),
    ("Kadıköy Hastane", time(9, 0), time(18, 0),
     ["Dahiliye", "Ortopedi", "Çocuk Sağlığı", "Laboratuvar", "Kardiyoloji", "Göz Hastalıkları",
      "Dermatoloji", "Kadın Hastalıkları", "Psikiyatri", "Fizik Tedavi"]),
    ("Anadolu Tıp Merkezi", time(7, 0), time(20, 0),
     ["Kardiyoloji", "Nöroloji", "Radyoloji", "Dahiliye", "Göğüs Hastalıkları", "Endokrinoloji",
      "Gastroenteroloji", "Üroloji", "Genel Cerrahi", "Çocuk Sağlığı"]),
    ("Şişli Şehir Hastanesi", time(8, 0), time(18, 0),
     ["Dahiliye", "Kardiyoloji", "Radyoloji", "Laboratuvar", "Ortopedi", "Nöroloji",
      "Göz Hastalıkları", "Kulak Burun Boğaz", "Psikiyatri", "Dermatoloji"]),
    ("Çankaya Hastanesi", time(8, 0), time(17, 0),
     ["Dahiliye", "Çocuk Sağlığı", "Kadın Hastalıkları", "Genel Cerrahi", "Üroloji", "Kardiyoloji",
      "Radyoloji", "Fizik Tedavi", "Endokrinoloji", "Gastroenteroloji"]),
    ("Konak Hastanesi", time(7, 0), time(19, 0),
     ["Dahiliye", "Kardiyoloji", "Ortopedi", "Göğüs Hastalıkları", "Göz Hastalıkları", "Laboratuvar",
      "Nöroloji", "Kulak Burun Boğaz", "Çocuk Sağlığı", "Psikiyatri"]),
]

# Hizmet tanımı: (tür, ad, süre dk, ücret, ekstra) ekstra: cihaz ücreti ya da tahlil sayısı
HIZMET_SABLONLARI = {
    "Dahiliye": [("muayene", "Genel Muayene", 30, 480)],
    "Kardiyoloji": [("muayene", "Kardiyoloji Muayenesi", 30, 700), ("radyoloji", "EKG", 30, 400, 300)],
    "Göz Hastalıkları": [("muayene", "Göz Muayenesi", 20, 450), ("radyoloji", "Görme Alanı Testi", 20, 150, 100)],
    "Radyoloji": [("radyoloji", "Röntgen", 15, 200, 150), ("radyoloji", "Ultrason", 30, 300, 200)],
    "Ortopedi": [("muayene", "Ortopedi Muayenesi", 30, 600), ("radyoloji", "Röntgen", 15, 200, 150)],
    "Çocuk Sağlığı": [("muayene", "Çocuk Muayenesi", 20, 400), ("muayene", "Aşı Takibi", 15, 250)],
    "Laboratuvar": [("laboratuvar", "Tam Kan Tahlili", 15, 100, 3), ("laboratuvar", "İdrar Tahlili", 10, 60, 1)],
    "Nöroloji": [("muayene", "Nöroloji Muayenesi", 30, 650), ("radyoloji", "EEG", 40, 400, 500)],
    "Kulak Burun Boğaz": [("muayene", "KBB Muayenesi", 20, 450), ("radyoloji", "İşitme Testi", 20, 150, 100)],
    "Genel Cerrahi": [("muayene", "Cerrahi Muayenesi", 30, 600), ("radyoloji", "Ultrason", 30, 300, 200)],
    "Dermatoloji": [("muayene", "Dermatoloji Muayenesi", 20, 450), ("laboratuvar", "Alerji Testi", 30, 120, 3)],
    "Üroloji": [("muayene", "Üroloji Muayenesi", 30, 550), ("radyoloji", "İdrar Yolu Ultrasonu", 30, 300, 200)],
    "Kadın Hastalıkları": [("muayene", "Kadın Doğum Muayenesi", 30, 550), ("radyoloji", "Ultrason", 30, 300, 200)],
    "Psikiyatri": [("muayene", "Psikiyatri Görüşmesi", 45, 700), ("muayene", "Psikolojik Test", 40, 300)],
    "Göğüs Hastalıkları": [("muayene", "Göğüs Muayenesi", 30, 550), ("radyoloji", "Solunum Fonksiyon Testi", 30, 250, 200)],
    "Fizik Tedavi": [("muayene", "Fizik Tedavi Muayenesi", 30, 450), ("muayene", "Tedavi Seansı", 45, 300)],
    "Endokrinoloji": [("muayene", "Endokrinoloji Muayenesi", 30, 600), ("laboratuvar", "Hormon Tahlili", 15, 150, 4)],
    "Gastroenteroloji": [("muayene", "Gastro Muayenesi", 30, 600), ("radyoloji", "Endoskopi", 45, 900, 600)],
}

# İlk 3 hastanenin eski örnek verisindeki hizmetler (aynen korunur)
OZEL_HIZMETLER = {
    ("Merkez Hastane", "Dahiliye"): [("muayene", "Genel Muayene", 30, 500)],
    ("Merkez Hastane", "Kardiyoloji"): [("radyoloji", "EKG", 30, 400, 300),
                                        ("laboratuvar", "Kolesterol Tahlili", 15, 100, 3)],
    ("Merkez Hastane", "Radyoloji"): [("radyoloji", "Röntgen", 15, 200, 150),
                                      ("radyoloji", "Ultrason", 30, 300, 200),
                                      ("radyoloji", "MR", 45, 800, 1200)],
    ("Kadıköy Hastane", "Dahiliye"): [("muayene", "Genel Muayene", 30, 450)],
    ("Anadolu Tıp Merkezi", "Radyoloji"): [("radyoloji", "BT", 30, 600, 900),
                                           ("radyoloji", "MR", 45, 800, 1200)],
}

CIHAZLAR = {"Radyoloji": "Röntgen Cihazı", "Laboratuvar": "Analiz Cihazı",
            "Kardiyoloji": "EKG Cihazı", "Fizik Tedavi": "Fizik Tedavi Ünitesi"}
CALISMA_DESENLERI = [((9, 12), (13, 16)), ((9, 13), (14, 16)), ((10, 12), (13, 16))]


def hizmet_olustur(tanim):
    tur, ad, sure, ucret = tanim[:4]
    ekstra = tanim[4] if len(tanim) > 4 else 0
    if tur == "radyoloji":
        return Radyoloji(ad, sure, ucret, cihaz_ucreti=ekstra)
    if tur == "laboratuvar":
        return Laboratuvar(ad, sure, ucret, tahlil_sayisi=ekstra)
    return Muayene(ad, sure, ucret)


def calisma_ekle(doktor, baslangic_gunu, gunler, bloklar=((9, 12), (13, 16))):
    """Doktora başlangıç gününden itibaren verilen gün sıraları için çalışma blokları ekler."""
    for sira in gunler:
        gun = baslangic_gunu + timedelta(days=sira)
        for bas, bit in bloklar:
            doktor.musaitlik_ekle(datetime.combine(gun, time(bas)), datetime.combine(gun, time(bit)))


class IsimUretici:
    """Her seferinde daha önce kullanılmamış bir ad-soyad ve TC üretir (rastgelelik yok)."""

    def __init__(self, kullanilan_adlar):
        self._kullanilan = set(kullanilan_adlar)
        self._sayac = 0
        self._tc = 100

    def sonraki(self):
        while True:
            ad = ADLAR[self._sayac % len(ADLAR)]
            soyad = SOYADLAR[(self._sayac * 7 + self._sayac // len(ADLAR)) % len(SOYADLAR)]
            self._sayac += 1
            anahtar = f"{ad}.{soyad}".translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")).lower()
            if anahtar not in self._kullanilan:
                self._kullanilan.add(anahtar)
                self._tc += 1
                return ad, soyad, f"9{self._tc:010d}"


def ornek_veri(baslangic_gunu: date = date(2026, 10, 28)) -> Uygulama:
    uyg = Uygulama()

    # ---------------- Elle tanımlanan kullanıcılar (sıraları sabit) ----------------
    admin = Yonetici("Mehmet", "Kaya", "11111111111")
    ali = Hasta("Ali", "Demir", "10987654321")
    veli = Hasta("Veli", "Can", "22222222222")
    ayse = Doktor("Ayşe", "Yılmaz", "12345678901", "Dahiliye")
    can = Doktor("Can", "Öztürk", "55555555555", "Kardiyoloji")
    elif_ = Asistan("Elif", "Aydın", "66666666666")
    zeynep = Hemsire("Zeynep", "Acar", "77777777777", "Hemşirelik")
    seda = Yonetici("Seda", "Güler", "90000000001")
    selin = Doktor("Selin", "Karaca", "90000000002", "Göz Hastalıkları")
    murat = Doktor("Murat", "Yıldız", "90000000003", "Radyoloji")
    deniz = Doktor("Deniz", "Arslan", "90000000004", "Dahiliye")
    burcu = Doktor("Burcu", "Kaya", "90000000005", "Ortopedi")
    emre = Doktor("Emre", "Çelik", "90000000006", "Çocuk Sağlığı")
    hakan = Doktor("Hakan", "Demirci", "90000000007", "Kardiyoloji")
    aylin = Doktor("Aylin", "Tekin", "90000000008", "Nöroloji")
    burak = Asistan("Burak", "Şen", "90000000009")
    gizem = Asistan("Gizem", "Aksoy", "90000000010")
    okan = Asistan("Okan", "Polat", "90000000011")
    merve = Hemsire("Merve", "Koç", "90000000012", "Hemşirelik")
    hatice = Hemsire("Hatice", "Uslu", "90000000013", "Hemşirelik")
    can_er = Teknisyen("Can", "Er", "90000000014", "Radyoloji", "MR Cihazı")
    ece = Teknisyen("Ece", "Sönmez", "90000000015", "Laboratuvar", "Analiz Cihazı")
    ayten = Hasta("Ayten", "Yurt", "90000000016")
    kemal = Hasta("Kemal", "Tunç", "90000000017")
    selma = Hasta("Selma", "Bulut", "90000000018")
    oguz = Hasta("Oğuz", "Eren", "90000000019")
    derya = Asistan("Derya", "Kurt", "90000000020")     # Can'ın ikinci asistanı

    demo_sifre = Sifre.olustur(VARSAYILAN_SIFRE)        # herkes için aynı (demo)

    def kullanici_ekle(k):
        k.sifre_belirle(demo_sifre)
        uyg.kullanici_ekle(k)

    for k in (admin, ali, veli, ayse, can, elif_, zeynep, seda, selin, murat, deniz, burcu,
              emre, hakan, aylin, burak, gizem, okan, merve, hatice, can_er, ece,
              ayten, kemal, selma, oguz, derya):
        kullanici_ekle(k)
    uretici = IsimUretici([k.kullanici_adi for k in uyg.kullanicilar])

    # ---------------- Hastaneler, klinikler, hizmetler ----------------
    klinikler = {}                  # (hastane adı, klinik adı) -> Klinik
    for hastane_adi, acilis, kapanis, klinik_adlari in HASTANELER:
        hastane = Hastane(hastane_adi, acilis, kapanis)
        admin.hastane_ekle(uyg.kurum, hastane)
        for klinik_adi in klinik_adlari:
            klinik = Klinik(klinik_adi)
            admin.klinik_ekle(hastane, klinik)
            klinikler[(hastane_adi, klinik_adi)] = klinik
            tanimlar = OZEL_HIZMETLER.get((hastane_adi, klinik_adi)) or HIZMET_SABLONLARI[klinik_adi]
            for tanim in tanimlar:
                admin.hizmet_ekle(klinik, hizmet_olustur(tanim))
    # ---------------- Elle yapılan personel atamaları ----------------
    atamalar = {
        ("Merkez Hastane", "Dahiliye"): [ayse, elif_, zeynep],
        ("Merkez Hastane", "Kardiyoloji"): [can, burak, derya],
        ("Merkez Hastane", "Göz Hastalıkları"): [selin],
        ("Merkez Hastane", "Radyoloji"): [murat, can_er],
        ("Kadıköy Hastane", "Dahiliye"): [ayse, deniz],
        ("Kadıköy Hastane", "Ortopedi"): [burcu, gizem],
        ("Kadıköy Hastane", "Çocuk Sağlığı"): [emre, merve],
        ("Kadıköy Hastane", "Laboratuvar"): [ece],
        ("Anadolu Tıp Merkezi", "Kardiyoloji"): [can, hakan, hatice],
        ("Anadolu Tıp Merkezi", "Nöroloji"): [aylin, okan],
        ("Anadolu Tıp Merkezi", "Radyoloji"): [murat],
    }
    for anahtar, kisiler in atamalar.items():
        for kisi in kisiler:
            admin.personel_ata(klinikler[anahtar], kisi)
    for asistan, doktor in ((elif_, ayse), (burak, can), (derya, can), (gizem, burcu), (okan, aylin)):
        admin.asistan_bagla(asistan, doktor)

    # Doktor bazlı hizmet tanımı: Hakan sadece muayene verir, Can'ın tüm hizmetleri
    anadolu_kardiyoloji = klinikler[("Anadolu Tıp Merkezi", "Kardiyoloji")]
    admin.doktor_hizmet_tanimla(hakan, anadolu_kardiyoloji, [anadolu_kardiyoloji.hizmetler[0]])

    # ---------------- Çalışma günleri (elle tanımlı doktorlar) ----------------
    calisma_ekle(ayse, baslangic_gunu, (0, 1, 2))
    calisma_ekle(can, baslangic_gunu, (0, 1, 2), ((10, 14),))
    calisma_ekle(selin, baslangic_gunu, (0, 1, 2, 3), ((9, 12), (13, 15)))
    calisma_ekle(murat, baslangic_gunu, (0, 1, 2), ((9, 13), (14, 17)))
    calisma_ekle(deniz, baslangic_gunu, (0, 1, 2), ((10, 13), (14, 17)))
    calisma_ekle(burcu, baslangic_gunu, (0, 1, 2, 3))
    calisma_ekle(emre, baslangic_gunu, (0, 1, 2), ((9, 12), (13, 17)))
    calisma_ekle(hakan, baslangic_gunu, (0, 1, 2), ((8, 12), (14, 18)))
    calisma_ekle(aylin, baslangic_gunu, (1, 2, 3))

    # ---------------- Üretilen personel: her klinikte en az 2 doktor ----------------
    uretilen_doktor = 0
    for hastane_adi, _, _, klinik_adlari in HASTANELER:
        for sira, klinik_adi in enumerate(klinik_adlari):
            klinik = klinikler[(hastane_adi, klinik_adi)]
            elle_tanimli = (hastane_adi, klinik_adi) in atamalar
            hedef = 3 if klinik_adi in ("Dahiliye", "Çocuk Sağlığı") else 2
            while len(klinik.doktorlar) < hedef:
                ad, soyad, tc = uretici.sonraki()
                doktor = Doktor(ad, soyad, tc, klinik_adi)
                kullanici_ekle(doktor)
                admin.personel_ata(klinik, doktor)
                desen = CALISMA_DESENLERI[uretilen_doktor % len(CALISMA_DESENLERI)]
                calisma_ekle(doktor, baslangic_gunu, range(5), desen)
                if len(klinik.doktorlar) == 2 and len(klinik.hizmetler) > 1:
                    # ikinci doktor sadece ilk hizmeti verir (doktor bazlı hizmet örneği)
                    admin.doktor_hizmet_tanimla(doktor, klinik, [klinik.hizmetler[0]])
                if not elle_tanimli and uretilen_doktor % 3 == 0:
                    ad, soyad, tc = uretici.sonraki()
                    asistan = Asistan(ad, soyad, tc)
                    kullanici_ekle(asistan)
                    admin.personel_ata(klinik, asistan)
                    admin.asistan_bagla(asistan, doktor)
                uretilen_doktor += 1
            if not elle_tanimli:
                # hemşireler: 4., 6. ve 8. kliniklerde, bir sonraki klinikle birlikte
                if sira in (4, 6, 8):
                    ad, soyad, tc = uretici.sonraki()
                    hemsire = Hemsire(ad, soyad, tc, "Hemşirelik")
                    kullanici_ekle(hemsire)
                    admin.personel_ata(klinik, hemsire)
                    admin.personel_ata(klinikler[(hastane_adi, klinik_adlari[sira + 1])], hemsire)
                if klinik_adi in CIHAZLAR:
                    ad, soyad, tc = uretici.sonraki()
                    teknisyen = Teknisyen(ad, soyad, tc, klinik_adi, CIHAZLAR[klinik_adi])
                    kullanici_ekle(teknisyen)
                    admin.personel_ata(klinik, teknisyen)

    # ---------------- Üretilen hastalar ----------------
    for _ in range(10):
        ad, soyad, tc = uretici.sonraki()
        kullanici_ekle(Hasta(ad, soyad, tc))
    return uyg
