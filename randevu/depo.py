import json
import os
from datetime import datetime, time

from randevu.guvenlik import Sifre
from randevu.kullanici import (Hasta, Misafir, Doktor, Yonetici, HastaneYoneticisi,
                               KlinikYoneticisi, Asistan, Hemsire, Teknisyen)
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
            "gorevler": uyg.gorevler,
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
            "id": r.id,
            "hasta": r.hasta.tc_no, "hastane": r.hastane.ad, "klinik": r.klinik.ad,
            "doktor": r.doktor.tc_no, "hizmet": r.hizmet.ad,
            "baslangic": r.baslangic.isoformat(), "durum": r.durum.name,
            "odenen_tutar": r.odenen_tutar,
            "recete": r.recete.sozluge() if r.recete else None,
            "kabul_zamani": r.kabul_zamani.isoformat() if r.kabul_zamani else None,
            "kabul_eden": r.kabul_eden.tc_no if hasattr(r.kabul_eden, "tc_no") else (str(r.kabul_eden) if r.kabul_eden else None),
            "gelmedi": r.gelmedi_mi,
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
                    klinik.doktor_yukle(kisiler[tc])
                for tc in k.get("personel", []):
                    klinik.personel_ekle(kisiler[tc])
                for tc, adlar in k.get("doktor_hizmetleri", {}).items():
                    kisiler[tc].hizmet_tanimla(
                        klinik, [s for s in klinik.hizmetler if s.ad in adlar])

        # Asistan-doktor ve hastane/klinik yöneticisi bağlantıları kurulduktan sonra atanır
        for k in veri["kullanicilar"]:
            if k["tur"] == "Asistan" and k.get("doktor"):
                kisiler[k["tc_no"]].doktora_bagla(kisiler[k["doktor"]])
            elif k["tur"] == "HastaneYoneticisi" and k.get("hastane"):
                kisiler[k["tc_no"]].hastane_ata(uyg.kurum.hastane_bul(k["hastane"]))
            elif k["tur"] == "KlinikYoneticisi" and k.get("hastane") and k.get("klinik"):
                hastane = uyg.kurum.hastane_bul(k["hastane"])
                kisiler[k["tc_no"]].klinik_ata(hastane, hastane.klinik_bul(k["klinik"]))

        # Doktorların müsaitliklerindeki hastane adlarını kurumdaki gerçek Hastane nesnelerine bağla
        for k in uyg.kullanicilar:
            if isinstance(k, Doktor):
                k.hastane_referanslarini_bagla(uyg.kurum)

        for r in veri["randevular"]:
            hastane = uyg.kurum.hastane_bul(r["hastane"])
            if not hastane:
                continue
            klinik = hastane.klinik_bul(r["klinik"])
            if not klinik:
                continue
            hizmetler = [s for s in klinik.hizmetler if s.ad == r["hizmet"]]
            if not hizmetler:
                continue
            hizmet = hizmetler[0]
            kabul_zamani = datetime.fromisoformat(r["kabul_zamani"]) if r.get("kabul_zamani") else None
            kabul_eden = kisiler.get(r.get("kabul_eden")) if r.get("kabul_eden") else None
            gelmedi = bool(r.get("gelmedi", False))
            uyg.sistem.randevu_yukle(Randevu(
                kisiler[r["hasta"]], hastane, klinik, kisiler[r["doktor"]], hizmet,
                datetime.fromisoformat(r["baslangic"]),
                RandevuDurumu[r["durum"]], r["odenen_tutar"],
                Recete.sozlukten(r["recete"]) if r.get("recete") else None,
                kabul_zamani=kabul_zamani, kabul_eden=kabul_eden, gelmedi=gelmedi,
                id=r.get("id")))

        if "gorevler" in veri and isinstance(veri["gorevler"], dict):
            for tur, liste in veri["gorevler"].items():
                if tur in uyg.gorevler:
                    for g in liste:
                        if not any(mevcut.lower() == g.lower() for mevcut in uyg.gorevler[tur]):
                            uyg.gorevler[tur].append(g)

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
        if k.get("ceza_bitis") and hasattr(kisi, "ceza_bitis_yukle"):
            kisi.ceza_bitis_yukle(datetime.fromisoformat(k["ceza_bitis"]))

    def _kullanici_olustur(self, k: dict):
        tur = k["tur"]
        if tur == "Misafir":
            return Misafir(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Hasta":
            return Hasta(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Yonetici":
            return Yonetici(k["ad"], k["soyad"], k["tc_no"])
        if tur == "HastaneYoneticisi":
            return HastaneYoneticisi(k["ad"], k["soyad"], k["tc_no"])
        if tur == "KlinikYoneticisi":
            return KlinikYoneticisi(k["ad"], k["soyad"], k["tc_no"])
        if tur == "Asistan":
            return Asistan(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        if tur == "Teknisyen":
            return Teknisyen(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"], k["cihaz"])
        if tur == "Hemsire":
            return Hemsire(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        doktor = Doktor(k["ad"], k["soyad"], k["tc_no"], k["uzmanlik"])
        for m in k.get("musaitlik", []):
            b = datetime.fromisoformat(m[0])
            s = datetime.fromisoformat(m[1])
            h = m[2] if len(m) >= 3 else None
            doktor.musaitlik_yukle(b, s, h)
        return doktor

    def _hizmet_olustur(self, s: dict):
        if s["tur"] == "Radyoloji":
            return Radyoloji(s["ad"], s["sure_dk"], s["taban_ucret"], s["cihaz_ucreti"])
        if s["tur"] == "Laboratuvar":
            return Laboratuvar(s["ad"], s["sure_dk"], s["taban_ucret"], s["tahlil_sayisi"])
        return Muayene(s["ad"], s["sure_dk"], s["taban_ucret"])
