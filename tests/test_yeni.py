"""Doktor hizmetleri, arama, en yakın boş randevu, reçete ve genişletilmiş örnek veri testleri."""
import os
import tempfile
import unittest
from datetime import date, datetime

import app as uygulama_modulu
from randevu.arama import Arama, sadelestir
from randevu.depo import Depo
from randevu.hatalar import RandevuHatasi, SistemHatasi, YetkiHatasi
from randevu.kullanici import Doktor, Asistan, Hemsire
from randevu.kurum import Klinik, Muayene
from randevu.ornek_veri import ornek_veri
from randevu.recete import Recete
from randevu.uygulama import VARSAYILAN_SIFRE
from tests.test_model import TemelTest


class DoktorHizmetTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.kontrol = Muayene("Kontrol", 15, 250.0)
        self.admin.hizmet_ekle(self.dahiliye, self.kontrol)

    def test_varsayilan_kliniğin_tum_hizmetleri(self):
        self.assertEqual(self.doktor.sunulan_hizmetler(self.dahiliye), [self.muayene, self.kontrol])
        self.assertIsNone(self.doktor.ozel_hizmetler(self.dahiliye))

    def test_secim_sonrasi_sadece_secilenler(self):
        self.doktor.hizmetlerimi_sec(self.dahiliye, [self.kontrol])
        self.assertEqual(self.doktor.sunulan_hizmetler(self.dahiliye), [self.kontrol])
        self.assertFalse(self.doktor.hizmet_sunar_mi(self.dahiliye, self.muayene))
        self.assertEqual(self.doktor.hizmetler, [self.kontrol, self.ekg])   # diğer klinik varsayılan

    def test_secilmeyen_hizmete_randevu_alinamaz(self):
        self.doktor.hizmetlerimi_sec(self.dahiliye, [self.kontrol])
        with self.assertRaises(RandevuHatasi):
            self.randevu_al()           # self.muayene seçili değil
        r = self.hasta.randevu_al(self.sistem, self.merkez, self.dahiliye, self.doktor,
                                  self.kontrol, self.zaman)
        self.assertIs(r.hizmet, self.kontrol)

    def test_dogrulamalar(self):
        with self.assertRaises(SistemHatasi):
            self.doktor.hizmet_tanimla(self.dahiliye, [])                 # boş
        with self.assertRaises(SistemHatasi):
            self.doktor.hizmet_tanimla(self.dahiliye, [self.ekg])         # başka kliniğin hizmeti
        with self.assertRaises(SistemHatasi):
            self.doktor.hizmet_tanimla(Klinik("Başka"), [self.muayene])   # doktor orada çalışmıyor

    def test_admin_doktor_hizmeti_tanimlar_baskasi_tanimlayamaz(self):
        self.admin.doktor_hizmet_tanimla(self.doktor, self.dahiliye, [self.kontrol])
        self.assertEqual(self.doktor.sunulan_hizmetler(self.dahiliye), [self.kontrol])
        self.assertFalse(self.hasta.yetki_var_mi("doktor_hizmet_tanimla"))
        self.assertFalse(self.doktor.yetki_var_mi("doktor_hizmet_tanimla"))
        self.assertTrue(self.doktor.yetki_var_mi("hizmet_sec"))

    def test_klinikte_ayni_adli_hizmet_olmaz(self):
        with self.assertRaises(SistemHatasi):
            self.admin.hizmet_ekle(self.dahiliye, Muayene("Kontrol", 10, 100.0))


class EnYakinBosTest(TemelTest):
    def test_en_yakin_bos_ve_dolu_saati_atlar(self):
        s = self.sistem.en_yakin_bos(self.merkez, self.doktor, self.muayene, datetime(2026, 10, 14, 0, 0))
        self.assertEqual(s.baslangic, datetime(2026, 10, 14, 13, 0))
        self.randevu_al(zaman=datetime(2026, 10, 14, 13, 0))
        s = self.sistem.en_yakin_bos(self.merkez, self.doktor, self.muayene, datetime(2026, 10, 14, 0, 0))
        self.assertEqual(s.baslangic, datetime(2026, 10, 14, 13, 30))

    def test_gecmis_saatler_secilmez(self):
        s = self.sistem.en_yakin_bos(self.merkez, self.doktor, self.muayene, datetime(2026, 10, 14, 14, 10))
        self.assertEqual(s.baslangic, datetime(2026, 10, 14, 14, 30))

    def test_bos_yer_yoksa_none(self):
        self.assertIsNone(self.sistem.en_yakin_bos(
            self.merkez, self.doktor, self.muayene, datetime(2026, 10, 15, 0, 0)))


class AramaTest(unittest.TestCase):
    def setUp(self):
        self.uyg = ornek_veri()
        self.arama = Arama(self.uyg)
        self.sonra = datetime(2026, 10, 28, 0, 0)

    def test_sadelestir(self):
        self.assertEqual(sadelestir("  AYŞE Öztürk "), "ayse ozturk")

    def test_doktor_adina_gore_turkce_karaktersiz(self):
        sonuclar = self.arama.ara("ayse", self.sonra)
        self.assertTrue(sonuclar)
        self.assertTrue(all("Ayşe" in s.doktor.tam_ad or "ayse" in sadelestir(s.klinik.ad)
                            for s in sonuclar))
        self.assertIn("Ayşe Yılmaz", [s.doktor.tam_ad for s in sonuclar])

    def test_klinik_adina_gore(self):
        sonuclar = self.arama.ara("KARDİYOLOJİ", self.sonra, limit=100)
        self.assertTrue(all(s.klinik.ad == "Kardiyoloji" for s in sonuclar))
        self.assertEqual(len({s.hastane.ad for s in sonuclar}), 6)         # her hastanede var

    def test_bos_arama_sonuc_vermez(self):
        self.assertEqual(self.arama.ara("   ", self.sonra), [])
        self.assertEqual(self.arama.ara("olmayan klinik adı", self.sonra), [])

    def test_en_yakin_bos_randevu_ve_siralama(self):
        sonuclar = self.arama.ara("kardiyoloji", self.sonra, limit=100)
        zamanlar = [s.en_yakin.baslangic for s in sonuclar if s.en_yakin]
        self.assertEqual(zamanlar, sorted(zamanlar))
        ayse = [s for s in self.arama.ara("ayse yilmaz", self.sonra) if s.klinik.ad == "Dahiliye"][0]
        self.assertEqual(ayse.en_yakin.baslangic, datetime(2026, 10, 28, 9, 0))
        self.assertEqual((ayse.hastane_sira, ayse.klinik_sira, ayse.doktor_sira), (0, 0, 0))

    def test_randevu_alinca_en_yakin_degisir(self):
        ali = self.uyg.kullanicilar[1]
        ayse = self.uyg.kullanicilar[3]
        merkez = self.uyg.kurum.hastaneler[0]
        dahiliye = merkez.klinikler[0]
        ali.randevu_al(self.uyg.sistem, merkez, dahiliye, ayse, dahiliye.hizmetler[0],
                       datetime(2026, 10, 28, 9, 0))
        sonuc = [s for s in self.arama.ara("ayse yilmaz", self.sonra) if s.klinik.ad == "Dahiliye"][0]
        self.assertEqual(sonuc.en_yakin.baslangic, datetime(2026, 10, 28, 9, 30))

    def test_gecmis_tarihte_bos_randevu_yok(self):
        sonuclar = self.arama.ara("kardiyoloji", datetime(2030, 1, 1), limit=100)
        self.assertTrue(all(s.en_yakin is None for s in sonuclar))

    def test_limit(self):
        self.assertEqual(len(self.arama.ara("a", self.sonra, limit=5)), 5)


class ReceteTest(TemelTest):
    def onayli(self):
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        return r

    def test_recete_yazma_ve_hastanin_gormesi(self):
        r = self.onayli()
        recete = self.doktor.recete_yaz(r, ["Parol 500 mg", "  ", "C Vitamini"], "Bol sıvı tüketin")
        self.assertEqual(recete.ilaclar, ("Parol 500 mg", "C Vitamini"))
        self.assertIs(r.recete, recete)
        self.assertEqual(self.hasta.receteli_randevularim(self.sistem), [r])
        self.assertEqual(self.hasta2.receteli_randevularim(self.sistem), [])

    def test_sadece_onayli_randevuya(self):
        r = self.randevu_al()
        with self.assertRaises(RandevuHatasi):
            self.doktor.recete_yaz(r, ["Parol"])

    def test_sadece_kendi_hastasina(self):
        r = self.onayli()
        diger = Doktor("Diğer", "Doktor", "55555555555", "Dahiliye")
        with self.assertRaises(YetkiHatasi):
            diger.recete_yaz(r, ["Parol"])

    def test_yetkisiz_roller(self):
        self.assertFalse(Asistan("A", "B", "66666666666").yetki_var_mi("recete_yaz"))
        self.assertFalse(Hemsire("H", "S", "77777777777", "Hemşirelik").yetki_var_mi("recete_yaz"))
        self.assertFalse(self.hasta.yetki_var_mi("recete_yaz"))
        self.assertTrue(self.doktor.yetki_var_mi("recete_yaz"))

    def test_bos_recete_olmaz(self):
        r = self.onayli()
        with self.assertRaises(ValueError):
            self.doktor.recete_yaz(r, ["   "])

    def test_recete_guncellenir(self):
        r = self.onayli()
        self.doktor.recete_yaz(r, ["Parol"])
        self.doktor.recete_yaz(r, ["Aspirin"], "Güncellendi")
        self.assertEqual(r.recete.ilaclar, ("Aspirin",))
        self.assertEqual(r.recete.doktor_notu, "Güncellendi")

    def test_ilaclar_degistirilemez(self):
        recete = Recete(["Parol"])
        self.assertIsInstance(recete.ilaclar, tuple)

    def test_misafir_de_kendi_recetesini_gorur(self):
        from randevu.kullanici import Misafir
        misafir = Misafir("Gizli", "Kişi", "80000000001")
        r = misafir.randevu_al(self.sistem, self.merkez, self.dahiliye, self.doktor,
                               self.muayene, self.zaman)
        self.doktor.randevu_onayla(r)
        self.doktor.recete_yaz(r, ["Parol"])
        self.assertEqual(misafir.receteli_randevularim(self.sistem), [r])


class OrnekVeriTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uyg = ornek_veri()

    def test_6_hastane_her_birinde_10_klinik(self):
        self.assertEqual(len(self.uyg.kurum.hastaneler), 6)
        for h in self.uyg.kurum.hastaneler:
            self.assertEqual(len(h.klinikler), 10, h.ad)
            self.assertEqual(len({k.ad for k in h.klinikler}), 10, h.ad)

    def test_her_klinikte_en_az_2_doktor_ve_hizmet(self):
        for h in self.uyg.kurum.hastaneler:
            for k in h.klinikler:
                self.assertGreaterEqual(len(k.doktorlar), 2, f"{h.ad}/{k.ad}")
                self.assertGreaterEqual(len(k.hizmetler), 1, f"{h.ad}/{k.ad}")

    def test_her_doktorun_calisma_saati_var(self):
        for d in self.uyg.doktorlar():
            self.assertTrue(d.musaitlik, d.tam_ad)

    def test_personel_turleri_bol(self):
        roller = [k.rol() for k in self.uyg.kullanicilar]
        self.assertGreaterEqual(roller.count("Doktor"), 120)
        for rol, en_az in (("Asistan", 30), ("Hemşire", 15), ("Teknisyen", 8), ("Hasta", 10), ("Admin", 2)):
            self.assertGreaterEqual(roller.count(rol), en_az, rol)

    def test_benzersiz_tc_kullanici_adi_eposta(self):
        for alan in ("tc_no", "kullanici_adi", "eposta"):
            degerler = [getattr(k, alan) for k in self.uyg.kullanicilar]
            self.assertEqual(len(degerler), len(set(degerler)), alan)

    def test_coklu_klinik_ve_hizmet_kisiti_ornekleri(self):
        self.assertTrue(any(len(d.klinikler) > 1 for d in self.uyg.doktorlar()))
        kisitli = [d for d in self.uyg.doktorlar()
                   if any(d.ozel_hizmetler(k) is not None for k in d.klinikler)]
        self.assertGreater(len(kisitli), 10)

    def test_asistan_kapasitesi_asilmaz(self):
        for d in self.uyg.doktorlar():
            self.assertLessEqual(len(d.asistanlar), Doktor.MAX_ASISTAN)

    def test_baslangic_gunu_parametresi(self):
        yeni = ornek_veri(date(2027, 1, 5))
        ayse = yeni.kullanicilar[3]
        self.assertEqual(min(b for b, _ in ayse.musaitlik).date(), date(2027, 1, 5))

    def test_ilk_yedi_kullanici_sirasi_sabit(self):
        self.assertEqual([k.tam_ad for k in self.uyg.kullanicilar[:7]],
                         ["Mehmet Kaya", "Ali Demir", "Veli Can", "Ayşe Yılmaz", "Can Öztürk",
                          "Elif Aydın", "Zeynep Acar"])


class YeniDepoTest(unittest.TestCase):
    def setUp(self):
        self.depo = Depo(os.path.join(tempfile.mkdtemp(), "veri.json"))

    def test_doktor_hizmet_secimi_ve_recete_korunur(self):
        uyg = ornek_veri()
        hakan = [k for k in uyg.kullanicilar if k.tam_ad == "Hakan Demirci"][0]
        anadolu_k = uyg.kurum.hastane_bul("Anadolu Tıp Merkezi").klinik_bul("Kardiyoloji")
        self.assertEqual(len(hakan.sunulan_hizmetler(anadolu_k)), 1)
        ali, ayse = uyg.kullanicilar[1], uyg.kullanicilar[3]
        merkez = uyg.kurum.hastaneler[0]
        dahiliye = merkez.klinikler[0]
        r = ali.randevu_al(uyg.sistem, merkez, dahiliye, ayse, dahiliye.hizmetler[0],
                           datetime(2026, 10, 28, 9, 0))
        ayse.randevu_onayla(r)
        ayse.recete_yaz(r, ["Parol", "C Vitamini"], "Dinlenin")
        self.depo.kaydet(uyg)

        yeni = self.depo.yukle()
        hakan2 = [k for k in yeni.kullanicilar if k.tam_ad == "Hakan Demirci"][0]
        k2 = yeni.kurum.hastane_bul("Anadolu Tıp Merkezi").klinik_bul("Kardiyoloji")
        self.assertEqual([h.ad for h in hakan2.sunulan_hizmetler(k2)], ["Kardiyoloji Muayenesi"])
        self.assertIsNone(hakan2.ozel_hizmetler(yeni.kurum.hastane_bul("Anadolu Tıp Merkezi")
                                                .klinik_bul("Dahiliye")))
        yr = yeni.sistem.randevular[0]
        self.assertEqual(yr.recete.ilaclar, ("Parol", "C Vitamini"))
        self.assertEqual(yr.recete.doktor_notu, "Dinlenin")
        self.assertEqual(len(yeni.kullanicilar), len(uyg.kullanicilar))


class YeniArayuzTest(unittest.TestCase):
    def setUp(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()

    def giris(self, sira):
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})

    def test_arama_sonuclari(self):
        self.giris(1)
        sayfa = self.istemci.get("/panel?q=ayse").get_data(as_text=True)
        self.assertIn("En yakın boş randevu", sayfa)
        self.assertIn("Ayşe Yılmaz", sayfa)
        sayfa = self.istemci.get("/panel?q=nöroloji").get_data(as_text=True)
        self.assertIn("Nöroloji", sayfa)
        self.assertIn("Sonuç bulunamadı", self.istemci.get("/panel?q=yokboyle").get_data(as_text=True))

    def test_hizmet_secimi_doktor_secilince_gelir(self):
        self.giris(1)
        once = self.istemci.get("/panel?h=0&k=0").get_data(as_text=True)
        self.assertNotIn("Hizmet seçin", once)
        sonra = self.istemci.get("/panel?h=0&k=0&d=0").get_data(as_text=True)
        self.assertIn("Hizmet seçin", sonra)

    def test_doktor_hizmet_secimi_hasta_ekranini_etkiler(self):
        self.giris(4)       # Can (Kardiyoloji)
        can = uygulama_modulu.uyg.kullanicilar[4]
        kardiyoloji = can.klinikler[0]
        self.istemci.post("/doktor/hizmetler", data={"klinik": 0, "hizmet": ["1"]})   # sadece Kolesterol
        self.assertEqual([h.ad for h in can.sunulan_hizmetler(kardiyoloji)], ["Kolesterol Tahlili"])
        self.istemci.get("/cikis")
        self.giris(1)
        sayfa = self.istemci.get("/panel?h=0&k=1&d=0").get_data(as_text=True)
        self.assertIn("Kolesterol Tahlili", sayfa)
        self.assertNotIn("EKG ·", sayfa)

    def test_hizmet_secmeden_kaydetme_hata_verir(self):
        self.giris(3)
        ayse = uygulama_modulu.uyg.kullanicilar[3]
        self.istemci.post("/doktor/hizmetler", data={"klinik": 0})
        self.assertIsNone(ayse.ozel_hizmetler(ayse.klinikler[0]))

    def test_recete_akisi(self):
        self.giris(1)
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        self.istemci.get("/cikis")
        self.giris(3)
        self.istemci.post("/doktor/recete/0", data={"ilaclar": "Parol\nVitamin"})     # henüz onaylı değil
        self.assertIsNone(uygulama_modulu.uyg.sistem.randevular[0].recete)
        self.istemci.post("/doktor/onayla/0")
        self.assertIn("Reçete yaz", self.istemci.get("/panel").get_data(as_text=True))
        self.istemci.post("/doktor/recete/0", data={"ilaclar": "Parolmax 500\nVitamin C", "doktor_notu": "Bol su için"})
        self.istemci.get("/cikis")
        self.giris(1)
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Parolmax 500", sayfa)
        self.assertIn("Vitamin C", sayfa)
        self.assertIn("Bol su için", sayfa)
        self.istemci.get("/cikis")
        self.giris(2)       # başka hasta başkasının reçetesini görmez
        self.assertNotIn("Parolmax 500", self.istemci.get("/panel").get_data(as_text=True))

    def test_baska_doktor_recete_yazamaz(self):
        self.giris(1)
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        self.istemci.get("/cikis")
        self.giris(3)
        self.istemci.post("/doktor/onayla/0")
        self.istemci.get("/cikis")
        self.giris(4)       # Can başka doktor
        self.istemci.post("/doktor/recete/0", data={"ilaclar": "Parol"})
        self.assertIsNone(uygulama_modulu.uyg.sistem.randevular[0].recete)

    def test_ana_sayfa_isim_filtresi(self):
        sayfa = self.istemci.get("/?grup=personel&q=ayse").get_data(as_text=True)
        self.assertIn("Ayşe Yılmaz", sayfa)
        self.assertNotIn("Zeynep Acar", sayfa)

    def test_doktor_ve_admin_klinikten_asistan_ekler(self):
        # Elif şu an Ayşe'ye bağlı (Merkez / Dahiliye). Önce ayıralım, sonra doktor kendi panelinden bağlasın.
        self.giris(0)
        uyg = uygulama_modulu.uyg
        elif_ = uyg.kullanicilar[5]
        ayse = uyg.kullanicilar[3]
        asistanlar = [p for p in uygulama_modulu.personeller() if isinstance(p, Asistan)]
        self.istemci.post("/admin/asistan-ayir", data={"asistan": asistanlar.index(elif_)})
        self.assertIsNone(elif_.doktor)
        # Admin panelinde klinik=0, doktor=0 seçildiğinde Elif uygun asistanlarda görünür
        admin_sayfa = self.istemci.get("/panel?ak=0&ad=0").get_data(as_text=True)
        self.assertIn("Elif Aydın", admin_sayfa)
        self.assertIn("Dahiliye", admin_sayfa)
        # Doktor kendi panelinden kliniğindeki boşta olan Elif'i kendine bağlar
        self.istemci.get("/cikis")
        self.giris(3)
        dr_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Kliniğimden Asistan Ekle", dr_sayfa)
        self.assertIn("Elif Aydın (Dahiliye)", dr_sayfa)
        self.istemci.post("/doktor/asistan-ekle", data={"asistan": uygulama_modulu.personeller().index(elif_)})
        self.assertIs(elif_.doktor, ayse)

    def test_yeni_sayfalar_emoji_icermez(self):
        import re
        emoji = re.compile("[\\U0001F000-\\U0001FFFF\\u2600-\\u27BF\\uFE0F\\u200D]")
        self.giris(1)
        self.assertIsNone(emoji.search(self.istemci.get("/panel?q=kardiyoloji").get_data(as_text=True)))
        self.istemci.get("/cikis")
        self.giris(3)
        self.assertIsNone(emoji.search(self.istemci.get("/panel").get_data(as_text=True)))


if __name__ == "__main__":
    unittest.main()
