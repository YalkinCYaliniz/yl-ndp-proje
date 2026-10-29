"""JSON ile kaydetme / yükleme."""
import json
import os
from datetime import datetime, time

from randevu.guvenlik import Sifre
from randevu.kullanici import (Hasta, Misafir, Doktor, Yonetici, Asistan, Hemsire,
                               Teknisyen)
from randevu.kurum import Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.randevu import Randevu, RandevuDurumu
from randevu.recete import Recete
from randevu.uygulama import Uygulama, VARSAYILAN_SIFRE


class Depo:
    """Uygulama verisini bir JSON dosyasına yazar ve oradan geri okur."""

    def __init__(self, dosya: str):
        self._dosya = dosya

    def var_mi(self) -> bool:
        return os.path.exists(self._dosya)

    # ---------------- KAYDET ----------------
    def kaydet(self, uyg: Uygulama) -> None:
        veri = {
            "kurum": uyg.kurum.ad,
            "kullanicilar": [k.sozluge() for k in uyg.kullanicilar],
            "hastaneler": [self._hastane_sozluge(h) for h in uyg.kurum.hastaneler],
            "randevular": [self._randevu_sozluge(r) for r in uyg.sistem.randevular],
        }
        with open(self._dosya, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)

    def _hastane_sozluge(self, h) -> dict:
        return {
            "ad": h.ad, "acilis": h.acilis.isoformat(), "kapanis": h.kapanis.isoformat(),
            "klinikler": [{
                "ad": k.ad,
                "hizmetler": [s.sozluge() for s in k.hizmetler],   # çok biçimlilik
                "doktorlar": [d.tc_no for d in k.doktorlar],
                "personel": [p.tc_no for p in k.personeller],
                # sadece hizmet seçimi yapmış doktorlar: {tc: [hizmet adları]}
                "doktor_hizmetleri": {
                    d.tc_no: [s.ad for s in d.ozel_hizmetler(k)]
                    for d in k.doktorlar if d.ozel_hizmetler(k) is not None},
            } for k in h.klinikler],
        }

    def _randevu_sozluge(self, r) -> dict:
        return {
            "hasta": r.hasta.tc_no, "hastane": r.hastane.ad, "klinik": r.klinik.ad,
            "doktor": r.doktor.tc_no, "hizmet": r.hizmet.ad,
            "baslangic": r.baslangic.isoformat(), "durum": r.durum.name,
            "odenen_tutar": r.odenen_tutar,
            "recete": r.recete.sozluge() if r.recete else None,
        }

    # ---------------- YÜKLE ----------------
    def yukle(self) -> Uygulama:
        with open(self._dosya, encoding="utf-8") as f:
            veri = json.load(f)

        uyg = Uygulama()
        uyg.kurum.ad = veri["kurum"]
        varsayilan = Sifre.olustur(VARSAYILAN_SIFRE)     # eski kayıtlarda şifre yoksa
        for k in veri["kullanicilar"]:
            kisi = self._kullanici_olustur(k)
            self._kimlik_yukle(kisi, k, varsayilan)
            uyg.kullanici_ekle(kisi)
        kisiler = {k.tc_no: k for k in uyg.kullanicilar}

        for h in veri["hastaneler"]:
            hastane = Hastane(h["ad"], time.fromisoformat(h["acilis"]), time.fromisoformat(h["kapanis"]))
            uyg.kurum.hastane_ekle(hastane)
            for k in h["klinikler"]:
                klinik = Klinik(k["ad"])
                hastane.klinik_ekle(klinik)
                for s in k["hizmetler"]:
                    klinik.hizmet_ekle(self._hizmet_olustur(s))
                for tc in k["doktorlar"]:
                    klinik.doktor_ekle(kisiler[tc])
                for tc in k.get("personel", []):
                    klinik.personel_ekle(kisiler[tc])
                for tc, adlar in k.get("doktor_hizmetleri", {}).items():
                    kisiler[tc].hizmet_tanimla(
                        klinik, [s for s in klinik.hizmetler if s.ad in adlar])

        # Asistan-doktor bağlantıları klinik atamalarından sonra kurulur
        for k in veri["kullanicilar"]:
            if k["tur"] == "Asistan" and k.get("doktor"):
                kisiler[k["tc_no"]].doktora_bagla(kisiler[k["doktor"]])

        for r in veri["randevular"]:
            hastane = uyg.kurum.hastane_bul(r["hastane"])
            klinik = hastane.klinik_bul(r["klinik"])
            hizmet = [s for s in klinik.hizmetler if s.ad == r["hizmet"]][0]
            uyg.sistem.randevu_yukle(Randevu(
                kisiler[r["hasta"]], hastane, klinik, kisiler[r["doktor"]], hizmet,
                datetime.fromisoformat(r["baslangic"]),
                RandevuDurumu[r["durum"]], r["odenen_tutar"],
                Recete.sozlukten(r["recete"]) if r.get("recete") else None))
        return uyg

    def _kimlik_yukle(self, kisi, k: dict, varsayilan) -> None:
        """Kullanıcı adı, e-posta ve şifreyi geri yükler."""
        if k.get("kullanici_adi"):
            kisi.kullanici_adi = k["kullanici_adi"]
        if k.get("eposta"):
            kisi.eposta = k["eposta"]
        if k.get("sifre"):
            kisi.sifre_belirle(Sifre.sozlukten(k["sifre"]))
        elif kisi.kayitli_mi:
            kisi.sifre_belirle(varsayilan)

    def _kullanici_olustur(self, k: dict):
        tur = k["tur"]
        if tur == "Misafir":
            return Misafir(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Hasta":
            return Hasta(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Yonetici":
            return Yonetici(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Asistan":
            kisi = Asistan(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        elif tur == "Teknisyen":
            kisi = Teknisyen(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"], k["cihaz"])
        elif tur == "Hemsire":
            kisi = Hemsire(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        else:
            kisi = Doktor(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        for baslangic, bitis in k["musaitlik"]:
            kisi.musaitlik_yukle(datetime.fromisoformat(baslangic), datetime.fromisoformat(bitis))
        return kisi

    def _hizmet_olustur(self, s: dict):
        if s["tur"] == "Radyoloji":
            return Radyoloji(s["ad"], s["sure_dk"], s["taban_ucret"], s["cihaz_ucreti"])
        if s["tur"] == "Laboratuvar":
            return Laboratuvar(s["ad"], s["sure_dk"], s["taban_ucret"], s["tahlil_sayisi"])
        return Muayene(s["ad"], s["sure_dk"], s["taban_ucret"])
