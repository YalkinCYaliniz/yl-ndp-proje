from datetime import datetime, timedelta
from enum import Enum
import uuid

from randevu.hatalar import RandevuHatasi


def su_an() -> datetime:
    """Gerçek saat (testlerde sahte saatle değiştirilebilir)."""
    return datetime.now()


class RandevuDurumu(Enum):
    BEKLIYOR = "Bekliyor"
    ONAYLANDI = "Onaylandı"
    REDDEDILDI = "Reddedildi"
    IPTAL = "İptal"


def tarih_saat_yaz(zaman) -> str:
    """datetime -> '14.10.2026 13:30'"""
    return zaman.strftime("%d.%m.%Y %H:%M")


class Randevu:
    """Tek bir randevu: hasta, hastane, klinik, doktor, hizmet ve tarih-saat."""

    # Demo için: False iken 'Hasta gelmedi' işareti randevu saatine bakmaz.
    # Gerçek kullanımda True yapılırsa saati gelmemiş randevu için işlem reddedilir.
    ZAMAN_KONTROLU = False

    def __init__(self, hasta, hastane, klinik, doktor, hizmet, baslangic,
                 durum=None, odenen_tutar=None, recete=None,
                 kabul_zamani=None, kabul_eden=None, gelmedi=False,
                 id: str = None):
        self.hasta = hasta
        self.hastane = hastane
        self.klinik = klinik
        self.doktor = doktor
        self.hizmet = hizmet
        self.baslangic = baslangic          # datetime
        self.id = str(id or uuid.uuid4().hex[:8])
        # Yeni randevu bekler; dosyadan yüklenirken durum ve ödeme verilir
        self._durum = durum or RandevuDurumu.BEKLIYOR
        self._odenen_tutar = odenen_tutar   # ödeme yapılınca dolar
        self._recete = recete               # doktor yazınca dolar
        self._kabul_zamani = kabul_zamani   # işlem zamanı (datetime)
        self._kabul_eden = kabul_eden       # işlemi yapan hemşire
        self._gelmedi = gelmedi             # hasta gelmedi mi

    @property
    def kabul_edildi_mi(self) -> bool:
        return self._kabul_zamani is not None and not self._gelmedi

    @property
    def gelmedi_mi(self) -> bool:
        return bool(self._gelmedi)

    @property
    def kabul_zamani(self):
        return self._kabul_zamani

    @property
    def kabul_eden(self):
        return self._kabul_eden

    @property
    def kabul_metni(self) -> str:
        if self._gelmedi:
            saat = self._kabul_zamani.strftime("%H:%M") if self._kabul_zamani else ""
            hemsire_adi = self._kabul_eden.tam_ad if hasattr(self._kabul_eden, "tam_ad") else (str(self._kabul_eden) if self._kabul_eden else "Hemşire")
            return f"Hasta gelmedi ({saat} · {hemsire_adi})" if saat else f"Hasta gelmedi ({hemsire_adi})"
        if not self.kabul_edildi_mi:
            return ""
        saat = self._kabul_zamani.strftime("%H:%M")
        hemsire_adi = self._kabul_eden.tam_ad if hasattr(self._kabul_eden, "tam_ad") else (str(self._kabul_eden) if self._kabul_eden else "Hemşire")
        return f"Hasta geldi ({saat} · {hemsire_adi})"

    def hasta_kabul_et(self, hemsire, zaman=None, odeme=None) -> None:
        """Hasta geldiğinde hemşire kabul işlemini yapar. Randevu durumu Onaylandı olarak kalır.

        Ödeme yapılmamışsa kabul ancak 'odeme' verilerek (ödeme yerinde alınarak) yapılır."""
        if self._durum != RandevuDurumu.ONAYLANDI:
            raise RandevuHatasi("Sadece onaylı randevuların hasta kabulü yapılabilir.")
        if self.kabul_edildi_mi:
            raise RandevuHatasi("Bu randevunun hasta kabulü zaten yapılmış.")
        if self.gelmedi_mi:
            raise RandevuHatasi("Bu randevu için 'Hasta gelmedi' işaretlenmiş.")
        if not self.odendi_mi:
            if odeme is None:
                raise RandevuHatasi("Ödeme yapılmamış; hasta kabulü için ödeme alınmalıdır.")
            self.odeme_yap(odeme)
        self._kabul_zamani = zaman or datetime.now()
        self._kabul_eden = hemsire
        self._gelmedi = False

    def hasta_gelmedi_isaretle(self, hemsire, zaman=None) -> None:
        """Hasta gelmediğinde hemşire tarafından işaretlenir. Hasta 24 saat randevu alamaz."""
        if self._durum != RandevuDurumu.ONAYLANDI:
            raise RandevuHatasi("Sadece onaylı randevular için hasta gelmedi işaretlenebilir.")
        if self.kabul_edildi_mi:
            raise RandevuHatasi("Hasta kabulü yapılmış randevu için 'Hasta gelmedi' işaretlenemez.")
        if self.gelmedi_mi:
            raise RandevuHatasi("Bu randevu için zaten 'Hasta gelmedi' işaretlenmiş.")
        islem_zamani = zaman or datetime.now()
        if self.ZAMAN_KONTROLU and self.baslangic > islem_zamani:
            raise RandevuHatasi("Randevu saati gelmeden 'Hasta gelmedi' işaretlenemez.")
        self._kabul_zamani = islem_zamani
        self._kabul_eden = hemsire
        self._gelmedi = True
        if hasattr(self.hasta, "ceza_ver"):
            self.hasta.ceza_ver(24, islem_zamani)

    @property
    def recete(self):
        return self._recete

    def recete_ekle(self, recete) -> None:
        """Sadece onaylı randevuya reçete yazılabilir; yenisi eskisinin yerine geçer."""
        if self._durum != RandevuDurumu.ONAYLANDI:
            raise RandevuHatasi("Sadece onaylı randevu için reçete yazılabilir.")
        if not self.kabul_edildi_mi:
            raise RandevuHatasi("Reçete, hasta kabulü (Hasta geldi) yapıldıktan sonra yazılabilir.")
        self._recete = recete

    @property
    def odendi_mi(self) -> bool:
        return self._odenen_tutar is not None

    @property
    def odenen_tutar(self):
        return self._odenen_tutar

    def odeme_yap(self, odeme) -> float:
        """Onaylı randevu için seçilen yönteme göre ödeme alır (çok biçimlilik)."""
        if self._durum != RandevuDurumu.ONAYLANDI:
            raise RandevuHatasi("Sadece onaylı randevu için ödeme yapılabilir.")
        if self.odendi_mi:
            raise RandevuHatasi("Bu randevunun ödemesi zaten yapılmış.")
        self._odenen_tutar = odeme.toplam_hesapla(self.hizmet.ucret)
        return self._odenen_tutar

    @property
    def bitis(self):
        return self.baslangic + timedelta(minutes=self.hizmet.sure_dk)

    @property
    def durum(self) -> RandevuDurumu:
        return self._durum

    @property
    def aktif_mi(self) -> bool:
        """İptal/red edilmemiş randevu zamanı doldurur."""
        return self._durum not in (RandevuDurumu.IPTAL, RandevuDurumu.REDDEDILDI)

    def onayla(self) -> None:
        if self._durum != RandevuDurumu.BEKLIYOR:
            raise RandevuHatasi("Sadece bekleyen randevu onaylanabilir.")
        self._durum = RandevuDurumu.ONAYLANDI

    def reddet(self) -> None:
        if self._durum != RandevuDurumu.BEKLIYOR:
            raise RandevuHatasi("Sadece bekleyen randevu reddedilebilir.")
        self._durum = RandevuDurumu.REDDEDILDI

    def iptal(self) -> None:
        if not self.aktif_mi:
            raise RandevuHatasi("Bu randevu zaten iptal/red edilmiş.")
        if self.odendi_mi:
            raise RandevuHatasi("Ödemesi yapılmış randevu iptal edilemez.")
        if self.gelmedi_mi:
            raise RandevuHatasi("'Hasta gelmedi' olarak işaretlenmiş randevu iptal edilemez.")
        self._durum = RandevuDurumu.IPTAL

    def cakisiyor_mu(self, baslangic, bitis) -> bool:
        """Verilen zaman aralığıyla kesişiyor mu?"""
        return self.aktif_mi and self.baslangic < bitis and baslangic < self.bitis

    def hasta_icin_uygun_mu(self, baslangic) -> bool:
        """Aynı gün için hastanın iki randevu başlangıcı arasında en az 1 saat olmalı."""
        if not self.aktif_mi or self.baslangic.date() != baslangic.date():
            return True
        return abs(baslangic - self.baslangic) >= timedelta(hours=1)

    def __str__(self) -> str:
        return (f"{tarih_saat_yaz(self.baslangic)} | {self.hastane.ad} | {self.klinik.ad} | "
                f"{self.doktor.tam_ad} | {self.hizmet.ad} | {self.hasta.tam_ad} | "
                f"{self.hizmet.ucret} TL | {self.durum.value}")


class Slot:
    """Tablodaki tek bir saat kutusu. Boşsa yeşil, doluysa kırmızı gösterilecek."""

    def __init__(self, baslangic, dolu: bool, randevu=None):
        self.baslangic = baslangic
        self.dolu = dolu
        self.randevu = randevu          # doluysa hangi randevu olduğu

    @property
    def renk(self) -> str:
        return "kırmızı" if self.dolu else "yeşil"

    def __str__(self) -> str:
        durum = "DOLU" if self.dolu else "BOŞ"
        return f"{tarih_saat_yaz(self.baslangic)} -> {durum} ({self.renk})"


class RandevuSistemi:
    """Randevuları oluşturur; müsaitlik ve çakışma kurallarını kontrol eder."""

    def __init__(self, saat=None):
        self._randevular = []
        self._saat = saat           # test için sahte saat verilebilir; yoksa gerçek saat

    def simdi(self) -> datetime:
        return self._saat() if self._saat else su_an()

    @property
    def randevular(self) -> tuple:
        return tuple(self._randevular)

    def randevu_yukle(self, randevu) -> None:
        """Dosyadan okunan randevuyu kural kontrolü yapmadan ekler."""
        self._randevular.append(randevu)

    def randevu_bul(self, randevu_id):
        """Sabit randevu ID'si veya geriye uyumluluk için indeks ile randevuyu bulur."""
        for r in self._randevular:
            if str(r.id) == str(randevu_id):
                return r
        if str(randevu_id).isdigit():
            sira = int(randevu_id)
            if 0 <= sira < len(self._randevular):
                return self._randevular[sira]
        return None

    def randevulari_sil(self, kosul) -> None:
        """Koşulu sağlayan randevuları kayıttan çıkarır (hastane/klinik silinirken kullanılır)."""
        self._randevular = [r for r in self._randevular if not kosul(r)]

    def gelecek_aktif_randevu_var_mi(self, kosul) -> bool:
        """Koşulu sağlayan, henüz bitmemiş aktif (bekleyen/onaylı) randevu var mı?"""
        simdi = self.simdi()
        return any(kosul(r) and r.aktif_mi and r.bitis > simdi for r in self._randevular)

    def hastanin_randevulari(self, hasta) -> list:
        """Hastanın tüm randevuları (geçmiş dahil, iptaller de görünür)."""
        return [r for r in self._randevular if r.hasta is hasta]

    def doktorun_randevulari(self, doktor) -> list:
        return [r for r in self._randevular if r.doktor is doktor]

    def bekleyen_randevular(self, doktor) -> list:
        """Doktorun onay bekleyen randevuları."""
        return [r for r in self.doktorun_randevulari(doktor)
                if r.durum == RandevuDurumu.BEKLIYOR]

    def _cakisan_randevu(self, doktor, baslangic, bitis):
        """Aralıkla çakışan randevuyu döndürür, yoksa None."""
        for r in self._randevular:
            if r.doktor is doktor and r.cakisiyor_mu(baslangic, bitis):
                return r
        return None

    def _dolu_mu(self, doktor, baslangic, bitis) -> bool:
        return self._cakisan_randevu(doktor, baslangic, bitis) is not None

    def musait_gunler(self, hastane, doktor, hizmet) -> list:
        """Bugünden itibaren doktorun çalıştığı günler ve boş saat sayısı: [(date, bos_sayisi)]."""
        gunler = sorted({
            m[0].date() for m in doktor.musaitlik
            if m[0].date() >= self.simdi().date() and (getattr(m, "hastane", None) in (None, hastane))
        })
        sonuc = []
        for gun in gunler:
            slotlar = self.saat_tablosu(hastane, doktor, hizmet, gun, gecmisi_gizle=True)
            if slotlar:                 # günün tüm saatleri geçmişte kaldıysa gösterilmez
                sonuc.append((gun, len([s for s in slotlar if not s.dolu])))
        return sonuc

    def saat_tablosu(self, hastane, doktor, hizmet, gun, gecmisi_gizle=False) -> list:
        """Doktorun o günkü tüm saatleri (boş/dolu). Frontend bunu tablo yapacak.

        gecmisi_gizle=True ise şu andan önceki saatler listelenmez (hasta ekranı için).
        """
        slotlar = []
        if hizmet.sure_dk <= 0:
            return slotlar
        sure = timedelta(minutes=hizmet.sure_dk)
        for baslangic, bitis in doktor.musaitlik_listesi(gun, hastane):
            zaman = baslangic
            while zaman + sure <= bitis:
                if gecmisi_gizle and zaman <= self.simdi():
                    zaman += sure
                    continue
                if hastane.acik_mi(zaman, zaman + sure):
                    randevu = self._cakisan_randevu(doktor, zaman, zaman + sure)
                    slotlar.append(Slot(zaman, randevu is not None, randevu))
                zaman += sure
        return slotlar

    def en_yakin_bos(self, hastane, doktor, hizmet, sonra):
        """'sonra' zamanından itibaren doktorun ilk boş saatini (Slot) döndürür, yoksa None."""
        gunler = sorted({
            m[0].date() for m in doktor.musaitlik
            if m[0].date() >= sonra.date() and (getattr(m, "hastane", None) in (None, hastane))
        })
        for gun in gunler:
            slotlar = sorted(self.saat_tablosu(hastane, doktor, hizmet, gun),
                             key=lambda s: s.baslangic)
            for slot in slotlar:
                if not slot.dolu and slot.baslangic >= sonra:
                    return slot
        return None

    def randevu_olustur(self, hasta, hastane, klinik, doktor, hizmet, baslangic) -> Randevu:
        if hasattr(hasta, "randevu_engeli_var_mi") and hasta.randevu_engeli_var_mi(self.simdi()):
            bitis_metni = hasta.engel_bitis_metni(self.simdi())
            raise RandevuHatasi(f"Randevunuza gelmediğiniz için {bitis_metni} tarihine kadar yeni randevu alamazsınız.")

        yeni = Randevu(hasta, hastane, klinik, doktor, hizmet, baslangic)

        if yeni.baslangic <= self.simdi():
            raise RandevuHatasi("Geçmiş tarih/saat için randevu alınamaz.")
        if klinik not in hastane.klinikler:
            raise RandevuHatasi("Bu klinik seçilen hastanede yok.")
        if doktor not in klinik.doktorlar:
            raise RandevuHatasi("Doktor bu klinikte çalışmıyor.")
        if hizmet not in klinik.hizmetler:
            raise RandevuHatasi("Bu hizmet seçilen klinikte verilmiyor.")
        if not doktor.hizmet_sunar_mi(klinik, hizmet):
            raise RandevuHatasi("Doktor bu hizmeti vermiyor.")
        if not hastane.acik_mi(yeni.baslangic, yeni.bitis):
            raise RandevuHatasi("Hastane bu saatte kapalı.")
        if not doktor.musait_mi(yeni.baslangic, yeni.bitis, hastane):
            raise RandevuHatasi("Doktor bu tarih/saatte müsait değil.")
        if self._dolu_mu(doktor, yeni.baslangic, yeni.bitis):
            raise RandevuHatasi("Randevu çakışması var.")
        for r in self.hastanin_randevulari(hasta):
            if r.cakisiyor_mu(yeni.baslangic, yeni.bitis) or not r.hasta_icin_uygun_mu(yeni.baslangic):
                raise RandevuHatasi("Aynı gün randevularınız arasında en az 1 saat olmalıdır.")

        self._randevular.append(yeni)
        return yeni
