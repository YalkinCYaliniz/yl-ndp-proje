# Hastane / Klinik Randevu Sistemi (NDP Projesi)

Bu proje, **Nesneye Dayalı Programlama (NDP / OOP)** dersi kapsamında **Seçenek A — Hastane/Klinik Randevu Sistemi Geliştirme** gereksinimlerini karşılamak üzere Python ve Flask kullanılarak geliştirilmiştir. Uygulama hem tek bir klinik/hastane için hem de **çok şubeli sağlık kuruluşlarını** (`Kurum -> Hastane -> Klinik -> Doktor/Personel`) destekleyecek şekilde tasarlanmıştır.

---

## 1. Kurulum ve Çalıştırma

```bash
cd yl-ndp-proje
python3 app.py
```

- Tarayıcıdan **http://127.0.0.1:5001** adresini açın.
- **Demo Şifresi:** Sistemdeki tüm örnek kullanıcıların (Admin, Doktor, Asistan, Hemşire, Teknisyen, Hasta) şifresi **`123456`** olarak tanımlanmıştır.
- Konsol üzerinden hızlı NDP demosunu çalıştırmak için:
  ```bash
  python3 main.py
  ```
- Birim testlerini çalıştırmak için:
  ```bash
  python3 -m unittest discover -s tests -t .
  ```

---

## 2. Proje Dosya Yapısı

İş mantığı tamamen `randevu/` paketi içindeki sınıflarda yer alır; `app.py` yalnızca web sayfalarını bu sınıflara bağlar:

```text
yl-ndp-proje/
├── app.py                  # Flask web arayüzü rotaları
├── main.py                 # Konsol üzerinden çalışan kısa NDP demosu
├── randevu/
│   ├── kullanici.py        # Kullanici (ABC), Hasta, Misafir, SaglikPersoneli, Doktor, Asistan, Hemsire, Teknisyen, Yonetici
│   ├── kurum.py            # Kurum, Hastane, Klinik ve Hizmet (ABC), Muayene, Radyoloji, Laboratuvar
│   ├── randevu.py          # Randevu, RandevuDurumu (Enum), Slot, RandevuSistemi
│   ├── odeme.py            # Odeme (ABC), NakitOdeme, KartOdeme, SigortaOdeme
│   ├── recete.py           # Recete sınıfı (ilaç listesi ve doktor notu)
│   ├── arama.py            # Arama ve AramaSonucu (doktor/klinik arama ve en yakın boş randevu)
│   ├── guvenlik.py         # Sifre sınıfı (PBKDF2-HMAC-SHA256 ile tuzlu şifre özeti)
│   ├── hatalar.py          # SistemHatasi, RandevuHatasi, YetkiHatasi, BulunamadiHatasi
│   ├── uygulama.py         # Uygulama sınıfı (kimlik doğrulama, kayıt, misafir oluşturma)
│   ├── ornek_veri.py       # 6 hastane, 60 klinik, 120+ doktor ve personel örnek verisi
│   └── depo.py             # Depo sınıfı (veri.json dosyasına kaydetme ve yükleme)
├── templates/              # HTML şablonları (giris, hasta, doktor, personel, admin)
└── tests/                  # 158 adet birim testi (unittest)
```

---

## 3. NDP (OOP) İlkelerinin Kodda Kullanımı (Sunum Rehberi)

Sunumda hocanın *"Hangi NDP ilkesini nerede kullandın?"* sorusuna doğrudan aşağıdaki sınıf ve metotlarla cevap verebilirsiniz:

### A. Soyutlama (Abstraction)
Doğrudan nesnesi oluşturulamayan (`ABC` ve `@abstractmethod` kullanan) **3 adet soyut taban sınıf** vardır:
1. **`Kullanici(ABC)`** (`randevu/kullanici.py`): Tüm kullanıcıların ortak atasıdır. `rol()` ve `yetkiler()` metotları soyuttur; her alt sınıf kendi rolünü ve yetki listesini tanımlamak zorundadır.
2. **`Hizmet(ABC)`** (`randevu/kurum.py`): Sağlık hizmetlerinin ortak atasıdır. `tur()` metodu soyuttur; `ucret_hesapla()` metodu alt sınıflarda özelleştirilir.
3. **`Odeme(ABC)`** (`randevu/odeme.py`): Ödeme yöntemlerinin soyut sınıfıdır. `yontem()` ve `toplam_hesapla(tutar)` metotlarını alt sınıflara zorunlu kılar.

### B. Kalıtım (Inheritance)
Projede 4 ayrı kalıtım ağacı bulunur:
1. **Kullanıcı Hiyerarşisi (`randevu/kullanici.py`):**
   ```text
   Kullanici (ABC)
   ├── Hasta
   │   └── Misafir
   ├── SaglikPersoneli
   │   ├── Doktor
   │   ├── Asistan
   │   ├── Hemsire
   │   └── Teknisyen
   └── Yonetici (Genel Admin — tüm kurumu yönetir)
       ├── HastaneYoneticisi (Sadece kendi hastanesini yönetir)
       └── KlinikYoneticisi  (Sadece kendi kliniğindeki doktor, personel ve randevuları yönetir)
   ```
2. **Hizmet Hiyerarşisi (`randevu/kurum.py`):**
   - `Hizmet(ABC)` $\rightarrow$ `Muayene`, `Radyoloji`, `Laboratuvar`
3. **Ödeme Hiyerarşisi (`randevu/odeme.py`):**
   - `Odeme(ABC)` $\rightarrow$ `NakitOdeme`, `KartOdeme`, `SigortaOdeme`
4. **Özel Hata Hiyerarşisi (`randevu/hatalar.py`):**
   - `Exception` $\rightarrow$ `SistemHatasi` $\rightarrow$ `RandevuHatasi`, `YetkiHatasi`, `BulunamadiHatasi`
   - Bu sayede arayüzde tek bir `except SistemHatasi:` bloğu ile tüm proje hataları yakalanır.

### C. Çok Biçimlilik (Polymorphism) — Overriding ve Overloading
1. **Metot Ezme (Method Overriding):**
   - **Hizmet Ücreti Hesaplama (`randevu/kurum.py`):**
     - `Muayene.ucret_hesapla()` $\rightarrow$ taban ücreti döndürür.
     - `Radyoloji.ucret_hesapla()` $\rightarrow$ `(taban_ucret + cihaz_ucreti)` döndürür.
     - `Laboratuvar.ucret_hesapla()` $\rightarrow$ `(taban_ucret * tahlil_sayisi)` döndürür.
   - **Ödeme Hesaplama (`randevu/odeme.py`):**
     - `Randevu.odeme_yap(odeme)` metodu kendisine gelen nesnenin `NakitOdeme`, `KartOdeme` veya `SigortaOdeme` olduğunu bilmeden `odeme.toplam_hesapla(ucret)` çağırır. Nakit aynen alır, Kart taksit komisyonu ekler, Sigorta katılım payını (%20) alır.
   - **Klinik Ataması (`randevu/kullanici.py`):**
     - `Yonetici.personel_ata(klinik, personel)` metodu `personel.klinige_ata(klinik)` çağırır. `SaglikPersoneli` bunu kliniğin personel listesine eklerken, `Doktor` sınıfı bu metodu **ezerek (override)** kendisini kliniğin doktor listesine ekler.
   - **JSON Serileştirme (`sozluge()`):**
     - Her sınıf `super().sozluge()` çağırıp kendi ek alanlarını (`uzmanlik`, `cihaz_ucreti`, `tahlil_sayisi`, `cihaz`) sözlüğe ekler.
2. **Metot Aşırı Yükleme (Overloading):**
   - Python'da aynı isimli iki metot tanımlanamadığı için aşırı yükleme **varsayılan parametrelerle** sağlanmıştır:
     - `hizmet.ucret_hesapla()` $\rightarrow$ indirimsiz ücret hesaplar.
     - `hizmet.ucret_hesapla(0.10)` $\rightarrow$ %10 indirimli ücret hesaplar.

### D. Kapsülleme (Encapsulation)
Sınıfların iç verileri dışarıdan doğrudan değiştirilemez; `_` (protected) ve `__` (private) alanlar ile `@property` doğrulamaları kullanılmıştır:
1. **Özel Alanlar ve `@property` Doğrulaması (`Kullanici`):**
   - `__tc_no`: Sadece 11 haneli rakam kabul eder (`@tc_no.setter`).
   - `__eposta`, `__kullanici_adi`: Format kontrolünden geçmeden atanamaz.
   - `_uzmanlik`: Boş bırakılamaz (`@uzmanlik.setter`).
2. **Şifre Güvenliği (`Sifre` ve `Kullanici.__sifre`):**
   - Düz metin şifre hiçbir yerde saklanmaz; `Sifre.olustur()` rastgele tuz (salt) ile PBKDF2-SHA256 özeti üretir ve sadece `dogru_mu()` ile doğrulama yapar.
3. **Randevu Durumu (`Randevu._durum`):**
   - Dışarıdan `randevu._durum = ...` şeklinde değiştirilmez; sadece `onayla()`, `reddet()` ve `iptal()` metotlarıyla kurallı şekilde geçiş yapar (örneğin iptal edilmiş bir randevu onaylanamaz).
4. **Salt Okunur Koleksiyonlar (`tuple` dönüşü):**
   - `_hastaneler`, `_klinikler`, `_doktorlar`, `_hizmetler`, `_asistanlar`, `_randevular`, `_ilaclar` listeleri dışarıya `tuple(...)` olarak döndürülür; böylece dışarıdan `.append()` ile kuralsız eleman eklenmesi engellenir.

---

## 4. İsterlerin Karşılanma Tablosu

| Proje Gereksinimi | Kodda Karşılandığı Yer |
| :--- | :--- |
| **1a.** Hastane/klinikler yetki çerçevesinde tanımlanabilecek | `Yonetici.hastane_ekle()`, `Yonetici.klinik_ekle()` (`_yetki_kontrol` ile korunur) |
| **1b.** Çalışma saatleri ve bölümler tanımlanabilecek | `Hastane(ad, acilis, kapanis)`, `Hastane.acik_mi()`, `Hastane.klinikler` |
| **1c.** Sağlık hizmetleri, süresi ve ücreti detaylı tanımlanabilecek | `Hizmet(ad, sure_dk, taban_ucret)` ve alt sınıfları `Muayene`, `Radyoloji`, `Laboratuvar` |
| **2a.** Doktor ve sağlık personeli kayıt edilebilecek | `Yonetici.personel_kaydet()` — `Doktor`, `Asistan`, `Hemsire`, `Teknisyen` |
| **2b.** Doktorun uzmanlık alanı ve sunduğu hizmetler tanımlanabilecek | `Doktor.uzmanlik`, `Doktor.klinige_uygun_mu()`, `Doktor.hizmet_tanimla()`, `Doktor.sunulan_hizmetler()` |
| **2c.** Doktor uygunluk zaman dilimleri; sadece bu aralıklara randevu | `Doktor.musaitlik_ekle()`, `Doktor.musait_mi()`, `RandevuSistemi.saat_tablosu()` |
| **3a.** Uygun çalışan ve işlem seçerek randevu oluşturma | MHRS akışı: Hastane $\rightarrow$ Klinik $\rightarrow$ Doktor $\rightarrow$ Hizmet $\rightarrow$ Müsait Gün $\rightarrow$ Saat |
| **3b.** Randevu oluşturulurken çakışma kontrolü | `Randevu.cakisiyor_mu()` (doktor çakışması) ve `Randevu.hasta_icin_uygun_mu()` (hasta aynı gün en az 1 saat ara kuralı) |
| **3c.** Randevu detayları (işlem, süre, ücret, çalışan, tarih/saat) kaydı | `Randevu` nesnesi ve `Depo.kaydet()` / `Depo.yukle()` (`veri.json`) |
| **3d.** Randevu onay mekanizması | `RandevuDurumu.BEKLIYOR` $\rightarrow$ `Doktor.randevu_onayla()` / `Doktor.randevu_reddet()` |
| **4.** En az üç kullanıcı rolü | `Hasta` (+ `Misafir`), `SaglikPersoneli` (`Doktor`, `Asistan`, `Hemsire`, `Teknisyen`), `Yonetici` |

---

## 5. Sunumda 5 Dakikalık Canlı Demo Senaryosu

Sunumda projeyi gösterirken şu sırayı izlerseniz tüm özellikleri takılmadan göstermiş olursunuz:

1. **Giriş ve Rol Yapısı:**
   - Ana sayfada **Admin**, **Personeller** (Doktor, Asistan, Hemşire, Teknisyen kategori filtreli) ve **Kullanıcılar** gruplarını gösterin.
   - Kayıt olmadan devam eden **Misafir** seçeneğini ve şifreli girişi (`123456`) kısaca belirtin.
2. **Hasta Olarak Randevu Alma ve Çakışma Kontrolü (`Ali Demir`):**
   - Üstteki arama kutusuna `kardiyoloji` veya `ayşe` yazıp **en yakın boş randevu** sıralamasını gösterin.
   - Hastane $\rightarrow$ Klinik $\rightarrow$ Doktor (yanında uzmanlığı ve asistanları görünür) $\rightarrow$ Hizmet seçin.
   - Açılan **yeşil müsait günlerden** birine tıklayıp saat tablosundan yeşil bir saate randevu alın; saatin **kırmızıya (dolu)** döndüğünü gösterin.
   - Aynı saate veya 30 dakika sonrasına ikinci bir randevu almaya çalışıp **çakışma / 1 saat ara** uyarısını gösterin.
3. **Doktor Onayı, Reçete ve Hizmet Seçimi (`Ayşe Yılmaz`):**
   - Doktor olarak giriş yapın; **Takvimim** bölümünde dolu saatin üzerinde hasta adının yazdığını gösterin.
   - Bekleyen randevuyu **Onayla** butonuyla onaylayın, ardından **Reçete yaz** kısmından ilaç ve doktor notu ekleyin.
   - **Sunduğum Hizmetler** ve **Kliniğimden Asistan Ekle** (en fazla 3 asistan) bölümlerini gösterin.
4. **Hasta Ödeme ve Reçete Görüntüleme (`Ali Demir`):**
   - Tekrar hasta olarak girip onaylanan randevu için **Nakit / Kredi Kartı (3 taksit) / Sigorta** seçeneklerinden biriyle ödeme yapın (çok biçimlilik).
   - Alttaki **Reçetelerim** tablosunda doktorun yazdığı ilaçları ve notu gösterin.
   - İsterseniz bir randevuyu iptal edip saatin tekrar **yeşile** döndüğünü gösterin.
5. **Admin Paneli ve Uzmanlık Kuralı (`Mehmet Kaya`):**
   - Admin olarak girip 6 hastane ve 60 kliniğin yapısını gösterin.
   - **Klinik seçerek doktora asistan bağla** kartını gösterin.
   - Son olarak **Personeli kliniğe ata** kısmından uzmanlığı *Dahiliye* olan bir doktoru *Kardiyoloji* kliniğine atamaya çalışın ve sistemin *"sadece kendi uzmanlık kliniğine atanabilir"* diyerek engellediğini gösterin.
