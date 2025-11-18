# LinkedIn Ghost Job Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Selenium](https://img.shields.io/badge/Selenium-4.0+-green.svg)
![Chrome](https://img.shields.io/badge/Chrome-Latest-orange.svg)
![License](https://img.shields.io/badge/License-Educational-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

</div>

LinkedIn iş ilanlarını analiz ederek "ghost job" (hayalet iş) olabilecek ilanları tespit eden otomatik analiz aracı.

---

## 🎯 Uygulamanın Amacı ve Çalışma Şekli

![Ghost Job Detector](img/ghostjob-detector-01.png)

### Amaç

Bu uygulama, LinkedIn'deki iş ilanlarını analiz ederek şüpheli veya "ghost job" olabilecek ilanları tespit eder. Ghost job'lar, şirketlerin gerçekten işe alım yapmak yerine veri toplama, marka bilinirliği veya uzun süredir açık kalan ilanlar olabilir.

### Çalışma Şekli

Uygulama 5 ana adımda çalışır:

1. **🔐 Otomatik Giriş**: LinkedIn'e email/parola ile otomatik giriş yapar
2. **🔍 İlan Toplama**: Belirtilen LinkedIn sayfasından iş ilanlarını toplar
3. **📄 Sayfa Gezinme**: Tüm sayfalarda (pagination) gezinerek belirtilen sayıda ilan toplar
4. **📊 Detay Çıkarma**: Her ilanın detay sayfasına gidip kapsamlı bilgileri çıkarır
5. **🎯 Analiz ve Raporlama**: Toplanan verileri analiz eder, risk skorları hesaplar ve CSV/JSON raporları oluşturur

### Terminal Kaydı

[![asciicast](https://asciinema.org/a/qeYdiAxsft8160c66mAc40Cjc.svg)](https://asciinema.org/a/qeYdiAxsft8160c66mAc40Cjc)

---

## 🚀 Kurulum

### Gereksinimler

- **Python 3.7 veya üzeri**
- **Google Chrome** veya **Chromium** tarayıcı
- **ChromeDriver** (otomatik yüklenir - webdriver-manager ile)
- **İnternet bağlantısı**

### macOS Kurulumu

#### Adım 1: Python Kurulumunu Kontrol Edin

```bash
python3 --version
```

Eğer Python yüklü değilse:

```bash
brew install python3
```

#### Adım 2: Proje Dizinine Gidin

```bash
cd "/path/to/Linedin-GhostJob_Detector"
```

#### Adım 3: Virtual Environment Oluşturun ve Aktif Edin

```bash
python3 -m venv venv
source venv/bin/activate
```

Terminal'de `(venv)` yazısı görünmelidir.

#### Adım 4: Gerekli Paketleri Yükleyin

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Adım 5: Chrome Kurulumunu Kontrol Edin

```bash
ls "/Applications/Google Chrome.app"
```

Eğer yüklü değilse, [Chrome'u indirip yükleyin](https://www.google.com/chrome/).

#### ✅ macOS Kurulumu Tamamlandı!

---

### Windows Kurulumu

#### Adım 1: Python Kurulumunu Kontrol Edin

**PowerShell** veya **Command Prompt**'u açın:

```cmd
python --version
```

veya

```cmd
py --version
```

Eğer Python yüklü değilse:

1. [Python.org](https://www.python.org/downloads/) adresinden Python 3.7+ indirin
2. İndirilen `.exe` dosyasını çalıştırın
3. **"Add Python to PATH"** seçeneğini işaretleyin
4. **"Install Now"** butonuna tıklayın

#### Adım 2: Proje Dizinine Gidin

```cmd
cd "C:\path\to\Linedin-GhostJob_Detector"
```

#### Adım 3: Virtual Environment Oluşturun ve Aktif Edin

```cmd
python -m venv venv
```

**PowerShell'de:**
```powershell
.\venv\Scripts\Activate.ps1
```

Eğer execution policy hatası alırsanız:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Command Prompt'ta:**
```cmd
venv\Scripts\activate.bat
```

Terminal'de `(venv)` yazısı görünmelidir.

#### Adım 4: Gerekli Paketleri Yükleyin

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Adım 5: Chrome Kurulumunu Kontrol Edin

Chrome'un yüklü olduğundan emin olun. Eğer yüklü değilse, [Chrome'u indirip yükleyin](https://www.google.com/chrome/).

#### ✅ Windows Kurulumu Tamamlandı!

---

## 📖 Kullanım

### Komut Formatı

```bash
python3 auto_analyzer.py "LINKEDIN_URL" "EMAIL" "PASSWORD" [MAX_JOBS]
```

### Parametreler

| Parametre | Zorunlu | Açıklama | Örnek |
|-----------|---------|----------|-------|
| `LINKEDIN_URL` | ✅ Evet | LinkedIn iş ilanları sayfasının URL'si | `https://www.linkedin.com/jobs/search/?keywords=IT` |
| `EMAIL` | ❌ Hayır | LinkedIn email adresiniz | `kullanici@email.com` |
| `PASSWORD` | ❌ Hayır | LinkedIn parolanız | `sifre123` |
| `MAX_JOBS` | ❌ Hayır | Taranacak maksimum ilan sayısı (varsayılan: 30) | `50` |

### Örnek Kullanım

**macOS/Linux:**
```bash
cd "/path/to/Linedin-GhostJob_Detector"
source venv/bin/activate
python3 auto_analyzer.py "https://www.linkedin.com/jobs/search/?keywords=IT&location=Turkey" "kullanici@email.com" "sifre123" 50
```

**Windows:**
```cmd
cd "C:\path\to\Linedin-GhostJob_Detector"
venv\Scripts\activate
python auto_analyzer.py "https://www.linkedin.com/jobs/search/?keywords=IT&location=Turkey" "kullanici@email.com" "sifre123" 50
```

### Güvenli Parola Kullanımı

Parolanızı komut satırında görünür şekilde girmek güvenli değildir. Bunun yerine:

1. `auto_analyzer.py` dosyasını açın
2. `main()` fonksiyonunda varsayılan email/şifre bölümünü bulun ve doldurun
3. Script'i sadece URL ile çalıştırın:

```bash
python3 auto_analyzer.py "LINKEDIN_URL" "" "" 50
```

**⚠️ Önemli:** `auto_analyzer.py` dosyasını Git'e commit etmeyin veya paylaşmayın!

### Çıktı Dosyaları

Script çalıştıktan sonra `report/` dizininde şu dosyalar oluşturulur:

- **`linkedin_jobs_master_report_YYYYMMDD_HHMMSS.csv`**: Tüm ilanların detaylı analizi (Ana rapor)
- **`all_jobs_analysis_YYYYMMDD_HHMMSS.json`**: Tüm ilanların JSON formatında analizi
- **`ghost_jobs_report_YYYYMMDD_HHMMSS.json`**: Şüpheli ilanların JSON formatında analizi

---

## 📊 Puanlama Mantığı

Uygulama, her ilan için **0-10 arası** bir risk skoru hesaplar. Bu skor, 7 ana kriterden oluşur:

### Ana Kriterler

1. **Yayın Tarihi ve Süresi** (0-2 puan): 30+ gün açık ilanlar şüpheli, 90+ gün açık ilanlar çok şüpheli
2. **İlan Açıklama Kalitesi** (0-2.5 puan): Belirsiz ifadeler, kısa açıklamalar risk oluşturur
3. **Maaş Şeffaflığı** (0-2 puan): Maaş bilgisi yoksa veya belirsizse risk artar
4. **Yüksek Başvuru Sayısı Ama Hareketsizlik** (0-1.5 puan): 100+ başvuru ama yanıt yok
5. **Yanıt Alamama / İletişim Gecikmesi** (0-1 puan): 14+ gün açık ama yanıt içgörüsü yok
6. **Gereksinim Anomalileri** (0-1 puan): Junior pozisyon ama senior deneyim bekleniyor
7. **İlan Durumu** (0-1.5 puan): Yeniden yayınlandı, genel başvuru vb.

### Özel Kurallar

- **30+ gün açık + Yeniden yayınlandı**: +3.0 ek puan (çok şüpheli)
- **False Positive Önleme**: Yeni ilanlar (30 günden az) için daha az agresif puanlama
  - 30 günden az açık ilanlar için eşik: **4 puan** (Ghost Job olarak işaretlenmek için)
  - 30+ gün açık ilanlar için eşik: **3 puan** (Ghost Job olarak işaretlenmek için)

### Final Skor

```
Final Skor = (Normalize Edilmiş Risk Skoru + Detaylı Skor) / 2
```

**Risk Skoru Yorumlama:**
- **0-2**: Düşük risk, normal ilan
- **3-5**: Orta risk, şüpheli ilan
- **6-8**: Yüksek risk, çok şüpheli ilan
- **9-10**: Çok yüksek risk, kesinlikle ghost job

---

## ⚠️ Önemli Uyarı ve Yasal Bildirim

### Eğitim Amaçlı Kullanım

**Bu uygulama tamamen eğitim ve araştırma amaçlı geliştirilmiştir.** Web scraping, veri analizi tekniklerini öğrenmek ve LinkedIn iş ilanları üzerinde akademik/araştırma amaçlı analiz yapmak için tasarlanmıştır.

### Analiz Sonuçları Hakkında

Bu uygulama tarafından üretilen analiz sonuçları:
- **Otomatik algoritmalar** tarafından hesaplanan **risk skorlarına** dayanmaktadır
- **Kesin bir gerçeklik** değil, **olasılık bazlı değerlendirmelerdir**
- **Yanlış pozitif (false positive)** sonuçlar içerebilir
- **Şirketlerin gerçek işe alım niyetlerini** doğrudan kanıtlamaz veya çürütmez

**Not**: Bu uygulama, şirketleri suçlamak veya kötülemek amacıyla değil, **işe alım süreçlerindeki şeffaflığı artırmak** ve **adayların zamanlarını korumak** için geliştirilmiştir.

---

## 🛠️ Kullanılan Teknolojiler

- **Python 3.7+** - Ana programlama dili
- **Selenium WebDriver 4.0+** - Web tarayıcı otomasyonu
- **WebDriver Manager** - ChromeDriver otomatik yönetimi
- **Chrome/Chromium** - Tarayıcı motoru
- **JSON/CSV** - Veri saklama ve rapor formatları
- **JavaScript** - Browser console extractor

---

## 🔧 Sorun Giderme

### Problem: "Chrome driver başlatılamadı"

**Çözüm:** ChromeDriver otomatik yüklenir (webdriver-manager ile). Chrome'un güncel olduğundan emin olun.

### Problem: "Hiç ilan bulunamadı"

**Çözüm:**
1. LinkedIn sayfasının doğru yüklendiğinden emin olun
2. "Sign in to view more jobs" mesajı varsa, script otomatik olarak giriş yapacaktır
3. Script'i tekrar çalıştırın

### Problem: "Login başarısız"

**Çözüm:**
1. Email ve parolanın doğru olduğundan emin olun
2. LinkedIn'de 2FA (iki faktörlü doğrulama) aktifse, geçici olarak devre dışı bırakın
3. LinkedIn'de CAPTCHA çıkarsa, manuel olarak çözün

### Problem: "ModuleNotFoundError: No module named 'selenium'"

**Çözüm:**
```bash
# Virtual environment'ın aktif olduğundan emin olun
source venv/bin/activate  # macOS/Linux
# veya
venv\Scripts\activate     # Windows

# Paketleri tekrar yükleyin
pip install -r requirements.txt
```

---

## 📁 Dosya Yapısı

```
Linedin-GhostJob_Detector/
├── auto_analyzer.py            # Otomatik extraction ve analiz (Ana script)
├── linkedin_analyzer.py        # Analiz ve raporlama scripti
├── collections_extractor.js    # Browser console extractor (JavaScript)
├── requirements.txt            # Python bağımlılıkları
├── README.md                   # Bu dosya
├── run.sh                      # Mac/Linux çalıştırma scripti
├── run.bat                     # Windows çalıştırma scripti
├── token.txt                   # Session bilgileri (opsiyonel)
├── venv/                       # Virtual environment
└── report/                     # Oluşturulan raporlar
    ├── linkedin_jobs_master_report_YYYYMMDD_HHMMSS.csv
    ├── all_jobs_analysis_YYYYMMDD_HHMMSS.json
    └── ghost_jobs_report_YYYYMMDD_HHMMSS.json
```

---

## 📞 Destek ve İletişim

Sorun yaşarsanız veya önerileriniz varsa:

1. Script çıktısını kontrol edin
2. `report/` dizinindeki raporları inceleyin
3. README.md dosyasını tekrar okuyun

### İletişim

- **Geliştirici**: Serdar BAYRAM
- **Email**: serdarbayram01@gmail.com
- **Website**: [www.serdarbayram.net](https://www.serdarbayram.net)

---

## 📄 Lisans

Bu proje eğitim amaçlıdır. LinkedIn'in kullanım şartlarına uygun olarak kullanın.

---

## 🏗️ Sistem Mimarisi

Aşağıda scriptin çalışma mimarisi ve veri akışı gösterilmektedir:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LinkedIn Ghost Job Analyzer                      │
│                              auto_analyzer.py                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          1. BAŞLATMA (main())                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • Komut satırı parametrelerini parse et (URL, email, password)   │  │
│  │ • LinkedInAutoExtractor instance oluştur                         │  │
│  │ • max_jobs değerini ayarla (varsayılan: 30)                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   2. DRIVER KURULUMU (setup_driver())                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • Chrome Options yapılandır                                      │  │
│  │ • WebDriver Manager ile ChromeDriver yükle                      │  │
│  │ • Chrome tarayıcı instance'ı oluştur                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   3. GİRİŞ YAPMA (login_with_credentials())             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │ Email/Password Varsa:                                    │  │  │
│  │  │ • LinkedIn login sayfasına git                           │  │  │
│  │  │ • Email input alanını bul ve doldur                      │  │  │
│  │  │ • Password input alanını bul ve doldur                    │  │  │
│  │  │ • Sign in butonuna tıkla                                 │  │  │
│  │  │ • Giriş başarısını kontrol et                            │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │ Token Varsa (token.txt):                                  │  │  │
│  │  │ • Session cookie'lerini yükle (li_at)                   │  │  │
│  │  │ • Cookie'leri tarayıcıya ekle                             │  │  │
│  │  │ • Ana sayfaya git ve login kontrolü yap                   │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             4. İLAN TOPLAMA (extract_jobs()) - ANA DÖNGÜ                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 4.1. Hedef URL'ye Git                                            │  │
│  │      • LinkedIn iş ilanları sayfasına navigate                  │  │
│  │      • Sayfa yüklenmesini bekle                                 │  │
│  │                                                                   │  │
│  │ 4.2. Pagination Tespiti                                          │  │
│  │      • "Sayfa 1/9" formatını ara                                │  │
│  │      • Toplam sayfa sayısını çıkar (regex ile)                   │  │
│  │                                                                   │  │
│  │ 4.3. Sayfa Döngüsü (while page <= total_pages)                  │  │
│  │      • Sayfa scroll işlemi (lazy loading için)                  │  │
│  │      • Job ID toplama (JavaScript + Manuel yöntemler)            │  │
│  │      • Sonraki sayfaya geç                                      │  │
│  │                                                                   │  │
│  │ 4.4. İlan Detay Çıkarma Döngüsü (Her Job ID İçin)               │  │
│  │      • Detay sayfasına git                                      │  │
│  │      • Veri çıkarma (15+ farklı selector)                        │  │
│  │      • Job dictionary oluştur                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   5. VERİ KAYDETME (save_jobs())                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • Tüm job dictionary'lerini JSON formatına çevir                │  │
│  │ • jobs.json dosyasına kaydet                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             6. GHOST JOB ANALİZİ (linkedin_analyzer.main())              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • JSON dosyasını oku                                             │  │
│  │ • Her ilan için analiz yap (7 kriter)                            │  │
│  │ • Risk skorları hesapla (0-10 arası)                             │  │
│  │ • Ghost job tespiti                                              │  │
│  │ • CSV/JSON raporları oluştur                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   7. TEMİZLİK (close())                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ • WebDriver.quit() ile tarayıcıyı kapat                         │  │
│  │ • Tüm kaynakları serbest bırak                                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ✅ İŞLEM TAMAMLANDI
                         📁 Raporlar report/ dizininde
```

### Bileşenler ve İlişkiler

```
┌──────────────────────┐         ┌──────────────────────┐
│  auto_analyzer.py    │────────▶│ linkedin_analyzer.py │
│  (Ana Script)        │         │  (Analiz Modülü)    │
└──────────────────────┘         └──────────────────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────┐
│  Selenium WebDriver   │         │  Risk Skorlama       │
│  (Browser Control)    │         │  Algoritması         │
└──────────────────────┘         └──────────────────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌──────────────────────┐         ┌──────────────────────┐
│ collections_extractor │         │  CSV/JSON Report     │
│      .js              │         │  Generator           │
│  (JS Injector)        │         └──────────────────────┘
└──────────────────────┘
```

### Veri Akışı

```
User Input (URL, email, password, max_jobs)
         │
         ▼
┌────────────────┐
│  auto_analyzer  │
│   .main()      │
└────────────────┘
         │
         ▼
┌────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Login Process │────▶│  Job Extract │────▶│  Data Parse  │
└────────────────┘     └──────────────┘     └──────────────┘
         │                     │                     │
         │                     │                     ▼
         │                     │            ┌──────────────┐
         │                     │            │  jobs.json   │
         │                     │            └──────────────┘
         │                     │                     │
         │                     │                     ▼
         │                     │            ┌──────────────┐
         │                     │            │  Analysis     │
         │                     │            │  (Risk Score) │
         │                     │            └──────────────┘
         │                     │                     │
         │                     │                     ▼
         │                     │            ┌──────────────┐
         │                     └───────────▶│  CSV/JSON     │
         │                                  │  Reports      │
         │                                  └──────────────┘
         │
         ▼
    Browser Close
```

---

<div align="center">

**⭐ Bu projeyi beğendiyseniz, GitHub'da star vermeyi unutmayın! ⭐**

---

Made with ❤️ for LinkedIn Job Analysis Community

</div>
