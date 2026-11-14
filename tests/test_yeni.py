import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta

import app as uygulama_modulu
from randevu.arama import Arama, sadelestir
from randevu.depo import Depo
from randevu.hatalar import RandevuHatasi, SistemHatasi, YetkiHatasi
from randevu.kullanici import (Doktor, Asistan, Hemsire, Teknisyen,
                               HastaneYoneticisi, KlinikYoneticisi, Hasta, Yonetici)
from randevu.kurum import Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.ornek_veri import ornek_veri
from randevu.recete import Recete
from randevu.randevu import Randevu, RandevuDurumu
from randevu.odeme import NakitOdeme
from randevu.uygulama import Uygulama, VARSAYILAN_SIFRE
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
        r.hasta_kabul_et(None, odeme=NakitOdeme())      # reçete için hasta gelmiş olmalı
        return r

    def test_recete_hasta_gelmeden_yazilamaz(self):
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        with self.assertRaises(RandevuHatasi):
            self.doktor.recete_yaz(r, ["Parol"])

    def test_odenmemis_randevu_odeme_almadan_kabul_edilemez(self):
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        with self.assertRaises(RandevuHatasi):
            r.hasta_kabul_et(None)
        self.assertFalse(r.kabul_edildi_mi)
        r.hasta_kabul_et(None, odeme=NakitOdeme())
        self.assertTrue(r.kabul_edildi_mi)
        self.assertTrue(r.odendi_mi)

    def test_odenmis_randevu_direkt_kabul_edilir(self):
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        r.odeme_yap(NakitOdeme())
        r.hasta_kabul_et(None)
        self.assertTrue(r.kabul_edildi_mi)

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
        r.hasta_kabul_et(None, odeme=NakitOdeme())
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
        r.hasta_kabul_et(None, odeme=NakitOdeme())
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


class TeslimDuzeltmeleriTest(TemelTest):
    """Teslim öncesi bulunan hataların düzeltmelerini doğrular."""

    def test_gecersiz_hizmet_kaydedilemez(self):
        with self.assertRaises(ValueError):
            Muayene("Sıfır süre", 0, 100.0)
        with self.assertRaises(ValueError):
            Muayene("Negatif ücret", 30, -500.0)
        with self.assertRaises(ValueError):
            Radyoloji("R", 30, 100.0, cihaz_ucreti=-1)
        with self.assertRaises(ValueError):
            Laboratuvar("L", 15, 100.0, tahlil_sayisi=0)

    def test_acilis_kapanistan_once_olmali(self):
        from datetime import time
        with self.assertRaises(ValueError):
            Hastane("Ters", time(17, 0), time(8, 0))

    def test_ayni_adli_hastane_ve_klinik_olmaz(self):
        from datetime import time
        with self.assertRaises(SistemHatasi):
            self.admin.hastane_ekle(self.kurum, Hastane("merkez", time(8, 0), time(17, 0)))
        with self.assertRaises(SistemHatasi):
            self.admin.klinik_ekle(self.merkez, Klinik("Dahiliye"))

    def test_ayni_adli_klinik_farkli_hastanede_olabilir(self):
        self.assertIsNot(self.dahiliye, self.dahiliye2)      # TemelTest'te iki hastanede de Dahiliye var

    def test_gecmis_tarihli_randevu_alinamaz(self):
        from randevu.randevu import RandevuSistemi
        sistem = RandevuSistemi(saat=lambda: datetime(2026, 10, 14, 14, 0))
        with self.assertRaises(RandevuHatasi):
            self.hasta.randevu_al(sistem, self.merkez, self.dahiliye, self.doktor,
                                  self.muayene, datetime(2026, 10, 14, 13, 30))
        r = self.hasta.randevu_al(sistem, self.merkez, self.dahiliye, self.doktor,
                                  self.muayene, datetime(2026, 10, 14, 14, 30))
        self.assertEqual(r.baslangic, datetime(2026, 10, 14, 14, 30))

    def test_musait_gunler_ve_saatler_gecmisi_gostermez(self):
        from randevu.randevu import RandevuSistemi
        sistem = RandevuSistemi(saat=lambda: datetime(2026, 10, 14, 14, 10))
        gun = datetime(2026, 10, 14).date()
        self.assertEqual(sistem.musait_gunler(self.merkez, self.doktor, self.muayene), [(gun, 1)])
        slotlar = sistem.saat_tablosu(self.merkez, self.doktor, self.muayene, gun, gecmisi_gizle=True)
        self.assertEqual([s.baslangic for s in slotlar], [datetime(2026, 10, 14, 14, 30)])
        sistem_sonra = RandevuSistemi(saat=lambda: datetime(2026, 10, 15, 8, 0))
        self.assertEqual(sistem_sonra.musait_gunler(self.merkez, self.doktor, self.muayene), [])

    def test_yeni_personel_hemen_giris_yapar(self):
        from randevu.uygulama import Uygulama
        uyg = Uygulama()
        yeni = Doktor("Yeni", "Doktor", "98765432101", "Dahiliye")
        self.admin.personel_kaydet(uyg, yeni)
        self.assertTrue(yeni.sifre_dogru_mu(VARSAYILAN_SIFRE))
        self.assertIs(uyg.kimlik_dogrula(yeni.kullanici_adi, VARSAYILAN_SIFRE), yeni)

    def test_odeme_sadece_randevu_sahibi_yapar(self):
        from randevu.odeme import NakitOdeme
        r = self.randevu_al()
        self.doktor.randevu_onayla(r)
        with self.assertRaises(YetkiHatasi):
            self.hasta2.odeme_yap(r, NakitOdeme())
        self.assertFalse(r.odendi_mi)
        self.assertEqual(self.hasta.odeme_yap(r, NakitOdeme()), 500.0)


class OdemeArayuzTest(unittest.TestCase):
    def setUp(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()

    def onayli_randevu(self):
        uyg = uygulama_modulu.uyg
        ali, ayse = uyg.kullanicilar[1], uyg.kullanicilar[3]
        merkez = uyg.kurum.hastaneler[0]
        dahiliye = merkez.klinikler[0]
        r = ali.randevu_al(uyg.sistem, merkez, dahiliye, ayse, dahiliye.hizmetler[0],
                           datetime(2026, 10, 28, 9, 0))
        ayse.randevu_onayla(r)
        return r

    def test_oturumsuz_odeme_yapilamaz(self):
        r = self.onayli_randevu()
        self.istemci.post("/hasta/odeme/0", data={"yontem": "kart"})
        self.assertFalse(r.odendi_mi)

    def test_baskasinin_randevusuna_odeme_yapilamaz(self):
        r = self.onayli_randevu()
        self.istemci.post("/giris/2", data={"sifre": VARSAYILAN_SIFRE})      # Veli
        self.istemci.post("/hasta/odeme/0", data={"yontem": "kart"})
        self.assertFalse(r.odendi_mi)
        self.istemci.get("/cikis")
        self.istemci.post("/giris/1", data={"sifre": VARSAYILAN_SIFRE})      # Ali (sahibi)
        self.istemci.post("/hasta/odeme/0", data={"yontem": "kart"})
        self.assertTrue(r.odendi_mi)

    def test_admin_panelinden_eklenen_doktor_ilk_sifreyle_girer(self):
        self.istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})
        self.istemci.post("/admin/personel", data={
            "tur": "doktor", "ad": "Taze", "soyad": "Doktor", "tc": "98765432109",
            "uzmanlik": "Dahiliye"})
        self.istemci.get("/cikis")
        cevap = self.istemci.post("/giris-kullanici", data={
            "kullanici_adi": "taze.doktor", "sifre": VARSAYILAN_SIFRE})
        self.assertEqual(cevap.status_code, 302)
        self.assertTrue(cevap.headers["Location"].endswith("/panel"))

    def test_gecersiz_hizmet_ve_saat_arayuzden_kaydedilmez(self):
        self.istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})
        uyg = uygulama_modulu.uyg
        klinik = uyg.kurum.hastaneler[0].klinikler[0]
        onceki = len(klinik.hizmetler)
        self.istemci.post("/admin/hizmet", data={
            "klinik": 0, "tur": "muayene", "ad": "Hatalı", "sure": 0, "ucret": -500})
        self.assertEqual(len(klinik.hizmetler), onceki)
        onceki_hastane = len(uyg.kurum.hastaneler)
        self.istemci.post("/admin/hastane", data={"ad": "Ters", "acilis": "17:00", "kapanis": "08:00"})
        self.assertEqual(len(uyg.kurum.hastaneler), onceki_hastane)


class SilmeDuzenlemeTest(unittest.TestCase):
    def setUp(self):
        from datetime import time
        self.time = time
        self.uyg = ornek_veri()
        self.admin = self.uyg.kullanicilar[0]
        self.merkez = self.uyg.kurum.hastaneler[0]
        self.kadikoy = self.uyg.kurum.hastaneler[1]
        self.dahiliye = self.merkez.klinik_bul("Dahiliye")
        self.ali, self.ayse = self.uyg.kullanicilar[1], self.uyg.kullanicilar[3]
        self.elif_ = self.uyg.kullanicilar[5]
        self.hastane_yon = next(k for k in self.uyg.kullanicilar
                                if isinstance(k, HastaneYoneticisi) and k.hastane is self.merkez)
        self.klinik_yon = next(k for k in self.uyg.kullanicilar
                               if isinstance(k, KlinikYoneticisi) and k.klinik is self.dahiliye)

    def randevu_al(self):
        return self.ali.randevu_al(self.uyg.sistem, self.merkez, self.dahiliye, self.ayse,
                                   self.dahiliye.hizmetler[0], datetime(2026, 10, 28, 9, 0))

    def test_klinik_sil_aktif_randevu_varken_engellenir(self):
        r = self.randevu_al()
        with self.assertRaises(SistemHatasi):
            self.admin.klinik_sil(self.uyg, self.merkez, self.dahiliye)
        self.assertIn(self.dahiliye, self.merkez.klinikler)
        self.ali.randevu_iptal(r)
        self.admin.klinik_sil(self.uyg, self.merkez, self.dahiliye)
        self.assertNotIn(self.dahiliye, self.merkez.klinikler)
        self.assertEqual(self.uyg.sistem.randevular, ())      # iptal edilmiş kayıt da temizlenir

    def test_klinik_silinince_personel_baglantisi_kalkar(self):
        self.admin.klinik_sil(self.uyg, self.merkez, self.dahiliye)
        self.assertEqual(len(self.ayse.klinikler), 1)          # Kadıköy Dahiliye kalır
        self.assertNotIn(self.dahiliye, self.ayse.klinikler)
        self.assertEqual(self.elif_.klinikler, ())
        self.assertIsNone(self.elif_.doktor)                   # ortak klinik kalmadı: doktordan ayrıldı
        self.assertNotIn(self.elif_, self.ayse.asistanlar)
        self.assertIsNone(self.klinik_yon.klinik)              # klinik yöneticisinin görevi boşa düşer

    def test_hastane_sil_ve_yonetici_baglantisi(self):
        self.admin.hastane_sil(self.uyg, self.merkez)
        self.assertNotIn(self.merkez, self.uyg.kurum.hastaneler)
        self.assertIsNone(self.hastane_yon.hastane)
        self.assertEqual(self.hastane_yon.yonetilen_klinikler(self.uyg.kurum), [])
        self.assertEqual(self.hastane_yon.yonetilebilir_kullanicilar(self.uyg), [])

    def test_hastane_silmede_aktif_randevu_engeller(self):
        self.randevu_al()
        with self.assertRaises(SistemHatasi):
            self.admin.hastane_sil(self.uyg, self.merkez)

    def test_silme_yetkileri(self):
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.hastane_sil(self.uyg, self.merkez)        # sadece genel admin
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.klinik_sil(self.uyg, self.merkez, self.dahiliye)
        with self.assertRaises(YetkiHatasi):                           # başka hastanenin kliniği
            self.hastane_yon.klinik_sil(self.uyg, self.kadikoy, self.kadikoy.klinikler[0])
        self.hastane_yon.klinik_sil(self.uyg, self.merkez, self.dahiliye)   # kendi hastanesi serbest
        self.assertNotIn(self.dahiliye, self.merkez.klinikler)

    def test_hastane_duzenle(self):
        self.admin.hastane_duzenle(self.uyg, self.merkez, "Merkez Yeni", self.time(7, 0), self.time(19, 0))
        self.assertEqual((self.merkez.ad, self.merkez.acilis, self.merkez.kapanis),
                         ("Merkez Yeni", self.time(7, 0), self.time(19, 0)))
        self.assertIs(self.uyg.kurum.hastane_bul("Merkez Yeni"), self.merkez)

    def test_hastane_duzenle_dogrulamalari(self):
        with self.assertRaises(SistemHatasi):                          # başka hastanenin adı
            self.admin.hastane_duzenle(self.uyg, self.merkez, "kadıköy hastane",
                                       self.time(8, 0), self.time(17, 0))
        with self.assertRaises(ValueError):
            self.admin.hastane_duzenle(self.uyg, self.merkez, "Merkez Hastane",
                                       self.time(17, 0), self.time(8, 0))
        self.admin.hastane_duzenle(self.uyg, self.merkez, "Merkez Hastane",   # kendi adı serbest
                                   self.time(8, 0), self.time(18, 0))
        self.assertEqual(self.merkez.ad, "Merkez Hastane")

    def test_saat_degisikligi_aktif_randevuyu_disarida_birakamaz(self):
        self.randevu_al()                                              # 09:00-09:30
        with self.assertRaises(SistemHatasi):
            self.admin.hastane_duzenle(self.uyg, self.merkez, "Merkez Hastane",
                                       self.time(10, 0), self.time(17, 0))
        self.assertEqual(self.merkez.acilis, self.time(8, 0))

    def test_duzenleme_yetkileri(self):
        self.hastane_yon.hastane_duzenle(self.uyg, self.merkez, "Merkez B", self.time(8, 0), self.time(17, 0))
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.hastane_duzenle(self.uyg, self.kadikoy, "Başka", self.time(8, 0), self.time(17, 0))
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.hastane_duzenle(self.uyg, self.merkez, "X", self.time(8, 0), self.time(17, 0))

    def test_silme_arayuzden(self):
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = istemci.get("/panel").get_data(as_text=True)
        for baslik in ("Hastaneyi düzenle", "Hastane sil", "Klinik sil"):
            self.assertIn(baslik, sayfa)
        istemci.post("/admin/hastane-duzenle", data={
            "h": 0, "ad": "Merkez Yeni", "acilis": "07:00", "kapanis": "19:00"})
        self.assertEqual(self.merkez.ad, "Merkez Yeni")
        sayi = len(self.merkez.klinikler)
        istemci.post("/admin/klinik-sil", data={"klinik": 0})
        self.assertEqual(len(self.merkez.klinikler), sayi - 1)
        istemci.post("/admin/hastane-sil", data={"h": 0})
        self.assertNotIn(self.merkez, self.uyg.kurum.hastaneler)
        # panel yeniden açılabiliyor
        self.assertEqual(istemci.get("/panel").status_code, 200)
        # klinik yöneticisi bu kartları görmez
        istemci.get("/cikis")
        yon = self.klinik_yon
        yeni_klinik_yon = next(k for k in self.uyg.kullanicilar
                               if isinstance(k, KlinikYoneticisi) and k.klinik is not None)
        istemci.post(f"/giris/{self.uyg.kullanicilar.index(yeni_klinik_yon)}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = istemci.get("/panel").get_data(as_text=True)
        for baslik in ("Hastaneyi düzenle", "Hastane sil", "Klinik sil"):
            self.assertNotIn(baslik, sayfa)

    def test_asistan_secilince_ayni_hastanedeki_doktorlar_siralanir(self):
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})
        # Elif Aydın (sira 0) Merkez Hastane / Dahiliye asistanı -> Merkez Hastane doktorları (Ayşe Yılmaz) en başta olmalı
        sayfa = istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Doktor:", sayfa)
        self.assertNotIn("asistanla aynı hastanedekiler üstte sıralanır", sayfa)
        # bagla_doktor_secim içindeki ilk option Ayşe Yılmaz (Merkez Dahiliye) olmalı
        self.assertIn('data-hastaneler="Merkez Hastane"', sayfa)
        # Kadıköy Hastanesi'nde olan asistan Gizem Aksoy (Ortopedi) seçilince:
        asistanlar = [p for p in uygulama_modulu.personeller() if isinstance(p, Asistan)]
        gizem_sira = next(i for i, a in enumerate(asistanlar) if a.tam_ad == "Gizem Aksoy")
        sayfa_gizem = istemci.get(f"/panel?as={gizem_sira}").get_data(as_text=True)
        # Kadıköy'deki doktor (Burcu Kaya) en başta sıralanmalı
        secim_bolumu = sayfa_gizem.split('id="bagla_doktor_secim"')[1].split('</select>')[0]
        ilk_option = secim_bolumu.split('<option')[1]
        self.assertIn("Burcu Kaya", ilk_option)


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
        self.assertNotIn("Reçete yaz", self.istemci.get("/panel").get_data(as_text=True))   # hasta gelmeden yok
        self.istemci.post("/doktor/recete/0", data={"ilaclar": "Parol"})
        self.assertIsNone(uygulama_modulu.uyg.sistem.randevular[0].recete)
        uygulama_modulu.uyg.sistem.randevular[0].hasta_kabul_et(None, odeme=NakitOdeme())
        self.assertIn("Kabul Edilen Hastalar", self.istemci.get("/panel").get_data(as_text=True))
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

    def test_hastane_ve_klinik_yoneticisi_panelleri(self):
        uyg = uygulama_modulu.uyg
        h_yon = next(k for k in uyg.kullanicilar if isinstance(k, HastaneYoneticisi))
        k_yon = next(k for k in uyg.kullanicilar if isinstance(k, KlinikYoneticisi))
        self.giris(uyg.kullanicilar.index(h_yon))
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Hastane Yöneticisi", sayfa)
        self.assertNotIn("Hastane ekle", sayfa)
        self.assertIn("Klinik ekle", sayfa)
        self.istemci.get("/cikis")
        self.giris(uyg.kullanicilar.index(k_yon))
        sayfa2 = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Klinik Yöneticisi", sayfa2)
        self.assertNotIn("Hastane ekle", sayfa2)
        self.assertNotIn("Klinik ekle", sayfa2)
        self.assertNotIn("Klinik yöneticisi ata", sayfa2)
        self.assertNotIn("Personeli kliniğe ata", sayfa2)

    def test_admin_ve_hastane_yoneticisi_rol_degistirir(self):
        uyg = uygulama_modulu.uyg
        # 1. Admin normal kullanıcı Ali'yi (sira=1) Merkez Hastane Yöneticisi yapar
        self.giris(0)
        self.istemci.post("/admin/rol-degistir", data={
            "kullanici": 1, "yeni_rol": "hastane_yoneticisi", "hastane": 0})
        self.assertIsInstance(uyg.kullanicilar[1], HastaneYoneticisi)
        self.assertIs(uyg.kullanicilar[1].hastane, uyg.kurum.hastaneler[0])
        self.assertTrue(uyg.kullanicilar[1].sifre_dogru_mu(VARSAYILAN_SIFRE))
        # 2. Şimdi Ali (Merkez Hastane Yöneticisi) giriş yapar; Veli'yi (sira=2) kendi kliniğine Klinik Yöneticisi yapar
        self.istemci.get("/cikis")
        self.giris(1)
        self.istemci.post("/admin/rol-degistir", data={
            "kullanici": 2, "yeni_rol": "klinik_yoneticisi", "klinik": 0})
        self.assertIsInstance(uyg.kullanicilar[2], KlinikYoneticisi)
        self.assertIs(uyg.kullanicilar[2].klinik, uyg.kurum.hastaneler[0].klinikler[0])
        # 3. Hastane yöneticisi Veli'yi başka bir hastanenin kliniğine (ör. klinik=10) atayamaz
        self.istemci.post("/admin/rol-degistir", data={
            "kullanici": 2, "yeni_rol": "klinik_yoneticisi", "klinik": 10})
        self.assertIs(uyg.kullanicilar[2].hastane, uyg.kurum.hastaneler[0])
        # 4. Hastane yöneticisi kimseyi Hastane Yöneticisi yapamaz
        self.istemci.post("/admin/rol-degistir", data={
            "kullanici": 2, "yeni_rol": "hastane_yoneticisi", "hastane": 0})
        self.assertIsInstance(uyg.kullanicilar[2], KlinikYoneticisi)
        # 5. Admin Ali'yi ve Veli'yi tekrar normal kullanıcı (Hasta) yapabilir
        self.istemci.get("/cikis")
        self.giris(0)
        self.istemci.post("/admin/rol-degistir", data={"kullanici": 1, "yeni_rol": "hasta"})
        self.istemci.post("/admin/rol-degistir", data={"kullanici": 2, "yeni_rol": "hasta"})
        self.assertEqual(uyg.kullanicilar[1].rol(), "Hasta")
        self.assertEqual(uyg.kullanicilar[2].rol(), "Hasta")


class YoneticiKapsamTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.hastane_yon = HastaneYoneticisi("Hakan", "Yurt", "81111111111", self.merkez)
        self.klinik_yon = KlinikYoneticisi("Kemal", "Ak", "82222222222", self.merkez, self.dahiliye)

    def test_hastane_yoneticisi_sadece_kendi_hastanesini_yonetir(self):
        from datetime import time
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.hastane_ekle(self.kurum, Hastane("Yeni", time(8, 0), time(17, 0)))
        # Kendi hastanesine klinik ekleyebilir, başka hastaneye ekleyemez
        yeni_kl = Klinik("Nöroloji")
        self.hastane_yon.klinik_ekle(self.merkez, yeni_kl)
        self.assertIn(yeni_kl, self.merkez.klinikler)
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.klinik_ekle(self.kadikoy, Klinik("Göz"))
        # Başka hastanenin kliniğine hizmet/personel ekleyemez
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.hizmet_ekle(self.dahiliye2, Muayene("Ek", 15, 200))

    def test_klinik_yoneticisi_sadece_kendi_klinigini_yonetir(self):
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.klinik_ekle(self.merkez, Klinik("Nöroloji"))
        # Kendi kliniğine hizmet ekleyebilir
        kontrol = Muayene("Kontrol", 15, 250.0)
        self.klinik_yon.hizmet_ekle(self.dahiliye, kontrol)
        self.assertIn(kontrol, self.dahiliye.hizmetler)
        # Klinik yöneticisinin personel_ata yetkisi yoktur (doğrudan çağrı da YetkiHatasi verir)
        asistan = Asistan("Elif", "Aydın", "66666666666", "Dahiliye Asistanı")
        hemsire = Hemsire("Zeynep", "Acar", "33333333333", "Hemşirelik")
        teknisyen = Teknisyen("Can", "Er", "44444444444", "Dahiliye", "Tansiyon Cihazı")
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.personel_ata(self.dahiliye, hemsire)
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.personel_ata(self.kardiyoloji, hemsire)
        # Klinik yöneticisi personel_kaydet ile personeli kaydettiğinde doğrudan kliniğine atanır
        uyg = Uygulama()
        for p in (asistan, hemsire, teknisyen):
            self.klinik_yon.personel_kaydet(uyg, p)
            self.assertIn(p, self.dahiliye.personeller)
        self.klinik_yon.asistan_bagla(asistan, self.doktor)
        self.assertIs(asistan.doktor, self.doktor)
        # Aynı hastanedeki başka bir kliniğe (Kardiyoloji) hizmet ekleyemez
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.hizmet_ekle(self.kardiyoloji, Muayene("Yasak", 15, 100))

    def test_klinik_yoneticisi_sadece_kendi_kliniginin_randevusuna_karisabilir(self):
        r_dahiliye = self.randevu_al()
        diger_dr = Doktor("Can", "Öztürk", "55555555555", "Kardiyoloji")
        self.admin.doktor_ekle(self.kardiyoloji, diger_dr)
        diger_dr.musaitlik_ekle(datetime(2026, 10, 14, 15, 0), datetime(2026, 10, 14, 16, 0))
        r_kardiyo = self.hasta2.randevu_al(self.sistem, self.merkez, self.kardiyoloji,
                                           diger_dr, self.ekg, datetime(2026, 10, 14, 15, 0))
        self.assertEqual(self.klinik_yon.yonetilen_randevular(self.sistem), [r_dahiliye])
        self.klinik_yon.randevu_onayla(r_dahiliye)
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.randevu_onayla(r_kardiyo)
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.randevu_iptal(r_kardiyo)


class GorevVeUzmanlikTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.uyg = Uygulama()
        self.uyg.kullanici_ekle(self.admin)
        self.uyg.kullanici_ekle(self.doktor)
        self.uyg.kullanici_ekle(self.hasta)

    def test_yonetici_gorev_ekle_basarili(self):
        self.admin.gorev_ekle(self.uyg, "doktor", "Onkoloji")
        self.assertIn("Onkoloji", self.uyg.gorevler_listesi("doktor"))
        self.admin.gorev_ekle(self.uyg, "hemsire", "Triyaj Hemşiresi")
        self.assertIn("Triyaj Hemşiresi", self.uyg.gorevler_listesi("hemsire"))

    def test_gecersiz_tur_ve_bos_ad_hatalari(self):
        with self.assertRaises(SistemHatasi):
            self.admin.gorev_ekle(self.uyg, "sekreter", "Danışma")
        with self.assertRaises(ValueError):
            self.admin.gorev_ekle(self.uyg, "doktor", "   ")

    def test_mukerrer_gorev_eklenemez(self):
        self.admin.gorev_ekle(self.uyg, "doktor", "Nükleer Tıp")
        with self.assertRaises(SistemHatasi):
            self.admin.gorev_ekle(self.uyg, "doktor", "Nükleer Tıp")

    def test_yetkisiz_kullanici_gorev_ekleyemez(self):
        self.assertFalse(self.hasta.yetki_var_mi("gorev_ekle"))
        with self.assertRaises((YetkiHatasi, AttributeError)):
            self.hasta.gorev_ekle(self.uyg, "doktor", "Yeni Görev")

    def test_depo_gorevleri_saklar_ve_yukler(self):
        self.admin.gorev_ekle(self.uyg, "doktor", "Genetik")
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
            gecici_yol = f.name
        try:
            d = Depo(gecici_yol)
            d.kaydet(self.uyg)
            yuklenen = d.yukle()
            self.assertIn("Genetik", yuklenen.gorevler_listesi("doktor"))
        finally:
            if os.path.exists(gecici_yol):
                os.remove(gecici_yol)

    def test_admin_gorev_ekle_route(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})
        yanit = istemci.post("/admin/gorev", data={"tur": "doktor", "ad": "Algoloji"}, follow_redirects=True)
        self.assertEqual(yanit.status_code, 200)
        self.assertIn("Algoloji", uygulama_modulu.uyg.gorevler_listesi("doktor"))


class AsistanDoktorFiltreTest(unittest.TestCase):
    def setUp(self):
        self.uyg = ornek_veri()
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()
        self.istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})

    def test_kliniksiz_asistana_uzmanlikla_alakali_doktorlar_eslesir(self):
        asistan_kardiyo = Asistan("Fırat", "Kayaalp", "99988877766", "Kardiyoloji")
        self.uyg.kullanici_ekle(asistan_kardiyo)
        as_sira = [p for p in self.uyg.kullanicilar if isinstance(p, Asistan)].index(asistan_kardiyo)
        yanit = self.istemci.get(f"/panel?as={as_sira}")
        self.assertEqual(yanit.status_code, 200)
        html = yanit.get_data(as_text=True)
        secim_bolumu = html.split('id="bagla_doktor_secim"')[1].split('</select>')[0]
        self.assertIn("Kardiyoloji", secim_bolumu)

    def test_klinige_atanmis_asistana_sadece_ayni_klinikteki_doktorlar_gelir(self):
        asistanlar = [p for p in self.uyg.kullanicilar if isinstance(p, Asistan)]
        elif_sira = next(i for i, a in enumerate(asistanlar) if a.tam_ad == "Elif Aydın")
        yanit = self.istemci.get(f"/panel?as={elif_sira}")
        self.assertEqual(yanit.status_code, 200)
        html = yanit.get_data(as_text=True)
        self.assertIn("Doktor:<br>", html)
        self.assertNotIn("Doktor (asistanla aynı hastanedekiler üstte sıralanır):", html)
        secim_bolumu = html.split('id="bagla_doktor_secim"')[1].split('</select>')[0]
        self.assertIn("Dahiliye", secim_bolumu)
        self.assertNotIn("Göz Hastalıkları", secim_bolumu)


class HizmetSilTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.uyg = Uygulama()
        self.uyg.kurum = self.kurum
        self.uyg.sistem = self.sistem
        self.hastane_yon = HastaneYoneticisi("Hakan", "Yurt", "33333333331", self.merkez)
        self.klinik_yon = KlinikYoneticisi("Selin", "Kaya", "44444444441", self.merkez, self.dahiliye)
        self.uyg.kullanici_ekle(self.admin)
        self.uyg.kullanici_ekle(self.hastane_yon)
        self.uyg.kullanici_ekle(self.klinik_yon)
        self.uyg.kullanici_ekle(self.doktor)
        self.uyg.kullanici_ekle(self.hasta)

        # Yeni bir hizmet ekleyelim
        self.ekstra_hizmet = Muayene("Checkup", 20, 300.0)
        self.admin.hizmet_ekle(self.dahiliye, self.ekstra_hizmet)

    def test_admin_hizmet_sil_basarili(self):
        self.assertIn(self.ekstra_hizmet, self.dahiliye.hizmetler)
        self.admin.hizmet_sil(self.uyg, self.merkez, self.dahiliye, self.ekstra_hizmet)
        self.assertNotIn(self.ekstra_hizmet, self.dahiliye.hizmetler)

    def test_hastane_yoneticisi_kendi_hastanesindeki_hizmeti_silebilir(self):
        self.assertTrue(self.hastane_yon.yetki_var_mi("hizmet_sil"))
        self.hastane_yon.hizmet_sil(self.uyg, self.merkez, self.dahiliye, self.ekstra_hizmet)
        self.assertNotIn(self.ekstra_hizmet, self.dahiliye.hizmetler)

    def test_hastane_yoneticisi_baska_hastaneden_hizmet_silemez(self):
        # Kadıköy hastanesindeki Dahiliye kliniğindeki ekg hizmetini silmeye çalışsın
        with self.assertRaises(YetkiHatasi):
            self.hastane_yon.hizmet_sil(self.uyg, self.kadikoy, self.dahiliye2, self.ekg)
        self.assertIn(self.ekg, self.dahiliye2.hizmetler)

    def test_klinik_yoneticisi_hizmet_sil_yetkisi_yoktur(self):
        self.assertFalse(self.klinik_yon.yetki_var_mi("hizmet_sil"))
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.hizmet_sil(self.uyg, self.merkez, self.dahiliye, self.ekstra_hizmet)

    def test_aktif_randevusu_olan_hizmet_silinemez(self):
        # self.muayene için aktif gelecekte bir randevu alalım
        self.randevu_al()
        with self.assertRaises(SistemHatasi):
            self.admin.hizmet_sil(self.uyg, self.merkez, self.dahiliye, self.muayene)
        self.assertIn(self.muayene, self.dahiliye.hizmetler)

    def test_hizmet_silinince_doktorun_ozel_hizmet_secimi_guncellenir(self):
        self.doktor.hizmetlerimi_sec(self.dahiliye, [self.muayene, self.ekstra_hizmet])
        self.assertIn(self.ekstra_hizmet, self.doktor.ozel_hizmetler(self.dahiliye))
        self.admin.hizmet_sil(self.uyg, self.merkez, self.dahiliye, self.ekstra_hizmet)
        self.assertNotIn(self.ekstra_hizmet, self.doktor.sunulan_hizmetler(self.dahiliye))

    def test_admin_hizmet_sil_route(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})

        # Panelde "Hizmet sil" kartı görünmeli
        sayfa = istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Hizmet sil", sayfa)

        # Aktif randevusu olmayan bir hizmet bulup silelim
        tum_hz = uygulama_modulu.tum_hizmetler()
        hz_sira = None
        secilen_k = None
        secilen_s = None
        for i, (h, k, s) in enumerate(tum_hz):
            if not uygulama_modulu.uyg.sistem.gelecek_aktif_randevu_var_mi(lambda r: r.klinik is k and r.hizmet is s):
                hz_sira = i
                secilen_k = k
                secilen_s = s
                break
        self.assertIsNotNone(hz_sira)
        yanit = istemci.post("/admin/hizmet-sil", data={"hizmet": hz_sira}, follow_redirects=True)
        self.assertEqual(yanit.status_code, 200)
        self.assertNotIn(secilen_s, secilen_k.hizmetler)

    def test_klinik_yoneticisi_panelinde_hizmet_sil_gorunmez(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        klinik_yon = next(k for k in uygulama_modulu.uyg.kullanicilar
                          if isinstance(k, KlinikYoneticisi) and k.klinik is not None)
        istemci.post(f"/giris/{uygulama_modulu.uyg.kullanicilar.index(klinik_yon)}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = istemci.get("/panel").get_data(as_text=True)
        self.assertNotIn("Hizmet sil", sayfa)


class CihazUcretiToplamaTest(TemelTest):
    def test_radyoloji_ucret_toplama_ve_parantez_ici_ek_ucret(self):
        radyoloji = Radyoloji("Röntgen Test", 15, 200.0, cihaz_ucreti=150.0)
        self.assertEqual(radyoloji.ucret, 350.0)
        self.assertEqual(radyoloji.ucret_metni, "350 TL (+150 TL ek ücret)")

    def test_cihaz_ucreti_olmayan_hizmetler(self):
        muayene = Muayene("Genel Muayene", 20, 300.0)
        self.assertEqual(muayene.ucret, 300.0)
        self.assertEqual(muayene.ucret_metni, "300 TL")

        lab = Laboratuvar("Tam Kan", 15, 100.0, tahlil_sayisi=3)
        self.assertEqual(lab.ucret, 300.0)
        self.assertEqual(lab.ucret_metni, "300 TL (3 tahlil)")

    def test_admin_hizmet_eklerken_cihaz_ucreti_varsa_radyoloji_olur_ve_toplar(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post("/giris/0", data={"sifre": VARSAYILAN_SIFRE})

        # tur='muayene' seçili kalsa bile ekstra=250 girildiyse Radyoloji oluşturulmalı ve toplanmalı
        yanit = istemci.post("/admin/hizmet", data={
            "klinik": 0,
            "tur": "muayene",
            "ad": "Tomografi Özel",
            "sure": 25,
            "ucret": 400.0,
            "ekstra": 250.0
        }, follow_redirects=True)
        self.assertEqual(yanit.status_code, 200)

        html = yanit.get_data(as_text=True)
        # 400 + 250 = 650 TL toplam ve (+250 TL ek ücret) parantez içinde belirtilmeli
        self.assertIn("Tomografi Özel", html)
        self.assertIn("650 TL (+250 TL ek ücret)", html)


class KlinikYoneticisiPersonelKayitTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.uyg = Uygulama()
        self.uyg.kurum = self.kurum
        self.uyg.sistem = self.sistem
        self.uyg.kullanici_ekle(self.admin)
        self.uyg.kullanici_ekle(self.doktor)
        self.klinik_yon = KlinikYoneticisi("Kemal", "Ak", "82222222222", self.merkez, self.dahiliye)
        self.uyg.kullanici_ekle(self.klinik_yon)

    def test_klinik_yoneticisi_yetkileri_sinirlidir(self):
        yetkiler = self.klinik_yon.yetkiler()
        self.assertNotIn("personel_ata", yetkiler)
        self.assertNotIn("gorev_ekle", yetkiler)
        self.assertNotIn("hizmet_sil", yetkiler)
        self.assertIn("personel_kaydet", yetkiler)
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.personel_ata(self.dahiliye, Hemsire("A", "B", "11122233344", "Hemşirelik"))

    def test_klinik_yoneticisi_kendi_klinigine_uygun_doktor_kaydeder_ve_otomatik_atanir(self):
        yeni_dr = Doktor("Fatma", "Demir", "11122233344", "Dahiliye")
        self.klinik_yon.personel_kaydet(self.uyg, yeni_dr)
        # Kullanıcı uygulamaya kaydedilmiş olmalı
        self.assertIn(yeni_dr, self.uyg.kullanicilar)
        # Doktor doğrudan kliniğe atanmış olmalı
        self.assertIn(yeni_dr, self.dahiliye.doktorlar)
        self.assertIn(self.dahiliye, yeni_dr.klinikler)

    def test_klinik_yoneticisi_baska_klinik_doktoru_kaydedemez(self):
        baska_dr = Doktor("Ahmet", "Kaya", "22233344455", "Kardiyoloji")
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.personel_kaydet(self.uyg, baska_dr)
        self.assertNotIn(baska_dr, self.uyg.kullanicilar)
        self.assertNotIn(baska_dr, self.dahiliye.doktorlar)

    def test_klinik_yoneticisi_kendi_klinigine_uygun_asistan_kaydeder_ve_otomatik_atanir(self):
        asistan = Asistan("Merve", "Yurt", "33344455566", "Dahiliye Asistanı")
        self.klinik_yon.personel_kaydet(self.uyg, asistan)
        self.assertIn(asistan, self.uyg.kullanicilar)
        self.assertIn(asistan, self.dahiliye.personeller)
        self.assertIn(self.dahiliye, asistan.klinikler)

    def test_klinik_yoneticisi_baska_klinik_asistani_kaydedemez(self):
        baska_asistan = Asistan("Oğuz", "Son", "44455566677", "Kardiyoloji Asistanı")
        with self.assertRaises(YetkiHatasi):
            self.klinik_yon.personel_kaydet(self.uyg, baska_asistan)
        self.assertNotIn(baska_asistan, self.uyg.kullanicilar)

    def test_klinik_yoneticisi_panelinde_personel_ata_ve_gorev_ekle_yoktur(self):
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post(f"/giris/{self.uyg.kullanicilar.index(self.klinik_yon)}",
                     data={"sifre": VARSAYILAN_SIFRE})
        yanit = istemci.get("/panel")
        html = yanit.get_data(as_text=True)
        self.assertNotIn("Personeli kliniğe ata", html)
        self.assertNotIn("Uzmanlık / görev ekle", html)
        self.assertIn("Kaydedilen personel doğrudan sorumlu olduğunuz <b>Dahiliye</b> kliniğine atanır.", html)

    def test_klinik_yoneticisi_panelinde_doktor_uzmanligi_klinikle_kisitlidir(self):
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        istemci = uygulama_modulu.app.test_client()
        istemci.post(f"/giris/{self.uyg.kullanicilar.index(self.klinik_yon)}",
                     data={"sifre": VARSAYILAN_SIFRE})
        yanit = istemci.get("/panel")
        html = yanit.get_data(as_text=True)
        # var tumGorevler içinde doktor sadece Dahiliye olmalı
        self.assertIn('"doktor": ["Dahiliye"]', html)


class HastaneBazliMusaitlikVeGorunumTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.uyg = ornek_veri(date.today() + timedelta(days=1))
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()

    def test_doktor_sayfasinda_kliniklerde_hastane_adi_yazar(self):
        ayse = next(k for k in self.uyg.kullanicilar if k.tam_ad == "Ayşe Yılmaz")
        sira = self.uyg.kullanicilar.index(ayse)
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Merkez Hastane / Dahiliye", sayfa)
        self.assertIn("Kadıköy Hastane / Dahiliye", sayfa)

    def test_takvimim_seceneklerinde_hastane_calisma_saatleri_yazar(self):
        ayse = next(k for k in self.uyg.kullanicilar if k.tam_ad == "Ayşe Yılmaz")
        sira = self.uyg.kullanicilar.index(ayse)
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Merkez Hastane (08:00 - 17:00)", sayfa)

    def test_hastane_calisma_saatleri_disinda_musaitlik_eklenemez(self):
        merkez = self.uyg.kurum.hastane_bul("Merkez Hastane")
        doktor = next(k for k in self.uyg.doktorlar() if "Merkez Hastane" in [h.ad for h in k.hastaneler()])
        gecersiz_bas = datetime(2026, 11, 20, 18, 0)
        gecersiz_bit = datetime(2026, 11, 20, 19, 0)
        with self.assertRaises(ValueError) as ctx:
            doktor.musaitlik_ekle(gecersiz_bas, gecersiz_bit, merkez)
        self.assertIn("çalışma saatleri", str(ctx.exception))

    def test_farkli_hastanelerde_ayni_anda_musaitlik_eklenemez(self):
        ayse = next(k for k in self.uyg.kullanicilar if k.tam_ad == "Ayşe Yılmaz")
        merkez = self.uyg.kurum.hastane_bul("Merkez Hastane")
        kadikoy = self.uyg.kurum.hastane_bul("Kadıköy Hastane")
        tarih = date.today() + timedelta(days=20)
        bas1 = datetime.combine(tarih, time(10, 0))
        bit1 = datetime.combine(tarih, time(12, 0))
        ayse.musaitlik_ekle(bas1, bit1, merkez)
        bas2 = datetime.combine(tarih, time(11, 0))
        bit2 = datetime.combine(tarih, time(13, 0))
        with self.assertRaises(ValueError) as ctx:
            ayse.musaitlik_ekle(bas2, bit2, kadikoy)
        self.assertIn("zaten müsaitliğiniz var", str(ctx.exception))

    def test_anasayfada_personel_hastaneleri_gorunur_ve_hastaneye_gore_filtrelenir(self):
        sayfa = self.istemci.get("/?grup=personel").get_data(as_text=True)
        self.assertIn("<b>Hastane:</b>", sayfa)
        self.assertIn("Tüm Hastaneler", sayfa)

        filtreli = self.istemci.get("/?grup=personel&hastane=Kad%C4%B1k%C3%B6y+Hastane").get_data(as_text=True)
        self.assertIn("Kadıköy Hastane", filtreli)
        self.assertNotIn("Selin Kaya", filtreli)


class HemsireHastaKabulVeIptalTest(TemelTest):
    def setUp(self):
        super().setUp()
        self.uyg = ornek_veri(date.today() + timedelta(days=1))
        uygulama_modulu.uyg = self.uyg
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()

    def test_odenen_randevu_iptal_edilemez(self):
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        merkez = self.uyg.kurum.hastane_bul("Merkez Hastane")
        klinik = merkez.klinikler[0]
        doktor = klinik.doktorlar[0]
        hizmet = klinik.hizmetler[0]
        randevu = Randevu(hasta, merkez, klinik, doktor, hizmet, datetime.now() + timedelta(days=1, hours=2))
        randevu.onayla()
        self.uyg.sistem.randevu_yukle(randevu)

        randevu.odeme_yap(NakitOdeme())
        self.assertTrue(randevu.odendi_mi)

        with self.assertRaises(RandevuHatasi) as ctx:
            randevu.iptal()
        self.assertIn("Ödemesi yapılmış randevu iptal edilemez", str(ctx.exception))

        with self.assertRaises(RandevuHatasi):
            randevu.hasta.randevu_iptal(randevu)

        hasta_sira = self.uyg.kullanicilar.index(hasta)
        self.istemci.post(f"/giris/{hasta_sira}", data={"sifre": VARSAYILAN_SIFRE})

        r_sira = self.uyg.sistem.randevular.index(randevu)
        yanit = self.istemci.post(f"/hasta/iptal/{r_sira}", follow_redirects=True)
        sayfa = yanit.get_data(as_text=True)
        self.assertIn("Ödemesi yapılmış randevu iptal edilemez", sayfa)
        self.assertNotEqual(randevu.durum, RandevuDurumu.IPTAL)

        panel_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertNotIn(f"/hasta/iptal/{r_sira}", panel_sayfa)

    def test_hemsire_hasta_kabul_yapar_ve_doktorda_gorunur(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        hemsire_klinik = hemsire.klinikler[0]
        hastane = hemsire_klinik.hastane
        doktor = hemsire_klinik.doktorlar[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = hemsire_klinik.hizmetler[0]

        bugun_zaman = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        randevu = Randevu(hasta, hastane, hemsire_klinik, doktor, hizmet, bugun_zaman)
        randevu.onayla()
        self.uyg.sistem.randevu_yukle(randevu)

        bugunku = hemsire.bugunun_onayli_randevulari(self.uyg.sistem.randevular)
        self.assertIn(randevu, bugunku)

        hemsire_sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{hemsire_sira}", data={"sifre": VARSAYILAN_SIFRE})

        r_sira = self.uyg.sistem.randevular.index(randevu)
        resp = self.istemci.post(f"/hemsire/hasta-kabul/{r_sira}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        self.assertTrue(randevu.kabul_edildi_mi)
        self.assertEqual(randevu.durum, RandevuDurumu.ONAYLANDI)
        self.assertEqual(randevu.kabul_eden, hemsire)
        self.assertIsNotNone(randevu.kabul_zamani)

        doktor_sira = self.uyg.kullanicilar.index(doktor)
        self.istemci.post(f"/giris/{doktor_sira}", data={"sifre": VARSAYILAN_SIFRE})
        doktor_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Hasta geldi", doktor_sayfa)
        self.assertIn(hemsire.tam_ad, doktor_sayfa)

    def test_hemsire_baska_klinigin_randevusunu_kabul_edemez(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        baska_klinik = None
        for h in self.uyg.kurum.hastaneler:
            for k in h.klinikler:
                if k not in hemsire.klinikler:
                    baska_klinik = k
                    break
            if baska_klinik:
                break
        self.assertIsNotNone(baska_klinik)
        doktor = baska_klinik.doktorlar[0]
        hastane = baska_klinik.hastane
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = baska_klinik.hizmetler[0]

        bugun_zaman = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        randevu = Randevu(hasta, hastane, baska_klinik, doktor, hizmet, bugun_zaman)
        randevu.onayla()

        with self.assertRaises(YetkiHatasi):
            hemsire.hasta_kabul(randevu)

    def test_yetkiler_listesi_arayuzde_gorunmez(self):
        admin = next(k for k in self.uyg.kullanicilar if type(k) is Yonetici)
        admin_sira = self.uyg.kullanicilar.index(admin)
        self.istemci.post(f"/giris/{admin_sira}", data={"sifre": VARSAYILAN_SIFRE})
        admin_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertNotIn("hastane_ekleklinik_ekle", admin_sayfa)

        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        hemsire_sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{hemsire_sira}", data={"sifre": VARSAYILAN_SIFRE})
        hemsire_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertNotIn("hasta_kabul", hemsire_sayfa)

    def test_doktor_panelinde_tum_hastaneler_yazmaz(self):
        ayse = next(k for k in self.uyg.kullanicilar if k.tam_ad == "Ayşe Yılmaz")
        ayse_sira = self.uyg.kullanicilar.index(ayse)
        self.istemci.post(f"/giris/{ayse_sira}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertNotIn("Tüm Hastaneler", sayfa)

    def test_hemsire_panelinde_kliniklerin_hastane_adi_gorunur(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        klinik = hemsire.klinikler[0]
        hastane = getattr(klinik, "hastane", None)
        self.assertIsNotNone(hastane)
        self.assertIn(f"{hastane.ad} / {klinik.ad}", sayfa)

    def test_hemsire_sadece_kendi_hastane_ve_klinik_randevularini_gorur(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        klinik1 = hemsire.klinikler[0]
        hastane1 = klinik1.hastane
        doktor1 = klinik1.doktorlar[0]
        hizmet1 = klinik1.hizmetler[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))

        # Kendi kliniğine ait randevu
        r1 = Randevu(hasta, hastane1, klinik1, doktor1, hizmet1, datetime.now() + timedelta(days=2))
        r1.onayla()
        self.uyg.sistem.randevu_yukle(r1)

        # Başka hastanedeki kliniğe ait randevu
        baska_klinik = None
        for h in self.uyg.kurum.hastaneler:
            for k in h.klinikler:
                if k not in hemsire.klinikler:
                    baska_klinik = k
                    break
            if baska_klinik:
                break
        r2 = Randevu(hasta, baska_klinik.hastane, baska_klinik, baska_klinik.doktorlar[0],
                     baska_klinik.hizmetler[0], datetime.now() + timedelta(days=2))
        r2.onayla()
        self.uyg.sistem.randevu_yukle(r2)

        onaylilar = hemsire.onayli_randevular(self.uyg.sistem.randevular)
        self.assertIn(r1, onaylilar)
        self.assertNotIn(r2, onaylilar)

    def test_hemsire_gelecek_veya_bugun_onayli_randevulari_gorur_ve_kabul_eder(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        klinik = hemsire.klinikler[0]
        doktor = klinik.doktorlar[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = klinik.hizmetler[0]

        # Yarın için onaylanmış bir randevu
        yarin_zaman = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        randevu = Randevu(hasta, klinik.hastane, klinik, doktor, hizmet, yarin_zaman)
        randevu.onayla()
        self.uyg.sistem.randevu_yukle(randevu)

        sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})

        # Varsayılan panelde onaylı randevu listelenmeli (sadece bugün ile sınırlandırılıp kaybolmamalı)
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn(randevu.hasta.tam_ad, sayfa)
        self.assertIn("Hasta geldi", sayfa)

        # Sadece bugün filtresi uygulandığında yarınki randevu görünmemeli
        bugun_sayfa = self.istemci.get("/panel?tarih=bugun").get_data(as_text=True)
        self.assertNotIn(randevu.hasta.tam_ad, bugun_sayfa)
        self.assertIn("Bugün için onaylı randevu bulunmuyor", bugun_sayfa)

        # Hemşire hasta kabul işlemini gerçekleştirebilmeli
        r_sira = self.uyg.sistem.randevular.index(randevu)
        resp = self.istemci.post(f"/hemsire/hasta-kabul/{r_sira}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(randevu.kabul_edildi_mi)

    def test_asistan_ve_hemsire_kaydinda_ozel_uzmanlik_gerekmez(self):
        admin = next(k for k in self.uyg.kullanicilar if type(k) is Yonetici)
        admin_sira = self.uyg.kullanicilar.index(admin)
        self.istemci.post(f"/giris/{admin_sira}", data={"sifre": VARSAYILAN_SIFRE})

        # Asistan kaydet: uzmanlık gönderilmediğinde otomatik 'Asistan' olur
        resp_as = self.istemci.post("/admin/personel", data={
            "tur": "asistan", "ad": "TestAsistan", "soyad": "Kaya", "tc": "99988877711"
        }, follow_redirects=True)
        self.assertEqual(resp_as.status_code, 200)
        yeni_as = next(k for k in self.uyg.kullanicilar if k.tc_no == "99988877711")
        self.assertIsInstance(yeni_as, Asistan)
        self.assertEqual(yeni_as.uzmanlik, "Asistan")

        # Hemşire kaydet: uzmanlık gönderilmediğinde otomatik 'Hemşirelik' olur
        resp_hem = self.istemci.post("/admin/personel", data={
            "tur": "hemsire", "ad": "TestHemsire", "soyad": "Demir", "tc": "99988877722"
        }, follow_redirects=True)
        self.assertEqual(resp_hem.status_code, 200)
        yeni_hem = next(k for k in self.uyg.kullanicilar if k.tc_no == "99988877722")
        self.assertIsInstance(yeni_hem, Hemsire)
        self.assertEqual(yeni_hem.uzmanlik, "Hemşirelik")

    def test_hemsire_hasta_gelmedi_isaretler_ve_24_saat_engel_koyar(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        klinik = hemsire.klinikler[0]
        doktor = klinik.doktorlar[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = klinik.hizmetler[0]

        randevu_zamani = datetime.now() - timedelta(hours=1)
        randevu = Randevu(hasta, klinik.hastane, klinik, doktor, hizmet, randevu_zamani)
        randevu.onayla()
        self.uyg.sistem.randevu_yukle(randevu)

        # Hasta gelmedi işaretle
        islem_ani = datetime.now()
        hemsire.hasta_gelmedi(randevu, islem_ani)

        self.assertTrue(randevu.gelmedi_mi)
        self.assertFalse(randevu.kabul_edildi_mi)
        self.assertIn("Hasta gelmedi", randevu.kabul_metni)
        self.assertTrue(hasta.randevu_engeli_var_mi(islem_ani + timedelta(hours=1)))
        self.assertTrue(hasta.randevu_engeli_var_mi(islem_ani + timedelta(hours=23, minutes=59)))

        # 24 saat boyunca yeni randevu alamaz
        with self.assertRaises(RandevuHatasi) as ctx:
            hasta.randevu_al(self.uyg.sistem, klinik.hastane, klinik, doktor, hizmet, islem_ani + timedelta(days=2))
        self.assertIn("Randevunuza gelmediğiniz için", str(ctx.exception))

        # 24 saat geçince engel kalkar
        gecerli_zaman = islem_ani + timedelta(hours=24, minutes=1)
        self.assertFalse(hasta.randevu_engeli_var_mi(gecerli_zaman))

        # Gelmedi olarak işaretlenmiş randevu iptal edilemez
        with self.assertRaises(RandevuHatasi):
            randevu.iptal()

    def test_hemsire_hasta_gelmedi_web_endpointi_ve_arayuz_engeli(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        klinik = hemsire.klinikler[0]
        doktor = klinik.doktorlar[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = klinik.hizmetler[0]

        randevu_zamani = datetime.now() - timedelta(minutes=10)
        randevu = Randevu(hasta, klinik.hastane, klinik, doktor, hizmet, randevu_zamani)
        randevu.onayla()
        self.uyg.sistem.randevu_yukle(randevu)

        # Hemşire web üzerinden 'Hasta gelmedi' butonuna basar
        h_sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{h_sira}", data={"sifre": VARSAYILAN_SIFRE})
        r_sira = self.uyg.sistem.randevular.index(randevu)

        resp = self.istemci.post(f"/hemsire/hasta-gelmedi/{randevu.id}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(randevu.gelmedi_mi)
        self.assertTrue(hasta.randevu_engeli_var_mi())

        # Doktor panelinde 'Hasta gelmedi' rozeti görünmeli
        d_sira = self.uyg.kullanicilar.index(doktor)
        self.istemci.post(f"/giris/{d_sira}", data={"sifre": VARSAYILAN_SIFRE})
        doktor_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Hasta gelmedi", doktor_sayfa)

        # Hasta paneline girince engel uyarısı görünmeli ve randevu alamamalı
        hasta_sira = self.uyg.kullanicilar.index(hasta)
        self.istemci.post(f"/giris/{hasta_sira}", data={"sifre": VARSAYILAN_SIFRE})
        hasta_sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Randevu Engeli", hasta_sayfa)
        self.assertIn("kadar yeni randevu alamazsınız", hasta_sayfa)

        # Web üzerinden randevu almaya çalışırsa engellenmeli
        al_resp = self.istemci.post("/hasta/randevu-al", data={
            "h": "0", "k": "0", "d": "0", "s": "0",
            "zaman": (datetime.now() + timedelta(days=3)).isoformat()
        }, follow_redirects=True)
        sayfa_sonuc = al_resp.get_data(as_text=True)
        self.assertIn("Randevunuza gelmediğiniz için", sayfa_sonuc)


class SonGuncellemelerTest(unittest.TestCase):
    def setUp(self):
        self.uyg = ornek_veri()
        self.uyg.sistem._saat = lambda: datetime(2026, 11, 8, 10, 0)
        uygulama_modulu.uyg = self.uyg
        self.istemci = uygulama_modulu.app.test_client()

    def test_hastane_silinince_doktor_musaitlikleri_temizlenir_ve_yeniden_acilir(self):
        # Ayşe Yılmaz'ın Kadıköy Hastanesi'nde müsaitliği var
        ayse = [k for k in self.uyg.kullanicilar if isinstance(k, Doktor) and k.ad == "Ayşe"][0]
        kadikoy = self.uyg.kurum.hastane_bul("Kadıköy Hastane")
        self.assertTrue(any(getattr(m, "hastane", None) is kadikoy for m in ayse.musaitlik))

        # Hastaneyi sil
        self.uyg.hastane_sil(kadikoy)

        # Ayşe'nin Kadıköy müsaitliği silinmiş olmalı
        self.assertFalse(any(getattr(m, "hastane", None) is kadikoy for m in ayse.musaitlik))
        self.assertFalse(any(getattr(getattr(m, "hastane", None), "ad", None) == "Kadıköy Hastane" for m in ayse.musaitlik))

        # Depoya kaydet ve geri yükle; BulunamadiHatasi fırlatılmadan temiz açılmalı
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_dosya = tmp.name
        try:
            depo = Depo(tmp_dosya)
            depo.kaydet(self.uyg)
            yeni_uyg = depo.yukle()
            yeni_ayse = [k for k in yeni_uyg.kullanicilar if isinstance(k, Doktor) and k.ad == "Ayşe"][0]
            self.assertFalse(any(getattr(getattr(m, "hastane", None), "ad", None) == "Kadıköy Hastane" for m in yeni_ayse.musaitlik))
        finally:
            if os.path.exists(tmp_dosya):
                os.remove(tmp_dosya)

    def test_randevu_id_ile_onay_silme_sonrasi_yanlis_randevuyu_onaylamaz(self):
        ayse = [k for k in self.uyg.kullanicilar if isinstance(k, Doktor) and k.ad == "Ayşe"][0]
        hastane = self.uyg.kurum.hastane_bul("Merkez Hastane")
        klinik = hastane.klinik_bul("Dahiliye")
        hizmet = klinik.hizmetler[0]
        hastalar = [k for k in self.uyg.kullanicilar if isinstance(k, Hasta)]
        hasta1 = hastalar[0]
        hasta2 = hastalar[1]

        r1 = Randevu(hasta1, hastane, klinik, ayse, hizmet, datetime(2026, 11, 16, 9, 0), id="ali_randevusu")
        r2 = Randevu(hasta2, hastane, klinik, ayse, hizmet, datetime(2026, 11, 16, 10, 0), id="veli_randevusu")
        self.uyg.sistem.randevu_yukle(r1)
        self.uyg.sistem.randevu_yukle(r2)

        # Doktor giriş yapar
        ayse_sira = self.uyg.kullanicilar.index(ayse)
        self.istemci.post(f"/giris/{ayse_sira}", data={"sifre": VARSAYILAN_SIFRE})

        # Yönetici r1'i siler (örneğin bir hizmeti veya randevuyu silerek sırayı kaydırır)
        self.uyg.sistem.randevulari_sil(lambda r: r.id == "ali_randevusu")

        # Doktor eski açık kalan ekrandaki Ali'nin butonuna basarsa:
        resp = self.istemci.post("/doktor/onayla/ali_randevusu", follow_redirects=True)
        # Ali bulunamaz, Veli ASLA onaylanmaz (Veli hala BEKLIYOR kalmalı)
        self.assertEqual(r2.durum, RandevuDurumu.BEKLIYOR)
        self.assertIn("Randevu bulunamadı veya silinmiş", resp.get_data(as_text=True))

        # Şimdi doktor Veli'nin butonuna basarsa Veli onaylanır
        self.istemci.post("/doktor/onayla/veli_randevusu", follow_redirects=True)
        self.assertEqual(r2.durum, RandevuDurumu.ONAYLANDI)

    def test_erken_hasta_gelmedi_islemi_reddedilir(self):
        hemsire = next(k for k in self.uyg.kullanicilar if isinstance(k, Hemsire) and k.klinikler)
        klinik = hemsire.klinikler[0]
        doktor = klinik.doktorlar[0]
        hasta = next(k for k in self.uyg.kullanicilar if isinstance(k, Hasta))
        hizmet = klinik.hizmetler[0]

        gelecek_randevu = Randevu(hasta, klinik.hastane, klinik, doktor, hizmet, datetime.now() + timedelta(days=2))
        gelecek_randevu.onayla()
        self.uyg.sistem.randevu_yukle(gelecek_randevu)
        Randevu.ZAMAN_KONTROLU = True        # varsayılan demo modunda kapalı
        self.addCleanup(setattr, Randevu, "ZAMAN_KONTROLU", False)

        # Model seviyesinde erken gelmedi denemesi
        with self.assertRaises(RandevuHatasi) as ctx:
            hemsire.hasta_gelmedi(gelecek_randevu)
        self.assertIn("Randevu saati gelmeden", str(ctx.exception))

        # Web endpoint üzerinden erken gelmedi denemesi
        h_sira = self.uyg.kullanicilar.index(hemsire)
        self.istemci.post(f"/giris/{h_sira}", data={"sifre": VARSAYILAN_SIFRE})
        resp = self.istemci.post(f"/hemsire/hasta-gelmedi/{gelecek_randevu.id}", follow_redirects=True)
        sayfa = resp.get_data(as_text=True)
        self.assertIn("Randevu saati gelmeden", sayfa)
        self.assertFalse(gelecek_randevu.gelmedi_mi)
        self.assertFalse(hasta.randevu_engeli_var_mi())


if __name__ == "__main__":
    unittest.main()
