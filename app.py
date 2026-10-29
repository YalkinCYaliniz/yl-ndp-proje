"""Flask arayüzü: iş mantığı randevu/ paketinde, burada sadece sayfalar var."""
from datetime import date, datetime, time, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for

from randevu.hatalar import SistemHatasi
from randevu.kullanici import (Hasta, Doktor, Yonetici, SaglikPersoneli, Asistan,
                               Hemsire, Teknisyen)
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
    if secili == "personel":
        # Kategori seçici: Doktor / Asistan / Hemşire / Teknisyen
        kategoriler = [(rol, len([k for _, k in liste if k.rol() == rol])) for rol in ROL_SIRASI]
        liste.sort(key=lambda cift: ROL_SIRASI.index(cift[1].rol()))
        if secili_rol in ROL_SIRASI:
            liste = [(sira, k) for sira, k in liste if k.rol() == secili_rol]
    isim = request.args.get("q", "").strip()
    if isim and secili:
        aranan = sadelestir(isim)
        liste = [(sira, k) for sira, k in liste if aranan in sadelestir(k.tam_ad)]
    return render_template("giris.html", gruplar=gruplar, secili=secili, liste=liste,
                           kategoriler=kategoriler, secili_rol=secili_rol, isim=isim,
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
                secim["hastane"], secim["doktor"], secim["hizmet"], gun)
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


@app.post("/hasta/iptal/<int:sira>")
def hasta_iptal(sira):
    calistir(lambda: simdiki_kullanici().randevu_iptal(uyg.sistem.randevular[sira]),
             "Randevu iptal edildi.")
    return redirect(url_for("panel"))


@app.post("/hasta/odeme/<int:sira>")
def hasta_odeme(sira):
    odeme = ODEMELER.get(request.form.get("yontem"))
    calistir(lambda: uyg.sistem.randevular[sira].odeme_yap(odeme), "Ödeme alındı.")
    return redirect(url_for("panel"))


# ---------------- DİĞER PERSONEL ----------------
def personel_sayfasi(personel: SaglikPersoneli):
    doktor = personel.doktor if isinstance(personel, Asistan) else None
    randevular = uyg.sistem.doktorun_randevulari(doktor) if doktor else []
    return render_template("personel.html", kullanici=personel, doktor=doktor,
                           randevular=randevular)


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
        gunler = sorted({b.date() for b, _ in doktor.musaitlik})
        takvim = [(gun, uyg.sistem.saat_tablosu(hastane, doktor, hizmet, gun)) for gun in gunler]
    musaitlikler = sorted(enumerate(doktor.musaitlik), key=lambda cift: cift[1][0])
    klinik_hizmetleri = []              # "Sunduğum hizmetler" formu için
    klinik_asistanlari = []             # Klinik seçip o klinikteki asistanı kendine bağlama
    for sira, klinik in enumerate(doktor.klinikler):
        hastane = next(h for h in uyg.kurum.hastaneler if klinik in h.klinikler)
        sunulan = doktor.sunulan_hizmetler(klinik)
        klinik_hizmetleri.append((sira, hastane, klinik,
                                  [(i, s, s in sunulan) for i, s in enumerate(klinik.hizmetler)]))
        uygun_asistanlar = [
            (personeller().index(p), p) for p in klinik.personeller
            if isinstance(p, Asistan) and p.doktor is not doktor
        ]
        klinik_asistanlari.append((sira, hastane, klinik, uygun_asistanlar))
    return render_template("doktor.html", kullanici=doktor, secenekler=secenekler,
                           klinik_hizmetleri=klinik_hizmetleri,
                           klinik_asistanlari=klinik_asistanlari,
                           musaitlikler=musaitlikler,
                           secili=secili, takvim=takvim,
                           randevular=[(uyg.sistem.randevular.index(r), r) for r in randevular])


@app.post("/doktor/onayla/<int:sira>")
def doktor_onayla(sira):
    calistir(lambda: simdiki_kullanici().randevu_onayla(uyg.sistem.randevular[sira]),
             "Randevu onaylandı.")
    return redirect(url_for("panel"))


@app.post("/doktor/reddet/<int:sira>")
def doktor_reddet(sira):
    calistir(lambda: simdiki_kullanici().randevu_reddet(uyg.sistem.randevular[sira]),
             "Randevu reddedildi.")
    return redirect(url_for("panel"))


@app.post("/doktor/musaitlik")
def doktor_musaitlik():
    f = request.form
    calistir(lambda: simdiki_kullanici().musaitlik_ekle(
        datetime.fromisoformat(f["baslangic"]), datetime.fromisoformat(f["bitis"])),
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


@app.post("/doktor/recete/<int:sira>")
def doktor_recete(sira):
    """Doktor, onaylı randevu için reçete yazar. İlaçlar satır satır girilir."""
    f = request.form
    calistir(lambda: simdiki_kullanici().recete_yaz(
        uyg.sistem.randevular[sira], f.get("ilaclar", "").splitlines(), f.get("doktor_notu", "")),
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


# ---------------- ADMIN ----------------
def admin_sayfasi(admin: Yonetici):
    tum_kl = tum_klinikler()
    ara = request.args
    secili_kl_sira = int(ara["ak"]) if ara.get("ak", "").isdigit() and int(ara["ak"]) < len(tum_kl) else 0
    secili_hastane, secili_klinik = tum_kl[secili_kl_sira] if tum_kl else (None, None)
    klinik_doktorlari = list(secili_klinik.doktorlar) if secili_klinik else []
    secili_dr_sira = int(ara["ad"]) if ara.get("ad", "").isdigit() and int(ara["ad"]) < len(klinik_doktorlari) else 0
    secili_doktor = klinik_doktorlari[secili_dr_sira] if klinik_doktorlari else None
    tum_asistanlar = [p for p in personeller() if isinstance(p, Asistan)]
    uygun_asistanlar = []
    if secili_klinik and secili_doktor:
        uygun_asistanlar = [
            (tum_asistanlar.index(p), p) for p in secili_klinik.personeller
            if isinstance(p, Asistan) and p.doktor is not secili_doktor
        ]
    asistan_klinikleri = {}
    for a in tum_asistanlar:
        etk = []
        for h in uyg.kurum.hastaneler:
            for k in h.klinikler:
                if a in k.personeller:
                    etk.append(f"{h.ad} / {k.ad}")
        asistan_klinikleri[id(a)] = ", ".join(etk) if etk else "Klinik atanmadı"
    return render_template("admin.html", kullanici=admin, hastaneler=uyg.kurum.hastaneler,
                           klinikler=tum_kl, doktorlar=uyg.doktorlar(),
                           personeller=personeller(),
                           asistanlar=tum_asistanlar,
                           asistan_klinikleri=asistan_klinikleri,
                           secili_kl_sira=secili_kl_sira,
                           klinik_doktorlari=[(uyg.doktorlar().index(d), d) for d in klinik_doktorlari],
                           secili_dr_sira=secili_dr_sira,
                           secili_doktor=secili_doktor,
                           uygun_asistanlar=uygun_asistanlar,
                           randevular=uyg.sistem.randevular)


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


@app.post("/admin/hizmet")
def admin_hizmet():
    f = request.form

    def islem():
        _, klinik = tum_klinikler()[int(f["klinik"])]
        ad, sure, ucret = f["ad"], int(f["sure"]), float(f["ucret"])
        ekstra = float(f.get("ekstra") or 0)
        if f["tur"] == "radyoloji":
            hizmet = Radyoloji(ad, sure, ucret, ekstra)
        elif f["tur"] == "laboratuvar":
            hizmet = Laboratuvar(ad, sure, ucret, int(ekstra) or 1)
        else:
            hizmet = Muayene(ad, sure, ucret)
        simdiki_kullanici().hizmet_ekle(klinik, hizmet)
    calistir(islem, "Hizmet eklendi.")
    return redirect(url_for("panel"))


@app.post("/admin/personel")
def admin_personel():
    f = request.form

    def islem():
        tur, ad, soyad, tc = f["tur"], f["ad"], f["soyad"], f["tc"]
        uzmanlik = f.get("uzmanlik") or tur.title()
        if tur == "doktor":
            kisi = Doktor(ad, soyad, tc, uzmanlik)
        elif tur == "asistan":
            kisi = Asistan(ad, soyad, tc, uzmanlik)
        elif tur == "hemsire":
            kisi = Hemsire(ad, soyad, tc, uzmanlik)
        else:
            kisi = Teknisyen(ad, soyad, tc, uzmanlik, f.get("cihaz") or "Cihaz")
        simdiki_kullanici().personel_kaydet(uyg, kisi)
    calistir(islem, "Personel kaydedildi.")
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
