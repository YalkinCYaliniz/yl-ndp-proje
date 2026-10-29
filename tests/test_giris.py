import json
import os
import tempfile
import unittest
from datetime import datetime

import app as uygulama_modulu
from randevu.depo import Depo
from randevu.guvenlik import Sifre
from randevu.hatalar import SistemHatasi
from randevu.kullanici import Hasta, Misafir
from randevu.ornek_veri import ornek_veri
from randevu.uygulama import Uygulama, VARSAYILAN_SIFRE


class SifreTest(unittest.TestCase):
    def test_dogrulama(self):
        s = Sifre.olustur("gizli123")
        self.assertTrue(s.dogru_mu("gizli123"))
        self.assertFalse(s.dogru_mu("yanlis"))

    def test_kisa_sifre_reddedilir(self):
        with self.assertRaises(ValueError):
            Sifre.olustur("123")

    def test_duz_sifre_saklanmaz(self):
        s = Sifre.olustur("gizli123")
        self.assertNotIn("gizli123", json.dumps(s.sozluge()))

    def test_sozluk_gidis_donus(self):
        s = Sifre.olustur("gizli123")
        self.assertTrue(Sifre.sozlukten(s.sozluge()).dogru_mu("gizli123"))

    def test_ayni_sifre_farkli_ozet(self):
        self.assertNotEqual(Sifre.olustur("gizli123").sozluge(), Sifre.olustur("gizli123").sozluge())


class KullaniciKimlikTest(unittest.TestCase):
    def test_varsayilan_kullanici_adi_ve_eposta(self):
        h = Hasta("Çağlar", "Şahin", "12345678901")
        self.assertEqual(h.kullanici_adi, "caglar.sahin")
        self.assertEqual(h.eposta, "caglar.sahin@hastane.com")

    def test_gecersiz_eposta_ve_kullanici_adi(self):
        h = Hasta("Ali", "Veli", "12345678901")
        with self.assertRaises(ValueError):
            h.eposta = "yanlis"
        with self.assertRaises(ValueError):
            h.kullanici_adi = "a"

    def test_sifresiz_kullanici_giris_yapamaz(self):
        self.assertFalse(Hasta("Ali", "Veli", "12345678901").sifre_dogru_mu("123456"))

    def test_misafir_cok_bicimlilik(self):
        m = Misafir("Gizli", "Kişi", "80000000001")
        self.assertEqual(m.rol(), "Misafir")
        self.assertFalse(m.kayitli_mi)
        self.assertTrue(Hasta("A", "B", "12345678901").kayitli_mi)
        self.assertIsInstance(m, Hasta)
        self.assertEqual(m.yetkiler(), ["randevu_al", "randevu_iptal"])


class UygulamaKimlikTest(unittest.TestCase):
    def setUp(self):
        self.uyg = ornek_veri()

    def test_tum_ornek_kullanicilar_ayni_sifreyle_girer(self):
        for k in self.uyg.kullanicilar:
            self.assertIs(self.uyg.kimlik_dogrula(k.kullanici_adi, VARSAYILAN_SIFRE), k)

    def test_yanlis_sifre(self):
        with self.assertRaises(SistemHatasi):
            self.uyg.kimlik_dogrula("ali.demir", "yanlis")
        with self.assertRaises(SistemHatasi):
            self.uyg.kimlik_dogrula("olmayan.kisi", VARSAYILAN_SIFRE)

    def test_kayit(self):
        h = self.uyg.hasta_kaydet("Yeni", "Hasta", "30000000001", "yeni@mail.com", "yeni_hasta",
                                  "sifre123", "sifre123")
        self.assertIs(self.uyg.kimlik_dogrula("yeni_hasta", "sifre123"), h)
        self.assertTrue(h.kayitli_mi)

    def test_kayit_hatalari(self):
        with self.assertRaises(SistemHatasi):    # şifre eşleşmiyor
            self.uyg.hasta_kaydet("A", "B", "30000000002", "a@b.com", "ab_kisi", "sifre123", "baska123")
        with self.assertRaises(SistemHatasi):    # kullanıcı adı alınmış
            self.uyg.hasta_kaydet("A", "B", "30000000003", "a2@b.com", "ali.demir", "sifre123", "sifre123")
        with self.assertRaises(SistemHatasi):    # e-posta alınmış
            self.uyg.hasta_kaydet("A", "B", "30000000004", "ali.demir@hastane.com", "yeni_ad", "sifre123", "sifre123")
        with self.assertRaises(ValueError):      # kısa şifre
            self.uyg.hasta_kaydet("A", "B", "30000000005", "a5@b.com", "yeni_ad5", "123", "123")

    def test_misafir_olusturma_benzersiz_ve_giris_yapamaz(self):
        m1 = self.uyg.misafir_olustur("Ali", "Demir")        # aynı isim olsa da sorun yok
        m2 = self.uyg.misafir_olustur("Ali", "Demir")
        self.assertNotEqual(m1.tc_no, m2.tc_no)
        self.assertNotEqual(m1.kullanici_adi, m2.kullanici_adi)
        with self.assertRaises(SistemHatasi):
            self.uyg.kimlik_dogrula(m1.kullanici_adi, VARSAYILAN_SIFRE)


class KimlikKayitTest(unittest.TestCase):
    def setUp(self):
        self.dosya = os.path.join(tempfile.mkdtemp(), "veri.json")
        self.depo = Depo(self.dosya)

    def test_kimlik_json_ile_korunur_ve_duz_sifre_yazilmaz(self):
        uyg = ornek_veri()
        uyg.hasta_kaydet("Yeni", "Hasta", "30000000001", "yeni@mail.com", "yeni_hasta", "ozel-sifre", "ozel-sifre")
        uyg.misafir_olustur("Gizli", "Misafir")
        self.depo.kaydet(uyg)
        with open(self.dosya, encoding="utf-8") as f:
            icerik = f.read()
        self.assertNotIn("ozel-sifre", icerik)
        self.assertNotIn(f'"{VARSAYILAN_SIFRE}"', icerik)
        yeni = self.depo.yukle()
        self.assertIsNotNone(yeni.kimlik_dogrula("yeni_hasta", "ozel-sifre"))
        self.assertIsNotNone(yeni.kimlik_dogrula("ali.demir", VARSAYILAN_SIFRE))
        misafir = [k for k in yeni.kullanicilar if isinstance(k, Misafir)][0]
        self.assertEqual(misafir.tam_ad, "Gizli Misafir")

    def test_eski_kayitta_sifre_yoksa_varsayilan_atanir(self):
        self.depo.kaydet(ornek_veri())
        with open(self.dosya, encoding="utf-8") as f:
            veri = json.load(f)
        for k in veri["kullanicilar"]:
            for alan in ("sifre", "kullanici_adi", "eposta"):
                k.pop(alan, None)
        with open(self.dosya, "w", encoding="utf-8") as f:
            json.dump(veri, f)
        yeni = self.depo.yukle()
        self.assertIsNotNone(yeni.kimlik_dogrula("ali.demir", VARSAYILAN_SIFRE))


class GirisArayuzTest(unittest.TestCase):
    def setUp(self):
        uygulama_modulu.uyg = ornek_veri()
        uygulama_modulu.depo = None
        self.istemci = uygulama_modulu.app.test_client()

    def test_sifre_ekrani(self):
        sayfa = self.istemci.get("/giris/1").get_data(as_text=True)
        self.assertIn("Ali Demir", sayfa)
        self.assertIn("password", sayfa)

    def test_yanlis_sifre_panel_acmaz(self):
        self.istemci.post("/giris/1", data={"sifre": "yanlis"})
        self.assertEqual(self.istemci.get("/panel").status_code, 302)

    def test_dogru_sifre_panel_acar(self):
        yanit = self.istemci.post("/giris/1", data={"sifre": VARSAYILAN_SIFRE})
        self.assertEqual(yanit.status_code, 302)
        self.assertEqual(self.istemci.get("/panel").status_code, 200)

    def test_kullanici_adi_ile_giris(self):
        self.istemci.post("/giris-kullanici", data={"kullanici_adi": "mehmet.kaya", "sifre": VARSAYILAN_SIFRE})
        self.assertIn("Yönetim", self.istemci.get("/panel").get_data(as_text=True))

    def test_cikis(self):
        self.istemci.post("/giris/1", data={"sifre": VARSAYILAN_SIFRE})
        self.istemci.get("/cikis")
        self.assertEqual(self.istemci.get("/panel").status_code, 302)

    def test_kayit_ve_otomatik_giris(self):
        self.istemci.post("/kayit", data={
            "ad": "Yeni", "soyad": "Hasta", "tc": "30000000001", "eposta": "yeni@mail.com",
            "kullanici_adi": "yeni_hasta", "sifre": "sifre123", "sifre_tekrar": "sifre123"})
        self.assertIn("Yeni Hasta", self.istemci.get("/panel").get_data(as_text=True))
        self.assertIn("yeni_hasta", [k.kullanici_adi for k in uygulama_modulu.uyg.kullanicilar])

    def test_hatali_kayit_kullanici_olusturmaz(self):
        onceki = len(uygulama_modulu.uyg.kullanicilar)
        self.istemci.post("/kayit", data={
            "ad": "Yeni", "soyad": "Hasta", "tc": "30000000001", "eposta": "yeni@mail.com",
            "kullanici_adi": "yeni_hasta", "sifre": "sifre123", "sifre_tekrar": "farkli123"})
        self.assertEqual(len(uygulama_modulu.uyg.kullanicilar), onceki)

    def test_misafir_randevu_alir_ama_listede_gorunmez(self):
        self.istemci.post("/misafir", data={"ad": "Gizli", "soyad": "Kişi"})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Misafir olarak devam ediyorsunuz", sayfa)
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        sayfa = self.istemci.get("/panel").get_data(as_text=True)
        self.assertIn("Bekliyor", sayfa)                       # bu oturumda randevusunu görür
        for yol in ("/?grup=kullanici", "/"):
            self.assertNotIn("Gizli Kişi", self.istemci.get(yol).get_data(as_text=True))

    def test_misafir_cikis_sonrasi_eski_randevulari_goremez(self):
        self.istemci.post("/misafir", data={"ad": "Gizli", "soyad": "Kişi"})
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        self.istemci.get("/cikis")
        self.istemci.post("/misafir", data={"ad": "Gizli", "soyad": "Kişi"})   # aynı isimle yeniden
        self.assertIn("Henüz randevunuz yok", self.istemci.get("/panel").get_data(as_text=True))
        # eski misafir hesabına giriş de yapılamaz
        sira = [i for i, k in enumerate(uygulama_modulu.uyg.kullanicilar) if isinstance(k, Misafir)][0]
        self.istemci.get("/cikis")
        self.istemci.post(f"/giris/{sira}", data={"sifre": VARSAYILAN_SIFRE})
        self.assertEqual(self.istemci.get("/panel").status_code, 302)

    def test_kayitli_kullanici_eski_randevularini_gorur(self):
        self.istemci.post("/giris/1", data={"sifre": VARSAYILAN_SIFRE})
        self.istemci.post("/hasta/randevu-al", data={
            "h": 0, "k": 0, "d": 0, "s": 0, "zaman": "2026-10-28T09:00:00"})
        self.istemci.get("/cikis")
        self.istemci.post("/giris/1", data={"sifre": VARSAYILAN_SIFRE})
        self.assertIn("Bekliyor", self.istemci.get("/panel").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
