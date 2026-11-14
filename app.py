
from datetime import date, datetime, time, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for

from randevu.hatalar import SistemHatasi
from randevu.kullanici import (Hasta, Doktor, Yonetici, SaglikPersoneli, Asistan,
                               Hemsire, Teknisyen, HastaneYoneticisi, KlinikYoneticisi)
from randevu.kurum import Hastane, Klinik, Muayene, Radyoloji, Laboratuvar
from randevu.odeme import NakitOdeme, KartOdeme, SigortaOdeme
from randevu.arama import Arama, sadelestir
from randevu.depo import Depo
from randevu.ornek_veri import ornek_veri
from randevu.uygulama import VARSAYILAN_SIFRE

app = Flask(__name__)
app.secret_key = "ndp-proje-gelistirme"
depo = Depo("veri.json")
# Kayıt dosyası varsa oradan yükle, yoksa örnek veriyle başla
uyg = depo.yukle() if depo.var_mi() else ornek_veri(date.today() + timedelta(days=1))

ODEMELER = {"nakit": NakitOdeme(), "kart": KartOdeme(3), "sigorta": SigortaOdeme()}


def simdiki_kullanici():
    sira = session.get("kullanici")
    if sira is None:
        return None
    return uyg.kullanicilar[sira]


def tum_klinikler() -> list:
    """[(hastane, klinik), ...] - formlardaki 'Hastane / Klinik' seçimi için."""
    return [(h, k) for h in uyg.kurum.hastaneler for k in h.klinikler]


def tum_hizmetler() -> list:
    """[(hastane, klinik, hizmet), ...] - formlardaki 'Hizmet sil' seçimi için."""
    return [(h, k, s) for h in uyg.kurum.hastaneler for k in h.klinikler for s in k.hizmetler]


def kaydet() -> None:
    if depo:
        depo.kaydet(uyg)


def calistir(islem, basari: str):
    """İşlemi dener; SistemHatasi olursa kullanıcıya mesaj gösterir."""
    try:
        islem()
        kaydet()                    # her başarılı işlemden sonra dosyaya yaz
        flash(basari, "ok")
    except (SistemHatasi, ValueError, IndexError, KeyError) as hata:
        flash(str(hata) or "Geçersiz seçim.", "hata")
    except AttributeError:      # rolün böyle bir metodu yok (yetkisiz)
        flash("Bu işlem için yetkiniz yok.", "hata")


GRUPLAR = {
    "admin": ("Admin", Yonetici),
    "personel": ("Personeller", SaglikPersoneli),
    "kullanici": ("Kullanıcılar", Hasta),
}
ROL_SIRASI = ["Doktor", "Asistan", "Hemşire", "Teknisyen"]
YONETICI_SIRASI = ["Admin", "Hastane Yöneticisi", "Klinik Yöneticisi"]


@app.route("/")
def giris():
    """Ana sayfa: Admin / Personeller / Kullanıcılar kartları; tıklanan grup listelenir."""
    gruplar = []
    for anahtar, (baslik, sinif) in GRUPLAR.items():
        uyeler = [(sira, k) for sira, k in enumerate(uyg.kullanicilar)
                  if isinstance(k, sinif) and k.kayitli_mi]
        gruplar.append((anahtar, baslik, len(uyeler)))
    secili = request.args.get("grup")
    liste = []
    if secili in GRUPLAR:
        sinif = GRUPLAR[secili][1]
        liste = [(sira, k) for sira, k in enumerate(uyg.kullanicilar)
                 if isinstance(k, sinif) and k.kayitli_mi]
    kategoriler = []
    secili_rol = request.args.get("rol", "")
    if secili in ("personel", "admin"):
        siralamalar = ROL_SIRASI if secili == "personel" else YONETICI_SIRASI
        kategoriler = [(rol, len([k for _, k in liste if k.rol() == rol])) for rol in siralamalar]
        liste.sort(key=lambda cift: siralamalar.index(cift[1].rol()))
        if secili_rol in siralamalar:
            liste = [(sira, k) for sira, k in liste if k.rol() == secili_rol]
    isim = request.args.get("q", "").strip()
    if isim and secili:
        aranan = sadelestir(isim)
        liste = [(sira, k) for sira, k in liste if aranan in sadelestir(k.tam_ad)]
    hastaneler = uyg.kurum.hastaneler
    secili_hastane = request.args.get("hastane", "").strip()
    if secili_hastane and secili in ("personel", "admin"):
        liste = [(sira, k) for sira, k in liste
                 if any(secili_hastane == h.ad for h in getattr(k, 'hastaneler', lambda kurum: [])(uyg.kurum))]
    return render_template("giris.html", gruplar=gruplar, secili=secili, liste=liste,
                           kategoriler=kategoriler, secili_rol=secili_rol, isim=isim,
                           hastaneler=hastaneler, secili_hastane=secili_hastane,
                           baslik=GRUPLAR[secili][0] if secili in GRUPLAR else "")


@app.route("/giris/<int:sira>", methods=["GET", "POST"])
def giris_yap(sira):
    """Listeden seçilen kullanıcı için şifre sorar."""
    if sira >= len(uyg.kullanicilar) or not uyg.kullanicilar[sira].kayitli_mi:
        flash("Bu hesapla giriş yapılamaz.", "hata")
        return redirect(url_for("giris"))
    secilen = uyg.kullanicilar[sira]
    if request.method == "POST":
        if secilen.sifre_dogru_mu(request.form.get("sifre", "")):
            session["kullanici"] = sira
            return redirect(url_for("panel"))
        flash("Şifre hatalı.", "hata")
    return render_template("sifre_giris.html", secilen=secilen, varsayilan=VARSAYILAN_SIFRE)


@app.post("/giris-kullanici")
def giris_kullanici():
    """Kullanıcı adı ve şifre ile giriş."""
    try:
        kisi = uyg.kimlik_dogrula(request.form.get("kullanici_adi", ""), request.form.get("sifre", ""))
        session["kullanici"] = uyg.kullanicilar.index(kisi)
        return redirect(url_for("panel"))
    except SistemHatasi as hata:
        flash(str(hata), "hata")
        return redirect(url_for("giris"))


@app.route("/kayit", methods=["GET", "POST"])
def kayit():
    """Yeni hasta kaydı: e-posta, kullanıcı adı ve şifre."""
    if request.method == "POST":
        f = request.form
        try:
            hasta = uyg.hasta_kaydet(f["ad"], f["soyad"], f["tc"], f["eposta"],
                                     f["kullanici_adi"], f["sifre"], f["sifre_tekrar"])
            kaydet()
            session["kullanici"] = uyg.kullanicilar.index(hasta)
            flash("Kayıt tamamlandı, hoş geldiniz.", "ok")
            return redirect(url_for("panel"))
        except (SistemHatasi, ValueError) as hata:
            flash(str(hata), "hata")
    return render_template("kayit.html", form=request.form)


@app.route("/misafir", methods=["GET", "POST"])
def misafir():
    """Kayıt olmadan devam: sadece ad soyad sorulur, eski randevular görüntülenmez."""
    if request.method == "POST":
        try:
            kisi = uyg.misafir_olustur(request.form["ad"].strip(), request.form["soyad"].strip())
            kaydet()
            session["kullanici"] = uyg.kullanicilar.index(kisi)
            return redirect(url_for("panel"))
        except (SistemHatasi, ValueError) as hata:
            flash(str(hata), "hata")
    return render_template("misafir.html", form=request.form)


@app.route("/cikis")
def cikis():
    session.clear()
    return redirect(url_for("giris"))


@app.route("/panel")
def panel():
    kullanici = simdiki_kullanici()
    if kullanici is None:
        return redirect(url_for("giris"))
    # Çok biçimlilik: aynı panel, rolüne göre farklı sayfa
    if isinstance(kullanici, Yonetici):
        return admin_sayfasi(kullanici)
    if isinstance(kullanici, Doktor):
        return doktor_sayfasi(kullanici)
    if isinstance(kullanici, SaglikPersoneli):      # asistan, hemşire, teknisyen
        return personel_sayfasi(kullanici)
    return hasta_sayfasi(kullanici)


# ---------------- HASTA ----------------
def hasta_sayfasi(hasta: Hasta):
    ara = request.args
    secim = {"hastane": None, "klinik": None, "doktor": None, "hizmet": None, "slotlar": None, "gunler": None,
             "hizmetler": []}
    try:
        if ara.get("h"):
            secim["hastane"] = uyg.kurum.hastaneler[int(ara["h"])]
        if ara.get("k") and secim["hastane"]:
            secim["klinik"] = secim["hastane"].klinikler[int(ara["k"])]
        if ara.get("d") and secim["klinik"]:
            secim["doktor"] = secim["klinik"].doktorlar[int(ara["d"])]
        if secim["doktor"]:
            # doktorun bu klinikte sunduğu hizmetler
            secim["hizmetler"] = secim["doktor"].sunulan_hizmetler(secim["klinik"])
        if ara.get("s") and secim["doktor"]:
            secim["hizmet"] = secim["hizmetler"][int(ara["s"])]
        if secim["doktor"] and secim["hizmet"]:
            secim["gunler"] = uyg.sistem.musait_gunler(
                secim["hastane"], secim["doktor"], secim["hizmet"])
        if ara.get("tarih") and secim["doktor"] and secim["hizmet"]:
            gun = datetime.strptime(ara["tarih"], "%Y-%m-%d").date()
            secim["slotlar"] = uyg.sistem.saat_tablosu(
                secim["hastane"], secim["doktor"], secim["hizmet"], gun, gecmisi_gizle=True)
    except (ValueError, IndexError):
        flash("Geçersiz seçim.", "hata")
    aranan = ara.get("q", "").strip()
    sonuclar = Arama(uyg).ara(aranan) if aranan else []
    randevular = uyg.sistem.hastanin_randevulari(hasta)
    return render_template("hasta.html", kullanici=hasta, secim=secim, ara=ara,
                           aranan=aranan, sonuclar=sonuclar,
                           receteler=hasta.receteli_randevularim(uyg.sistem),
                           hastaneler=uyg.kurum.hastaneler,
                           randevular=[(uyg.sistem.randevular.index(r), r) for r in randevular])


@app.post("/hasta/randevu-al")
def randevu_al():
    hasta = simdiki_kullanici()
    if hasattr(hasta, "randevu_engeli_var_mi") and hasta.randevu_engeli_var_mi():
        flash(f"Randevunuza gelmediğiniz için {hasta.engel_bitis_metni()} tarihine kadar yeni randevu alamazsınız.", "hata")
        return redirect(url_for("panel"))
    f = request.form

    def islem():
        hastane = uyg.kurum.hastaneler[int(f["h"])]
        klinik = hastane.klinikler[int(f["k"])]
        doktor = klinik.doktorlar[int(f["d"])]
        hasta.randevu_al(uyg.sistem, hastane, klinik, doktor,
                         doktor.sunulan_hizmetler(klinik)[int(f["s"])],
                         datetime.fromisoformat(f["zaman"]))
    calistir(islem, "Randevu oluşturuldu, doktor onayı bekleniyor.")
    return redirect(url_for("panel"))


@app.post("/hasta/iptal/<randevu_id>")
def hasta_iptal(randevu_id):
    hasta = simdiki_kullanici()
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    if r.hasta is not hasta:
        flash("Sadece kendi randevunuzu iptal edebilirsiniz.", "hata")
        return redirect(url_for("panel"))
    if r.odendi_mi:
        flash("Ödemesi yapılmış randevu iptal edilemez.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: hasta.randevu_iptal(r),
             "Randevu iptal edildi.")
    return redirect(url_for("panel"))


@app.post("/hasta/odeme/<randevu_id>")
def hasta_odeme(randevu_id):
    kullanici = simdiki_kullanici()
    if kullanici is None:
        flash("Ödeme için giriş yapmalısınız.", "hata")
        return redirect(url_for("giris"))
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    odeme = ODEMELER.get(request.form.get("yontem"))
    if odeme is None:
        flash("Geçersiz ödeme yöntemi.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: kullanici.odeme_yap(r, odeme), "Ödeme alındı.")
    return redirect(url_for("panel"))


# ---------------- DİĞER PERSONEL ----------------
def personel_sayfasi(personel: SaglikPersoneli):
    doktor = personel.doktor if isinstance(personel, Asistan) else None
    randevular = uyg.sistem.doktorun_randevulari(doktor) if doktor else []
    bugunku_randevular = []
    secili_tarih = request.args.get("tarih", "").strip()
    if isinstance(personel, Hemsire):
        tum_randevular = list(uyg.sistem.randevular)
        filtre_gun = None
        if secili_tarih == "bugun":
            filtre_gun = date.today()
        elif secili_tarih and secili_tarih != "tumu":
            try:
                filtre_gun = datetime.strptime(secili_tarih, "%Y-%m-%d").date()
            except ValueError:
                filtre_gun = None
        onaylilar = personel.onayli_randevular(tum_randevular, gun=filtre_gun)
        onaylilar.sort(key=lambda r: r.baslangic)
        bugunku_randevular = [(tum_randevular.index(r), r) for r in onaylilar]
    return render_template("personel.html", kullanici=personel, doktor=doktor,
                           randevular=randevular, bugunku_randevular=bugunku_randevular,
                           secili_tarih=secili_tarih)


@app.post("/hemsire/hasta-kabul/<randevu_id>")
def hemsire_hasta_kabul(randevu_id):
    hemsire = simdiki_kullanici()
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(request.referrer or url_for("panel"))
    # Ödeme yapılmışsa sadece kabul; yapılmamışsa ödeme yerinde alınır ve kabul birlikte yapılır
    odeme = None
    mesaj = "Hasta kabulü yapıldı."
    if not r.odendi_mi:
        odeme = ODEMELER.get(request.form.get("yontem", "nakit"))
        if odeme is None:
            flash("Geçersiz ödeme yöntemi.", "hata")
            return redirect(request.referrer or url_for("panel"))
        mesaj = "Ödeme alındı ve hasta kabulü yapıldı."
    calistir(lambda: hemsire.hasta_kabul(r, odeme=odeme), mesaj)
    return redirect(request.referrer or url_for("panel"))


@app.post("/hemsire/hasta-gelmedi/<randevu_id>")
def hemsire_hasta_gelmedi(randevu_id):
    hemsire = simdiki_kullanici()
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(request.referrer or url_for("panel"))
    calistir(lambda: hemsire.hasta_gelmedi(r), "Hasta gelmedi olarak işaretlendi. 24 saat randevu engeli uygulandı.")
    return redirect(request.referrer or url_for("panel"))


# ---------------- DOKTOR ----------------
def doktor_sayfasi(doktor: Doktor):
    randevular = uyg.sistem.doktorun_randevulari(doktor)
    # Takvim için (hastane, klinik, hizmet) seçenekleri: saat adımı hizmet süresine göre
    secenekler = [(h, k, s) for h in uyg.kurum.hastaneler for k in h.klinikler
                  if doktor in k.doktorlar for s in doktor.sunulan_hizmetler(k)]
    takvim = []
    secili = 0
    if secenekler:
        try:
            secili = int(request.args.get("x", 0))
            hastane, _, hizmet = secenekler[secili]
        except (ValueError, IndexError):
            secili = 0
            hastane, _, hizmet = secenekler[0]
        gunler = sorted({
            m[0].date() for m in doktor.musaitlik
            if getattr(m, "hastane", None) in (None, hastane)
        })
        takvim = [(gun, uyg.sistem.saat_tablosu(hastane, doktor, hizmet, gun)) for gun in gunler]
    musaitlikler = sorted(enumerate(doktor.musaitlik), key=lambda cift: cift[1][0])
    klinik_hizmetleri = []              # "Sunduğum hizmetler" formu için
    klinik_asistanlari = []             # Klinik seçip o klinikteki asistanı kendine bağlama
    for sira, klinik in enumerate(doktor.klinikler):
        hastane = next((h for h in uyg.kurum.hastaneler if klinik in h.klinikler), None)
        if not hastane:
            continue
        sunulan = doktor.sunulan_hizmetler(klinik)
        klinik_hizmetleri.append((sira, hastane, klinik,
                                  [(i, s, s in sunulan) for i, s in enumerate(klinik.hizmetler)]))
        uygun_asistanlar = [
            (personeller().index(p), p) for p in klinik.personeller
            if isinstance(p, Asistan) and p.doktor is not doktor
        ]
        klinik_asistanlari.append((sira, hastane, klinik, uygun_asistanlar))
    doktor_klinikleri = doktor.klinik_konumlari(uyg.kurum)
    doktor_hastaneleri = doktor.hastaneler(uyg.kurum)
    return render_template("doktor.html", kullanici=doktor, secenekler=secenekler,
                           klinik_hizmetleri=klinik_hizmetleri,
                           klinik_asistanlari=klinik_asistanlari,
                           doktor_klinikleri=doktor_klinikleri,
                           doktor_hastaneleri=doktor_hastaneleri,
                           musaitlikler=musaitlikler,
                           secili=secili, takvim=takvim,
                           randevular=[(uyg.sistem.randevular.index(r), r) for r in randevular])


@app.post("/doktor/onayla/<randevu_id>")
def doktor_onayla(randevu_id):
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().randevu_onayla(r),
             "Randevu onaylandı.")
    return redirect(url_for("panel"))


@app.post("/doktor/reddet/<randevu_id>")
def doktor_reddet(randevu_id):
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().randevu_reddet(r),
             "Randevu reddedildi.")
    return redirect(url_for("panel"))


@app.post("/doktor/musaitlik")
def doktor_musaitlik():
    f = request.form
    doktor = simdiki_kullanici()
    hastane_adi = f.get("hastane")
    hastane = uyg.kurum.hastane_bul(hastane_adi) if hastane_adi else None
    if hastane is None:
        hastaneler = doktor.hastaneler(uyg.kurum)
        if hastaneler:
            hastane = hastaneler[0]
    calistir(lambda: doktor.musaitlik_ekle(
        datetime.fromisoformat(f["baslangic"]),
        datetime.fromisoformat(f["bitis"]),
        hastane),
        "Müsaitlik eklendi.")
    return redirect(url_for("panel"))


@app.post("/doktor/hizmetler")
def doktor_hizmetler():
    """Doktor, bir klinikte vereceği hizmetleri seçer."""
    doktor = simdiki_kullanici()
    f = request.form

    def islem():
        klinik = doktor.klinikler[int(f["klinik"])]
        doktor.hizmetlerimi_sec(klinik, [klinik.hizmetler[int(i)] for i in f.getlist("hizmet")])
    calistir(islem, "Sunduğunuz hizmetler güncellendi.")
    return redirect(url_for("panel"))


@app.post("/doktor/recete/<randevu_id>")
def doktor_recete(randevu_id):
    """Doktor, onaylı randevu için reçete yazar. İlaçlar satır satır girilir."""
    f = request.form
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().recete_yaz(
        r, f.get("ilaclar", "").splitlines(), f.get("doktor_notu", "")),
        "Reçete kaydedildi.")
    return redirect(url_for("panel"))


@app.post("/doktor/musaitlik-sil/<int:sira>")
def doktor_musaitlik_sil(sira):
    doktor = simdiki_kullanici()
    calistir(lambda: doktor.musaitlik_sil(sira, uyg.sistem.doktorun_randevulari(doktor)),
             "Müsaitlik silindi.")
    return redirect(url_for("panel"))


@app.post("/doktor/asistan-ekle")
def doktor_asistan_ekle():
    doktor = simdiki_kullanici()
    f = request.form

    def islem():
        asistan = personeller()[int(f["asistan"])]
        doktor.asistan_ekle(asistan)
    calistir(islem, "Asistanınıza eklendi.")
    return redirect(url_for("panel"))


# ---------------- ADMIN / HASTANE YÖNETİCİSİ / KLİNİK YÖNETİCİSİ ----------------
def admin_sayfasi(admin: Yonetici):
    tum_kl = tum_klinikler()
    yonetilen_kl = admin.yonetilen_klinikler(uyg.kurum)
    yonetilen_kume = {k for _, k in yonetilen_kl}
    ara = request.args
    secili_kl_sira = (int(ara["ak"]) if ara.get("ak", "").isdigit() and int(ara["ak"]) < len(yonetilen_kl)
                      else 0)
    secili_hastane, secili_klinik = yonetilen_kl[secili_kl_sira] if yonetilen_kl else (None, None)
    klinik_doktorlari = list(secili_klinik.doktorlar) if secili_klinik else []
    secili_dr_sira = (int(ara["ad"]) if ara.get("ad", "").isdigit() and int(ara["ad"]) < len(klinik_doktorlari)
                      else 0)
    secili_doktor = klinik_doktorlari[secili_dr_sira] if klinik_doktorlari else None
    tum_asistanlar = [p for p in personeller() if isinstance(p, Asistan)]
    uygun_asistanlar = []
    if secili_klinik and secili_doktor:
        uygun_asistanlar = [
            (tum_asistanlar.index(p), p) for p in secili_klinik.personeller
            if isinstance(p, Asistan) and p.doktor is not secili_doktor
        ]
    hastane_secenekleri = [(uyg.kurum.hastaneler.index(h), h)
                           for h in admin.yonetilen_hastaneler(uyg.kurum)
                           if h in uyg.kurum.hastaneler]
    klinik_secenekleri = [(tum_kl.index((h, k)), h, k) for h, k in yonetilen_kl if (h, k) in tum_kl]
    tum_hz = tum_hizmetler()
    hizmet_secenekleri = [(tum_hz.index((h, k, s)), h, k, s)
                          for h, k in yonetilen_kl
                          for s in k.hizmetler
                          if (h, k, s) in tum_hz]

    def kisi_konumu(kisi):
        konumlar = [f"{h.ad} / {k.ad}" for h in uyg.kurum.hastaneler for k in h.klinikler if k in kisi.klinikler]
        return ", ".join(konumlar) if konumlar else "Klinik atanmadı"

    def kisi_hastaneleri(kisi):
        return [h.ad for h in uyg.kurum.hastaneler if any(k in h.klinikler for k in kisi.klinikler)]

    def kisi_klinikleri(kisi):
        return [k.ad for k in kisi.klinikler]

    asistan_secenekleri = [
        (tum_asistanlar.index(a), a, kisi_konumu(a), kisi_hastaneleri(a), kisi_klinikleri(a))
        for a in tum_asistanlar
        if (not a.klinikler) or any(k in yonetilen_kume for k in a.klinikler)
    ]

    secili_as_sira = int(ara["as"]) if ara.get("as", "").isdigit() and int(ara["as"]) < len(tum_asistanlar) else (asistan_secenekleri[0][0] if asistan_secenekleri else None)
    secili_asistan = tum_asistanlar[secili_as_sira] if secili_as_sira is not None else None

    ham_doktorlar = [
        (uyg.doktorlar().index(d), d, kisi_konumu(d), kisi_hastaneleri(d), kisi_klinikleri(d))
        for d in uyg.doktorlar()
        if any(k in yonetilen_kume for k in d.klinikler)
    ]

    # Seçilen asistana göre doktorları filtrele:
    # 1. Asistanın bağlı olduğu klinik varsa: SADECE aynı hastane ve klinikteki doktorlar
    # 2. Asistanın bağlı hastanesi yoksa: uzmanlığıyla alakalı doktorlar
    if secili_asistan and secili_asistan.klinikler:
        doktor_secenekleri = [
            d_item for d_item in ham_doktorlar
            if any(k in d_item[1].klinikler for k in secili_asistan.klinikler)
        ]
    elif secili_asistan:
        as_uzm = secili_asistan.uzmanlik.lower().strip()
        if as_uzm == "asistan" or not as_uzm:
            doktor_secenekleri = ham_doktorlar
        else:
            alakali = [
                d_item for d_item in ham_doktorlar
                if (d_item[1].uzmanlik.lower() in as_uzm
                    or as_uzm in d_item[1].uzmanlik.lower()
                    or any(w in d_item[1].uzmanlik.lower() for w in as_uzm.split() if len(w) > 3))
            ]
            doktor_secenekleri = alakali if alakali else ham_doktorlar
    else:
        doktor_secenekleri = ham_doktorlar

    doktor_secenekleri.sort(key=lambda item: item[1].tam_ad)

    yapi = [(h, [k for h2, k in yonetilen_kl if h2 is h])
            for h in admin.yonetilen_hastaneler(uyg.kurum)]
    randevular = [(uyg.sistem.randevular.index(r), r)
                  for r in admin.yonetilen_randevular(uyg.sistem)]

    if isinstance(admin, KlinikYoneticisi) and admin.klinik:
        kl_ad = admin.klinik.ad
        kl_ad_lower = kl_ad.lower()
        asistan_listesi = [g for g in uyg.gorevler.get("asistan", [])
                           if kl_ad_lower in g.lower() or g.lower() in kl_ad_lower]
        if not asistan_listesi:
            asistan_listesi = [f"{kl_ad} Asistanı"]
        gorevler_veri = {
            "doktor": [kl_ad],
            "asistan": asistan_listesi,
            "hemsire": list(uyg.gorevler.get("hemsire", [])),
            "teknisyen": list(uyg.gorevler.get("teknisyen", [])),
        }
    else:
        gorevler_veri = uyg.gorevler

    return render_template("admin.html", kullanici=admin,
                           hastane_secenekleri=hastane_secenekleri,
                           klinik_secenekleri=klinik_secenekleri,
                           hizmet_secenekleri=hizmet_secenekleri,
                           yonetilen_kl=yonetilen_kl,
                           yonetilebilir_kullanicilar=admin.yonetilebilir_kullanicilar(uyg),
                           doktorlar=doktor_secenekleri,
                           tum_doktorlar=ham_doktorlar,
                           gorevler=gorevler_veri,
                           personeller=list(enumerate(personeller())),
                           asistanlar=asistan_secenekleri,
                           secili_as_sira=secili_as_sira,
                           secili_kl_sira=secili_kl_sira,
                           klinik_doktorlari=[(uyg.doktorlar().index(d), d) for d in klinik_doktorlari if d in uyg.doktorlar()],
                           secili_dr_sira=secili_dr_sira,
                           secili_doktor=secili_doktor,
                           uygun_asistanlar=uygun_asistanlar,
                           yapi=yapi,
                           randevular=randevular)


@app.post("/admin/hastane")
def admin_hastane():
    f = request.form
    ac, kap = time.fromisoformat(f["acilis"]), time.fromisoformat(f["kapanis"])
    calistir(lambda: simdiki_kullanici().hastane_ekle(uyg.kurum, Hastane(f["ad"], ac, kap)),
             "Hastane eklendi.")
    return redirect(url_for("panel"))


@app.post("/admin/klinik")
def admin_klinik():
    f = request.form
    calistir(lambda: simdiki_kullanici().klinik_ekle(
        uyg.kurum.hastaneler[int(f["h"])], Klinik(f["ad"])), "Klinik eklendi.")
    return redirect(url_for("panel"))


@app.post("/admin/hastane-duzenle")
def admin_hastane_duzenle():
    f = request.form

    def islem():
        hastane = uyg.kurum.hastaneler[int(f["h"])]
        simdiki_kullanici().hastane_duzenle(
            uyg, hastane, f["ad"], time.fromisoformat(f["acilis"]), time.fromisoformat(f["kapanis"]))
    calistir(islem, "Hastane güncellendi.")
    return redirect(url_for("panel"))


@app.post("/admin/hastane-sil")
def admin_hastane_sil():
    f = request.form
    calistir(lambda: simdiki_kullanici().hastane_sil(uyg, uyg.kurum.hastaneler[int(f["h"])]),
             "Hastane silindi.")
    return redirect(url_for("panel"))


@app.post("/admin/klinik-sil")
def admin_klinik_sil():
    f = request.form

    def islem():
        hastane, klinik = tum_klinikler()[int(f["klinik"])]
        simdiki_kullanici().klinik_sil(uyg, hastane, klinik)
    calistir(islem, "Klinik silindi.")
    return redirect(url_for("panel"))


@app.post("/admin/hizmet")
def admin_hizmet():
    f = request.form

    def islem():
        _, klinik = tum_klinikler()[int(f["klinik"])]
        ad, sure, ucret = f["ad"], int(f["sure"]), float(f["ucret"])
        ekstra = float(f.get("ekstra") or 0)
        tur = f.get("tur", "muayene")
        if tur == "radyoloji" or (tur == "muayene" and ekstra > 0):
            hizmet = Radyoloji(ad, sure, ucret, ekstra)
        elif tur == "laboratuvar":
            hizmet = Laboratuvar(ad, sure, ucret, int(ekstra) or 1)
        else:
            hizmet = Muayene(ad, sure, ucret)
        simdiki_kullanici().hizmet_ekle(klinik, hizmet)
    calistir(islem, "Hizmet eklendi.")
    return redirect(url_for("panel"))


@app.post("/admin/hizmet-sil")
def admin_hizmet_sil():
    f = request.form

    def islem():
        hastane, klinik, hizmet = tum_hizmetler()[int(f["hizmet"])]
        simdiki_kullanici().hizmet_sil(uyg, hastane, klinik, hizmet)
    calistir(islem, "Hizmet silindi.")
    return redirect(url_for("panel"))


@app.post("/admin/personel")
def admin_personel():
    f = request.form

    def islem():
        tur, ad, soyad, tc = f["tur"], f["ad"], f["soyad"], f["tc"]
        if tur == "doktor":
            uzmanlik = f.get("uzmanlik", "").strip() or "Dahiliye"
            kisi = Doktor(ad, soyad, tc, uzmanlik)
        elif tur == "asistan":
            kisi = Asistan(ad, soyad, tc, "Asistan")
        elif tur == "hemsire":
            kisi = Hemsire(ad, soyad, tc, "Hemşirelik")
        else:
            uzmanlik = f.get("uzmanlik", "").strip() or "Radyoloji"
            kisi = Teknisyen(ad, soyad, tc, uzmanlik, f.get("cihaz") or "Cihaz")
        simdiki_kullanici().personel_kaydet(uyg, kisi)
    calistir(islem, "Personel kaydedildi.")
    return redirect(url_for("panel"))


@app.post("/admin/gorev")
def admin_gorev_ekle():
    f = request.form
    tur = f.get("tur", "doktor").strip() or "doktor"
    calistir(lambda: simdiki_kullanici().gorev_ekle(uyg, tur, f["ad"]),
             "Uzmanlık alanı eklendi.")
    return redirect(url_for("panel"))


def personeller() -> list:
    return [k for k in uyg.kullanicilar if isinstance(k, SaglikPersoneli)]


@app.post("/admin/personel-ata")
def admin_personel_ata():
    f = request.form

    def islem():
        _, klinik = tum_klinikler()[int(f["klinik"])]
        simdiki_kullanici().personel_ata(klinik, personeller()[int(f["personel"])])
    calistir(islem, "Personel kliniğe atandı.")
    return redirect(url_for("panel"))


@app.post("/admin/asistan-bagla")
def admin_asistan_bagla():
    f = request.form

    def islem():
        asistanlar = [p for p in personeller() if isinstance(p, Asistan)]
        simdiki_kullanici().asistan_bagla(asistanlar[int(f["asistan"])],
                                          uyg.doktorlar()[int(f["doktor"])])
    calistir(islem, "Asistan doktora bağlandı.")
    return redirect(url_for("panel"))


@app.post("/admin/asistan-ayir")
def admin_asistan_ayir():
    f = request.form

    def islem():
        asistanlar = [p for p in personeller() if isinstance(p, Asistan)]
        simdiki_kullanici().asistan_ayir(asistanlar[int(f["asistan"])])
    calistir(islem, "Asistan doktordan ayrıldı.")
    return redirect(url_for("panel"))


@app.post("/admin/randevu-onayla/<randevu_id>")
def admin_randevu_onayla(randevu_id):
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().randevu_onayla(r),
             "Randevu onaylandı.")
    return redirect(url_for("panel"))


@app.post("/admin/randevu-reddet/<randevu_id>")
def admin_randevu_reddet(randevu_id):
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().randevu_reddet(r),
             "Randevu reddedildi.")
    return redirect(url_for("panel"))


@app.post("/admin/randevu-iptal/<randevu_id>")
def admin_randevu_iptal(randevu_id):
    r = uyg.sistem.randevu_bul(randevu_id)
    if not r:
        flash("Randevu bulunamadı veya silinmiş.", "hata")
        return redirect(url_for("panel"))
    calistir(lambda: simdiki_kullanici().randevu_iptal(r),
             "Randevu iptal edildi.")
    return redirect(url_for("panel"))


@app.post("/admin/rol-degistir")
def admin_rol_degistir():
    f = request.form

    def islem():
        kisi = uyg.kullanicilar[int(f["kullanici"])]
        yeni_rol = f["yeni_rol"]
        hastane = klinik = None
        if yeni_rol == "hastane_yoneticisi":
            hastane = uyg.kurum.hastaneler[int(f["hastane"])]
        elif yeni_rol == "klinik_yoneticisi":
            hastane, klinik = tum_klinikler()[int(f["klinik"])]
        simdiki_kullanici().rol_degistir(uyg, kisi, yeni_rol, hastane, klinik)
    calistir(islem, "Kullanıcı rolü güncellendi.")
    return redirect(url_for("panel"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
