#!/usr/bin/env python3
"""
LinkedIn Otomatik Ghost Job Analyzer

Bu script token.txt dosyasındaki session bilgilerini kullanarak
LinkedIn'den otomatik olarak iş ilanlarını çeker ve ghost job analizi yapar.
"""

import json
import os
import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import linkedin_analyzer

class LinkedInAutoExtractor:
    def __init__(self, session_info_path='token.txt', email=None, password=None):
        self.session_info_path = session_info_path
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.driver = None
        self.session_info = None
        self.email = email
        self.password = password
        
    def load_session_info(self):
        """Token dosyasından session bilgilerini yükle"""
        try:
            with open(self.session_info_path, 'r', encoding='utf-8') as f:
                self.session_info = json.load(f)
            print(f"✅ Session bilgileri yüklendi: {self.session_info_path}")
            return True
        except FileNotFoundError:
            print(f"❌ Hata: {self.session_info_path} dosyası bulunamadı!")
            print("\n💡 Önce browser console'da get_session_info.js kodunu çalıştırın")
            return False
        except json.JSONDecodeError:
            print(f"❌ Hata: {self.session_info_path} dosyası geçersiz JSON formatında!")
            return False
    
    def setup_driver(self, use_existing_chrome=False, remote_debugging_port=9222):
        """Chrome driver'ı session bilgileriyle kur"""
        chrome_options = Options()
        
        # User agent (session_info varsa)
        if self.session_info and self.session_info.get('userAgent'):
            chrome_options.add_argument(f'user-agent={self.session_info["userAgent"]}')
        
        # Mevcut Chrome session'ına bağlan (remote debugging)
        if use_existing_chrome:
            print(f"🔗 Mevcut Chrome session'ına bağlanılıyor (port {remote_debugging_port})...")
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{remote_debugging_port}")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✅ Mevcut Chrome session'ına bağlanıldı")
                return True
            except Exception as e:
                print(f"⚠️ Mevcut Chrome'a bağlanılamadı: {e}")
                print("💡 Chrome'u remote debugging modunda başlatmanız gerekiyor")
                return False
        
        # Yeni Chrome instance başlat
        # Headless mode (opsiyonel - test için kapatabilirsiniz)
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # WebDriver Manager kullan (chromedriver'ı otomatik yükler)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            service = Service(ChromeDriverManager().install())
        except:
            service = None
        
        # Email/şifre ile giriş yapılacaksa session bilgilerini yükleme
        if self.email and self.password:
            print("📧 Email/şifre ile giriş yapılacak, session bilgileri atlanıyor...")
            # Session bilgilerini yükleme kısmını atla
            try:
                if service:
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_script_timeout(600)
                print("✅ Chrome driver başlatıldı")
                return True
            except Exception as e:
                print(f"❌ Chrome driver başlatılamadı: {e}")
                return False
        
        try:
            if service:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            # Script timeout'u artır (10 dakika - extractor uzun sürebilir)
            self.driver.set_script_timeout(600)
            print("✅ Chrome driver başlatıldı")
            
            # Session bilgilerini yükle
            self.driver.get("https://www.linkedin.com")
            
            # Cookies ekle - önce allCookies varsa onu kullan
            cookies_to_add = self.session_info.get('allCookies', self.session_info.get('cookies', {}))
            
            if cookies_to_add:
                print(f"📋 {len(cookies_to_add)} cookie ekleniyor...")
                for name, value in cookies_to_add.items():
                    try:
                        # Cookie değerini temizle (tırnak işaretlerini kaldır)
                        clean_value = str(value).strip('"').strip("'")
                        self.driver.add_cookie({
                            'name': name, 
                            'value': clean_value, 
                            'domain': '.linkedin.com'
                        })
                    except Exception as e:
                        print(f"⚠️ Cookie eklenemedi ({name}): {e}")
                
                # li_at kontrolü
                if 'li_at' not in cookies_to_add:
                    print("⚠️ UYARI: li_at cookie bulunamadı!")
                    print("   LinkedIn authentication başarısız olabilir.")
                    print("   Lütfen LinkedIn ana sayfasından (linkedin.com) session bilgilerini çıkarın.")
                else:
                    print("✅ li_at cookie bulundu")
            
            # LocalStorage ekle
            if 'localStorage' in self.session_info:
                self.driver.execute_script("""
                    var localStorage = arguments[0];
                    for (var key in localStorage) {
                        window.localStorage.setItem(key, localStorage[key]);
                    }
                """, self.session_info['localStorage'])
            
            # SessionStorage ekle
            if 'sessionStorage' in self.session_info:
                self.driver.execute_script("""
                    var sessionStorage = arguments[0];
                    for (var key in sessionStorage) {
                        window.sessionStorage.setItem(key, sessionStorage[key]);
                    }
                """, self.session_info['sessionStorage'])
            
            # Sayfayı yenile
            self.driver.refresh()
            time.sleep(5)
            
            # Login kontrolü
            current_url = self.driver.current_url
            if "login" in current_url.lower() or "authwall" in current_url.lower():
                print("⚠️ Login sayfasına yönlendirildi. Session bilgileri geçersiz olabilir.")
                print("💡 Çözüm: LinkedIn ana sayfasından (linkedin.com) session bilgilerini tekrar çıkarın")
                return False
            
            print("✅ Session bilgileri yüklendi")
            return True
            
        except Exception as e:
            print(f"❌ Chrome driver başlatılamadı: {e}")
            print("\n💡 Chrome ve chromedriver'ın yüklü olduğundan emin olun")
            return False
    
    def login_with_credentials(self):
        """Email ve şifre ile LinkedIn'e giriş yap"""
        if not self.email or not self.password:
            return False
        
        print(f"\n🔐 LinkedIn'e giriş yapılıyor...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(5)  # Sayfanın tam yüklenmesini bekle
        
        try:
            # Email input - farklı selector'ları dene
            email_input = None
            email_selectors = [
                (By.ID, "username"),
                (By.NAME, "session_key"),
                (By.XPATH, "//input[@id='username']"),
                (By.XPATH, "//input[@name='session_key']"),
                (By.CSS_SELECTOR, "input#username"),
                (By.CSS_SELECTOR, "input[name='session_key']")
            ]
            
            for selector_type, selector_value in email_selectors:
                try:
                    email_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    break
                except:
                    continue
            
            if not email_input:
                print("❌ Email input bulunamadı!")
                return False
            
            # Email input'a scroll et ve tıkla
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_input)
            time.sleep(1)
            email_input.click()
            time.sleep(1)
            email_input.clear()
            email_input.send_keys(self.email)
            print("✅ Email girildi")
            time.sleep(1)
            
            # Password input - farklı selector'ları dene
            password_input = None
            password_selectors = [
                (By.ID, "password"),
                (By.NAME, "session_password"),
                (By.XPATH, "//input[@id='password']"),
                (By.XPATH, "//input[@name='session_password']"),
                (By.CSS_SELECTOR, "input#password"),
                (By.CSS_SELECTOR, "input[name='session_password']")
            ]
            
            for selector_type, selector_value in password_selectors:
                try:
                    password_input = self.driver.find_element(selector_type, selector_value)
                    break
                except:
                    continue
            
            if not password_input:
                print("❌ Password input bulunamadı!")
                return False
            
            # Password input'a scroll et ve tıkla
            self.driver.execute_script("arguments[0].scrollIntoView(true);", password_input)
            time.sleep(1)
            password_input.click()
            time.sleep(1)
            password_input.clear()
            password_input.send_keys(self.password)
            print("✅ Şifre girildi")
            time.sleep(2)
            
            # Login button - farklı selector'ları dene
            login_button = None
            login_selectors = [
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                (By.XPATH, "//button[contains(text(), 'Oturum aç')]"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button.btn-primary"),
                (By.CSS_SELECTOR, "button[data-litms-control-urn='login-submit']")
            ]
            
            for selector_type, selector_value in login_selectors:
                try:
                    login_button = self.driver.find_element(selector_type, selector_value)
                    if login_button.is_displayed() and login_button.is_enabled():
                        break
                except:
                    continue
            
            if not login_button:
                print("❌ Login button bulunamadı!")
                return False
            
            # Login button'a scroll et ve tıkla
            self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
            time.sleep(1)
            login_button.click()
            print("✅ Giriş butonuna tıklandı")
            
            # Giriş yapılmasını bekle (daha uzun süre)
            print("⏳ Giriş yapılıyor, bekleniyor...")
            time.sleep(10)  # 10 saniye bekle
            
            # Giriş başarılı mı kontrol et
            current_url = self.driver.current_url.lower()
            print(f"📄 Mevcut URL: {current_url}")
            
            if "login" not in current_url and "authwall" not in current_url:
                print("✅ Giriş başarılı!")
                return True
            else:
                print("⚠️ Giriş başarısız olabilir. Sayfa kontrol ediliyor...")
                # Captcha veya 2FA kontrolü
                if "challenge" in current_url or "checkpoint" in current_url:
                    print("⚠️ LinkedIn güvenlik kontrolü gerekiyor. Lütfen manuel olarak tamamlayın.")
                    print("💡 Browser açık kalacak, kontrolü tamamladıktan sonra devam edin...")
                    input("Güvenlik kontrolünü tamamladıktan sonra Enter'a basın...")
                    return True
                # Tekrar dene
                print("🔄 Giriş tekrar deneniyor...")
                time.sleep(5)
                current_url = self.driver.current_url.lower()
                if "login" not in current_url and "authwall" not in current_url:
                    print("✅ Giriş başarılı (ikinci deneme)!")
                    return True
                return False
                
        except Exception as e:
            print(f"❌ Giriş hatası: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_jobs(self, url=None, max_jobs=30):
        """LinkedIn'den iş ilanlarını çıkar"""
        if not url:
            url = "https://www.linkedin.com/jobs/collections/recommended/"
        
        # ÖNCE LOGIN OL - Email/şifre varsa direkt login yap
        if self.email and self.password:
            print("\n" + "="*80)
            print("🔐 ADIM 1: LinkedIn'e Giriş Yapılıyor...")
            print("="*80)
            
            # Login sayfasına git
            print("📄 Login sayfasına gidiliyor...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(5)
            
            # Login yap
            if not self.login_with_credentials():
                print("❌ Giriş başarısız! Email ve şifreyi kontrol edin.")
                return []
            
            # Login başarılı mı kontrol et
            print("\n🔍 Login başarısı kontrol ediliyor...")
            time.sleep(3)
            current_url = self.driver.current_url.lower()
            
            # Eğer hala login sayfasındaysak, tekrar dene
            if "login" in current_url or "authwall" in current_url:
                print("⚠️ Hala login sayfasındayız, tekrar giriş yapılıyor...")
                if not self.login_with_credentials():
                    print("❌ Giriş başarısız!")
                    return []
                time.sleep(5)
                current_url = self.driver.current_url.lower()
            
            # Login başarılı kontrolü
            if "login" in current_url or "authwall" in current_url:
                print("❌ Giriş başarısız! Lütfen manuel olarak giriş yapın.")
                print("💡 Browser açık kalacak, giriş yaptıktan sonra script devam edecek...")
                input("Giriş yaptıktan sonra Enter'a basın...")
            else:
                print("✅ Login başarılı!")
            
            # Ana sayfaya git ve login kontrolü yap
            print("📄 Ana sayfaya gidiliyor (login kontrolü için)...")
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(5)
            
            # Login kontrolü - feed sayfasında mıyız?
            current_url = self.driver.current_url.lower()
            if "feed" in current_url or "linkedin.com" in current_url and "login" not in current_url:
                print("✅ Login başarılı, feed sayfasındayız!")
            else:
                print("⚠️ Login kontrolü başarısız, tekrar denenecek...")
                if "login" in current_url or "authwall" in current_url:
                    if not self.login_with_credentials():
                        print("❌ Giriş başarısız!")
                        return []
                    time.sleep(5)
        
        # HEDEF URL'YE GİT
        print("\n" + "="*80)
        print("🔍 ADIM 2: Hedef Sayfaya Gidiliyor...")
        print("="*80)
        print(f"📄 Hedef URL: {url}")
        self.driver.get(url)
        time.sleep(4)  # Sayfanın yüklenmesini bekle (daha hızlı)
        
        # Login kontrolü - hedef sayfada login gerekiyor mu?
        current_url = self.driver.current_url.lower()
        if "login" in current_url or "authwall" in current_url:
            print("⚠️ Hedef sayfada login gerekiyor, giriş yapılıyor...")
            if self.email and self.password:
                if not self.login_with_credentials():
                    print("❌ Giriş başarısız!")
                    return []
                # Tekrar hedef URL'ye git
                self.driver.get(url)
                time.sleep(4)
            else:
                print("⚠️ Login gerekiyor ama email/şifre yok.")
                return []
        
        # Sayfa yüklendi mi kontrol et
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("⚠️ Sayfa yüklenemedi")
            return []
        
        # "Sign in to view more jobs" kontrolü
        time.sleep(2)
        try:
            # "Sign in to view more jobs" mesajını ara
            sign_in_texts = [
                "Sign in to view more jobs",
                "Daha fazla iş ilanı görmek için giriş yapın",
                "Sign in",
                "Oturum aç"
            ]
            
            page_text = self.driver.page_source.lower()
            sign_in_found = any(text.lower() in page_text for text in sign_in_texts)
            
            if sign_in_found:
                print("🔐 'Sign in to view more jobs' mesajı tespit edildi, giriş yapılıyor...")
                
                # Email/şifre varsa direkt login yap
                if self.email and self.password:
                    if self.login_with_credentials():
                        # Giriş başarılı, hedef URL'ye geri dön
                        print(f"✅ Giriş başarılı, hedef sayfaya geri dönülüyor: {url}")
                        self.driver.get(url)
                        time.sleep(4)
                    else:
                        print("❌ Giriş başarısız!")
                        return []
        except Exception as e:
            print(f"⚠️ Sign in kontrolü sırasında hata: {e}")
        
        # ADIM 3: İLANLARI TOPLA VE LİNKLERE TIKLA (PAGINATION İLE)
        print("\n" + "="*80)
        print("🔍 ADIM 3: İlanlar Toplanıyor (Tüm Sayfalar)...")
        print("="*80)
        print("✅ Sayfa yüklendi, ilanlar çıkarılıyor...")
        
        # Tüm sayfalardan ilanları topla
        all_jobs = []
        all_job_ids = set()
        current_page = 1
        total_pages = 1
        
        # Sayfa sayısını tespit et
        try:
            # Pagination bilgisini bul (örn: "Sayfa 1/9" veya "Sayfa 2/40")
            pagination_selectors = [
                # Yeni selector'lar - browser snapshot'tan bulundu
                (By.XPATH, "//*[contains(text(), 'Sayfa ') and contains(text(), '/')]"),
                (By.XPATH, "//div[contains(@class, 'generic') and contains(., 'Sayfa') and contains(., '/')]"),
                (By.CSS_SELECTOR, "div[class*='pagination']"),
                # Eski selector'lar
                (By.CSS_SELECTOR, ".jobs-search-pagination__page-state"),
                (By.CSS_SELECTOR, "[class*='pagination'][class*='page-state']"),
                (By.XPATH, "//*[contains(text(), 'Page ') and contains(text(), 'of')]"),
                (By.CSS_SELECTOR, "span[aria-label*='Page']"),
            ]
            
            page_info_text = None
            for selector_type, selector_value in pagination_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    for el in elements:
                        # Birden fazla yöntemle metni al
                        text = el.text.strip()
                        if not text:
                            # .text boşsa, innerText veya textContent dene
                            try:
                                text = el.get_attribute('innerText') or el.get_attribute('textContent') or ''
                                text = text.strip()
                            except:
                                pass
                        
                        # "Sayfa 2/40" veya "Page 2 of 40" formatını ara
                        if text and (('sayfa' in text.lower() and '/' in text) or ('page' in text.lower() and ('/' in text or 'of' in text.lower()))):
                            page_info_text = text
                            break
                    if page_info_text:
                        break
                except Exception as e:
                    continue
            
            if page_info_text:
                # "Sayfa 1/9" veya "Page 1 of 9" formatından toplam sayfa sayısını çıkar
                import re
                match = re.search(r'(\d+)\s*/\s*(\d+)', page_info_text)
                if match:
                    current_page = int(match.group(1))
                    total_pages = int(match.group(2))
                    print(f"📄 Sayfa bilgisi bulundu: {page_info_text} (Toplam {total_pages} sayfa)")
                else:
                    # Alternatif format: "Page 1 of 9"
                    match = re.search(r'of\s*(\d+)', page_info_text, re.IGNORECASE)
                    if match:
                        total_pages = int(match.group(1))
                        print(f"📄 Sayfa bilgisi bulundu: {page_info_text} (Toplam {total_pages} sayfa)")
                    else:
                        print(f"⚠️ Sayfa bilgisi bulundu ama parse edilemedi: {page_info_text}")
            else:
                print("⚠️ Sayfa bilgisi bulunamadı, sadece mevcut sayfa taranacak")
        except Exception as e:
            print(f"⚠️ Sayfa sayısı tespit edilemedi: {e}")
        
        # Tüm sayfalardan ilanları topla
        page = 1
        while len(all_job_ids) < max_jobs and page <= total_pages:
            print(f"\n📄 Sayfa {page}/{total_pages} taranıyor... (Şu ana kadar {len(all_job_ids)} ilan bulundu)")
            
            # Sayfanın tam yüklenmesini bekle
            time.sleep(3)
            
            # Sayfayı agresif bir şekilde kaydır (lazy loading için)
            # LinkedIn'de tüm ilanların yüklenmesi için birden fazla scroll gerekebilir
            for scroll_attempt in range(5):
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_attempt / 4});")
                time.sleep(1)
            
            # En alta kaydır
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Tekrar yukarı kaydır (bazı ilanlar sadece scroll sonrası görünür)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Bu sayfadaki ilanları topla
            page_jobs = []
            
            # Önce manuel olarak job ID'leri bul (daha güvenilir)
            try:
                import re
                
                # 1. Önce job list container'larından direkt job ID'leri bul
                job_list_selectors = [
                    (By.CSS_SELECTOR, "a[href*='/jobs/view/']"),
                    (By.CSS_SELECTOR, "a.job-card-container__link"),
                    (By.CSS_SELECTOR, "a[data-tracking-control-name='public_jobs_jserp-result_search-card']"),
                    (By.XPATH, "//a[contains(@href, '/jobs/view/')]"),
                ]
                
                for selector_type, selector_value in job_list_selectors:
                    try:
                        job_links = self.driver.find_elements(selector_type, selector_value)
                        for link in job_links:
                            try:
                                href = link.get_attribute('href') or ''
                                if '/jobs/view/' in href:
                                    match = re.search(r'/jobs/view/(\d+)', href)
                                    if match:
                                        job_id = match.group(1)
                                        if job_id not in all_job_ids:
                                            all_job_ids.add(job_id)
                                            page_jobs.append({
                                                'link': f'https://www.linkedin.com/jobs/view/{job_id}/',
                                                'job_id': job_id
                                            })
                            except:
                                continue
                    except:
                        continue
                
                # 2. Sayfa kaynağından job ID'leri ara (fallback)
                jobs_before_source = len(all_job_ids)
                page_source = self.driver.page_source
                matches = re.findall(r'/jobs/view/(\d+)', page_source)
                for job_id in matches:
                    if job_id not in all_job_ids:
                        all_job_ids.add(job_id)
                        page_jobs.append({
                            'link': f'https://www.linkedin.com/jobs/view/{job_id}/',
                            'job_id': job_id
                        })
                
                # 3. Tüm link'lerden de job ID'leri bul (son fallback)
                if len(all_job_ids) == jobs_before_source:  # Eğer sayfa kaynağından da ilan bulunamadıysa
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        try:
                            href = link.get_attribute('href') or ''
                            if '/jobs/view/' in href:
                                match = re.search(r'/jobs/view/(\d+)', href)
                                if match:
                                    job_id = match.group(1)
                                    if job_id not in all_job_ids:
                                        all_job_ids.add(job_id)
                                        page_jobs.append({
                                            'link': f'https://www.linkedin.com/jobs/view/{job_id}/',
                                            'job_id': job_id
                                        })
                        except:
                            continue
                
                print(f"   ✅ Sayfa {page}'de {len(page_jobs)} yeni ilan bulundu (Toplam: {len(all_job_ids)} ilan)")
                
            except Exception as e:
                print(f"   ⚠️ Sayfa {page}'de hata: {e}")
            
            # Hedef sayıya ulaştıysak dur
            if len(all_job_ids) >= max_jobs:
                print(f"   ✅ Hedef sayıya ulaşıldı ({max_jobs} ilan), sayfa taraması durduruluyor")
                break
            
            # Sonraki sayfaya git (eğer daha fazla sayfa varsa)
            if page < total_pages:
                try:
                    # Sonraki sayfa butonunu bul
                    next_button = None
                    next_selectors = [
                        # Yeni selector - browser snapshot'tan bulundu
                        (By.XPATH, "//button[contains(@name, 'Sonraki') or contains(text(), 'Sonraki sayfayı görüntüle')]"),
                        (By.XPATH, "//button[@aria-label='Sonraki sayfayı görüntüle' or contains(@aria-label, 'next page') or contains(@aria-label, 'Sonraki')]"),
                        # Eski selector'lar
                        (By.XPATH, "//button[@aria-label='Next' or @aria-label='İleri' or contains(@aria-label, 'Next page')]"),
                        (By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'İleri') or contains(text(), 'Sonraki')]"),
                        (By.CSS_SELECTOR, "button[aria-label*='Next']"),
                        (By.CSS_SELECTOR, "button[aria-label*='İleri']"),
                        (By.CSS_SELECTOR, "button[aria-label*='Sonraki']"),
                        (By.CSS_SELECTOR, ".jobs-search-pagination__button--next"),
                        (By.CSS_SELECTOR, "[data-test-pagination-page-btn='next']"),
                    ]
                    
                    for selector_type, selector_value in next_selectors:
                        try:
                            buttons = self.driver.find_elements(selector_type, selector_value)
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    next_button = btn
                                    break
                            if next_button:
                                break
                        except:
                            continue
                    
                    if next_button:
                        # Sonraki sayfa butonuna tıkla
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        next_button.click()
                        print(f"   ➡️ Sonraki sayfaya geçiliyor...")
                        time.sleep(4)  # Yeni sayfanın yüklenmesini bekle
                        page += 1
                    else:
                        # Sayfa numarasına tıklayarak git
                        try:
                            # Sayfa numarası butonlarını bul - yeni selector'lar
                            next_page_num = page + 1
                            page_button_selectors = [
                                # Yeni format: "3. Sayfa", "4. Sayfa"
                                (By.XPATH, f"//button[contains(@name, '{next_page_num}. Sayfa') or contains(text(), '{next_page_num}. Sayfa')]"),
                                (By.XPATH, f"//button[contains(@aria-label, '{next_page_num}. Sayfa') or @name='{next_page_num}. Sayfa']"),
                                # Eski format
                                (By.CSS_SELECTOR, "button[data-test-pagination-page-btn]"),
                            ]
                            
                            page_button_found = False
                            for selector_type, selector_value in page_button_selectors:
                                try:
                                    page_buttons = self.driver.find_elements(selector_type, selector_value)
                                    for btn in page_buttons:
                                        try:
                                            btn_text = btn.text.strip()
                                            # "3. Sayfa", "4. Sayfa" veya sadece "3", "4" formatını kabul et
                                            if btn_text == str(next_page_num) or btn_text == f"{next_page_num}. Sayfa" or btn_text.startswith(f"{next_page_num}."):
                                                self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                                time.sleep(1)
                                                btn.click()
                                                print(f"   ➡️ Sayfa {next_page_num}'e geçiliyor... (Buton: '{btn_text}')")
                                                time.sleep(4)
                                                page += 1
                                                page_button_found = True
                                                break
                                        except:
                                            continue
                                    if page_button_found:
                                        break
                                except:
                                    continue
                            
                            # Sayfa numarası butonu bulunamadıysa, URL'yi değiştir
                            if not page_button_found:
                                if 'start=' in url or 'page=' in url:
                                    # URL'de sayfa parametresi varsa güncelle
                                    import urllib.parse
                                    parsed = urllib.parse.urlparse(url)
                                    params = urllib.parse.parse_qs(parsed.query)
                                    params['start'] = [str(page * 25)]  # Her sayfada genellikle 25 ilan var
                                    new_url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(params, doseq=True)))
                                    self.driver.get(new_url)
                                    print(f"   ➡️ Sayfa {page + 1}'e URL ile geçiliyor...")
                                    time.sleep(4)
                                    page += 1
                                else:
                                    print(f"   ⚠️ Sonraki sayfa butonu bulunamadı, sayfa taraması sonlandırılıyor")
                                    break
                        except Exception as e:
                            print(f"   ⚠️ Sonraki sayfaya geçilemedi: {e}")
                            break
                except Exception as e:
                    print(f"   ⚠️ Sayfa geçişi sırasında hata: {e}")
                    break
            else:
                # Son sayfaya ulaşıldı
                print(f"   ✅ Son sayfaya ulaşıldı")
                break
        
        # Toplanan tüm ilanları formatla
        result = []
        for job_id in list(all_job_ids)[:max_jobs]:
            result.append({
                'link': f'https://www.linkedin.com/jobs/view/{job_id}/',
                'title': f'İlan #{job_id}',
                'company': '',
                'location': '',
                'posted_date': '',
                'applicants': '',
                'recruiter_info': '',
                'response_insight': '',
                'job_description': '',
                'work_type': '',
                'employment_type': '',
                'salary': '',
                'posting_status': ''
            })
        
        print(f"\n✅ Toplam {len(result)} ilan toplandı ({total_pages} sayfadan)")
        
        # Her ilan için detay sayfasına git ve bilgileri çıkar
        if result:
            # İlk max_jobs ilanı al
            limited_result = result[:max_jobs]
            print(f"\n" + "="*80)
            print(f"🔍 ADIM 4: İlan Detaylarına Gidiliyor...")
            print("="*80)
            print(f"📋 İlk {max_jobs} ilan için detaylı bilgiler çıkarılıyor... (Toplam: {len(result)} ilan)")
            enhanced_jobs = []
            
            for idx, job in enumerate(limited_result, 1):
                job_id = job.get('link', '').split('/jobs/view/')[-1].rstrip('/')
                if not job_id:
                    # URL'den job ID çıkar
                    import re
                    match = re.search(r'/jobs/view/(\d+)', job.get('link', ''))
                    if match:
                        job_id = match.group(1)
                
                print(f"\n   📋 İlan {idx}/{max_jobs}: Job ID {job_id}")
                print(f"   🔗 Link: https://www.linkedin.com/jobs/view/{job_id}/")
                
                # Sadece eksik bilgiler varsa detay sayfasına git (daha hızlı)
                needs_details = (not job.get('title') or job.get('title', '').startswith('İlan #') or \
                   not job.get('company') or not job.get('location') or not job.get('posted_date'))
                
                if needs_details:
                    # Detay sayfasına git ve bilgileri çıkar
                    try:
                        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                        print(f"      🔗 Detay sayfasına gidiliyor: {job_url}")
                        self.driver.get(job_url)
                        time.sleep(2)  # Sayfanın yüklenmesini bekle (daha hızlı)
                        
                        # Login kontrolü - detay sayfasında login gerekiyor mu?
                        current_url = self.driver.current_url.lower()
                        if "login" in current_url or "authwall" in current_url:
                            print(f"      ⚠️ Detay sayfasında login gerekiyor, giriş yapılıyor...")
                            if self.email and self.password:
                                if self.login_with_credentials():
                                    # Tekrar detay sayfasına git
                                    self.driver.get(job_url)
                                    time.sleep(2)
                                else:
                                    print(f"      ❌ Giriş başarısız, bu ilan atlanıyor...")
                                    enhanced_jobs.append(job)
                                    continue
                            else:
                                print(f"      ⚠️ Login gerekiyor ama email/şifre yok, bu ilan atlanıyor...")
                                enhanced_jobs.append(job)
                                continue
                        
                        # Sayfanın yüklenmesini bekle (daha hızlı)
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                        except:
                            pass
                        
                        time.sleep(2)  # Ekstra bekleme (daha kısa)
                        
                        # Sayfa içeriğinin yüklenmesini bekle (daha hızlı)
                        try:
                            WebDriverWait(self.driver, 8).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            # H1 elementinin yüklenmesini bekle (iş başlığı) - daha kısa timeout
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                                )
                            except:
                                pass  # H1 yoksa devam et
                        except:
                            pass
                        
                        # Ekstra bekleme - dinamik içerik için (daha kısa)
                        time.sleep(1)
                        
                        # Başlık - daha fazla selector dene
                        if not job.get('title') or job.get('title', '').startswith('İlan #'):
                            title_selectors = [
                                (By.CSS_SELECTOR, "h1.job-title"),
                                (By.CSS_SELECTOR, "h1[class*='job-title']"),
                                (By.CSS_SELECTOR, "h1.jobs-details-top-card__job-title"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__job-title h1"),
                                (By.CSS_SELECTOR, "h1.jobs-details-top-card__job-title-text"),
                                (By.CSS_SELECTOR, ".jobs-details__top-card__job-title h1"),
                                (By.CSS_SELECTOR, "h1.top-card-layout__title"),
                                (By.CSS_SELECTOR, "h1[data-test-id='job-title']"),
                                (By.XPATH, "//h1[contains(@class, 'job-title')]"),
                                (By.XPATH, "//h1[contains(@class, 'jobs-details')]"),
                                (By.XPATH, "//h1[contains(@class, 'top-card')]"),
                                (By.XPATH, "//h1[not(contains(text(), 'LinkedIn')) and not(contains(text(), 'Sign in')) and string-length(text()) > 10]"),
                                (By.TAG_NAME, "h1")
                            ]
                            for selector_type, selector_value in title_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and len(text) > 3 and 'LinkedIn' not in text and 'Sign in' not in text and 'Jobs' != text and 'Job' != text and not text.startswith('İlan #'):
                                            job['title'] = text
                                            break
                                    if job.get('title') and not job.get('title', '').startswith('İlan #'):
                                        break
                                except:
                                    continue
                        
                        # Şirket - daha fazla selector dene
                        if not job.get('company'):
                            company_selectors = [
                                (By.CSS_SELECTOR, "a[data-tracking-control-name='public_jobs_topcard-org-name']"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__company-name"),
                                (By.CSS_SELECTOR, "a[href*='/company/']"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__company-name a"),
                                (By.CSS_SELECTOR, ".jobs-details__top-card-company-name a"),
                                (By.CSS_SELECTOR, ".jobs-details__top-card__company-name a"),
                                (By.XPATH, "//a[contains(@href, '/company/')]"),
                                (By.XPATH, "//a[contains(@data-tracking-control-name, 'org-name')]")
                            ]
                            for selector_type, selector_value in company_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and len(text) > 1 and 'LinkedIn' not in text and 'Company' not in text:
                                            job['company'] = text
                                            break
                                    if job.get('company'):
                                        break
                                except:
                                    continue
                        
                        # Lokasyon
                        if not job.get('location'):
                            location_selectors = [
                                (By.CSS_SELECTOR, ".jobs-details-top-card__bullet"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__job-info span"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__primary-description"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__job-info li"),
                                (By.CSS_SELECTOR, ".top-card-layout__entity-info li"),
                                (By.CSS_SELECTOR, "[data-test-id='job-location']"),
                                (By.XPATH, "//span[contains(@class, 'job-criteria__text')]"),
                                (By.XPATH, "//li[contains(text(), ',') or contains(text(), 'Istanbul') or contains(text(), 'İstanbul') or contains(text(), 'Turkey') or contains(text(), 'Türkiye')]")
                            ]
                            for selector_type, selector_value in location_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and (',' in text or 'Istanbul' in text or 'İstanbul' in text or 'Turkey' in text or 'Türkiye' in text or 'Remote' in text or 'Hybrid' in text or 'On-site' in text):
                                            job['location'] = text
                                            break
                                    if job.get('location'):
                                        break
                                except:
                                    continue
                            
                            # Eğer hala bulunamadıysa, sayfa kaynağından ara
                            if not job.get('location'):
                                try:
                                    page_text = self.driver.page_source
                                    import re
                                    location_patterns = [
                                        r'(Istanbul|İstanbul|Ankara|İzmir|Bursa|Antalya|Adana|Gaziantep|Konya|Kayseri|Türkiye|Turkey)',
                                        r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*),\s*(Türkiye|Turkey)',
                                        r'(Remote|Uzaktan|Hybrid|Hibrit|On-site|Yerinde)'
                                    ]
                                    for pattern in location_patterns:
                                        match = re.search(pattern, page_text, re.IGNORECASE)
                                        if match:
                                            job['location'] = match.group(0)
                                            break
                                except:
                                    pass
                        
                        # Tarih - daha fazla selector dene
                        if not job.get('posted_date'):
                            date_selectors = [
                                (By.CSS_SELECTOR, "time[datetime]"),
                                (By.CSS_SELECTOR, "time"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__posted-date"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__job-info time"),
                                (By.CSS_SELECTOR, ".topcard__flavor--metadata"),
                                (By.CSS_SELECTOR, "[data-test-id='job-posted-date']"),
                                (By.XPATH, "//time[@datetime]"),
                                (By.XPATH, "//time"),
                                (By.XPATH, "//span[contains(text(), 'gün önce') or contains(text(), 'ay önce') or contains(text(), 'hafta önce') or contains(text(), 'ago')]")
                            ]
                            for selector_type, selector_value in date_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        date_val = el.get_attribute('datetime') or el.text.strip()
                                        if date_val and len(date_val) > 0:
                                            job['posted_date'] = date_val
                                            break
                                    if job.get('posted_date'):
                                        break
                                except:
                                    continue
                            
                            # Eğer hala bulunamadıysa, sayfa kaynağından ara
                            if not job.get('posted_date'):
                                try:
                                    page_text = self.driver.page_source
                                    import re
                                    date_patterns = [
                                        r'(\d+\s*(gün|ay|hafta|day|month|week)\s*önce|ago)',
                                        r'(datetime="[^"]+")',
                                        r'(\d{4}-\d{2}-\d{2})'
                                    ]
                                    for pattern in date_patterns:
                                        match = re.search(pattern, page_text, re.IGNORECASE)
                                        if match:
                                            job['posted_date'] = match.group(0)
                                            break
                                except:
                                    pass
                        
                        # Başvuru sayısı - daha fazla selector dene
                        if not job.get('applicants'):
                            applicant_selectors = [
                                (By.CSS_SELECTOR, ".jobs-details-top-card__job-info-text"),
                                (By.CSS_SELECTOR, "[class*='applicant']"),
                                (By.CSS_SELECTOR, ".num-applicants__caption"),
                                (By.CSS_SELECTOR, ".jobs-details-top-card__applicant-count"),
                                (By.CSS_SELECTOR, "[class*='applicant-count']"),
                                (By.XPATH, "//*[contains(@class, 'applicant')]"),
                                (By.XPATH, "//*[contains(text(), 'applicant') or contains(text(), 'başvuru')]")
                            ]
                            for selector_type, selector_value in applicant_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and ('applicant' in text.lower() or 'başvuru' in text.lower() or 'başvuran' in text.lower() or text.replace('+', '').replace(',', '').isdigit()):
                                            job['applicants'] = text
                                            break
                                    if job.get('applicants'):
                                        break
                                except:
                                    continue
                        
                        # İşe alım uzmanı bilgisi
                        try:
                            recruiter_selectors = [
                                (By.XPATH, "//*[contains(text(), 'İşe alım uzmanı') or contains(text(), 'tanıtılıyor') or contains(text(), 'recruiter')]"),
                                (By.CSS_SELECTOR, "[class*='recruiter']"),
                                (By.CSS_SELECTOR, "[class*='hiring']")
                            ]
                            for selector_type, selector_value in recruiter_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and ('tanıtılıyor' in text.lower() or 'recruiter' in text.lower() or 'işe alım' in text.lower()):
                                            job['recruiter_info'] = text
                                            break
                                    if job.get('recruiter_info'):
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # Yanıt içgörüsü bilgisi
                        try:
                            insight_selectors = [
                                (By.XPATH, "//*[contains(text(), 'yanıt içgörüsü') or contains(text(), 'response insight') or contains(text(), 'Henüz yanıt')]"),
                                (By.CSS_SELECTOR, "[class*='insight']"),
                                (By.CSS_SELECTOR, "[class*='response']")
                            ]
                            for selector_type, selector_value in insight_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and ('yanıt' in text.lower() or 'insight' in text.lower() or 'içgörü' in text.lower()):
                                            job['response_insight'] = text
                                            break
                                    if job.get('response_insight'):
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # Çalışma şekli (Remote, Hybrid, On-site)
                        try:
                            work_type_patterns = [
                                (r'(Remote|Uzaktan|Uzaktan\s+çalışma)', 'Remote'),
                                (r'(Hybrid|Hibrit|Hibrit\s+çalışma)', 'Hybrid'),
                                (r'(On-site|Ofis|Yerinde)', 'On-site')
                            ]
                            location_text = job.get('location', '') or self.driver.page_source
                            for pattern, work_type_value in work_type_patterns:
                                import re
                                if re.search(pattern, location_text, re.IGNORECASE):
                                    job['work_type'] = work_type_value
                                    break
                        except:
                            pass
                        
                        # İş tipi (Full-time, Part-time, Contract)
                        try:
                            employment_patterns = [
                                (r'(Full-time|Tam\s+zamanlı|Tam\s+zaman)', 'Full-time'),
                                (r'(Part-time|Yarı\s+zamanlı|Yarı\s+zaman)', 'Part-time'),
                                (r'(Contract|Sözleşmeli|Kontrat)', 'Contract'),
                                (r'(Internship|Staj|Stajyer)', 'Internship'),
                                (r'(Temporary|Geçici)', 'Temporary')
                            ]
                            page_text = self.driver.page_source
                            for pattern, emp_type_value in employment_patterns:
                                import re
                                if re.search(pattern, page_text, re.IGNORECASE):
                                    job['employment_type'] = emp_type_value
                                    break
                        except:
                            pass
                        
                        # Maaş bilgisi (varsa)
                        try:
                            salary_selectors = [
                                (By.CSS_SELECTOR, "[class*='salary']"),
                                (By.CSS_SELECTOR, "[class*='compensation']"),
                                (By.XPATH, "//*[contains(text(), 'TL') or contains(text(), '$') or contains(text(), '€')]")
                            ]
                            for selector_type, selector_value in salary_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip()
                                        if text and ('TL' in text or '$' in text or '€' in text or '£' in text):
                                            job['salary'] = text
                                            break
                                    if job.get('salary'):
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # İlan durumu bilgisi (yeniden yayınlandı, genel başvuru vb.)
                        try:
                            # Daha spesifik selector'lar kullanarak ilan durumunu tespit et
                            posting_status = []
                        
                            # 1. Yeniden yayınlandı kontrolü - Daha spesifik selector'lar
                            reposted_selectors = [
                                (By.XPATH, "//*[contains(text(), 'Yeniden yayınlandı') or contains(text(), 'Reposted') or contains(text(), 'İlan yenilendi')]"),
                                (By.CSS_SELECTOR, "[class*='reposted']"),
                                (By.CSS_SELECTOR, "[class*='renewed']"),
                                (By.CSS_SELECTOR, "[data-test-id*='repost']")
                            ]
                            
                            for selector_type, selector_value in reposted_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip().lower()
                                        if text and any(keyword in text for keyword in ['yeniden yayınlandı', 'reposted', 'ilan yenilendi', 'renewed', 'tekrar yayınlandı']):
                                            posting_status.append('Yeniden Yayınlandı')
                                            break
                                    if 'Yeniden Yayınlandı' in posting_status:
                                        break
                                except:
                                    continue
                        
                            # 2. Genel başvuru kontrolü - Daha spesifik
                            general_application_selectors = [
                                (By.XPATH, "//*[contains(text(), 'Genel başvuru') or contains(text(), 'General application') or contains(text(), 'Sürekli alıyoruz')]"),
                                (By.CSS_SELECTOR, "[class*='general-application']"),
                                (By.CSS_SELECTOR, "[class*='always-hiring']")
                            ]
                            
                            for selector_type, selector_value in general_application_selectors:
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    for el in elements:
                                        text = el.text.strip().lower()
                                        if text and any(keyword in text for keyword in ['genel başvuru', 'general application', 'open application', 'sürekli alıyoruz', 'always hiring']):
                                            posting_status.append('Genel Başvuru')
                                            break
                                    if 'Genel Başvuru' in posting_status:
                                        break
                                except:
                                    continue
                        
                            # 3. Sayfa kaynağından daha spesifik arama (sadece yukarıdaki selector'lar bulamazsa)
                            if not posting_status:
                                page_text = self.driver.page_source.lower()
                                # Sadece belirli context'lerde ara (daha az false positive için)
                                # "reposted" kelimesi "job" veya "position" ile birlikte geçiyorsa
                                if ('reposted' in page_text or 'yeniden yayınlandı' in page_text) and \
                                   ('job' in page_text or 'position' in page_text or 'ilan' in page_text):
                                    # Ama sadece belirli pattern'lerde
                                    import re
                                    reposted_patterns = [
                                        r'reposted\s+(?:this\s+)?(?:job|position)',
                                        r'(?:this\s+)?(?:job|position)\s+was\s+reposted',
                                        r'ilan\s+yeniden\s+yayınlandı',
                                        r'yeniden\s+yayınlandı\s+ilan'
                                    ]
                                    for pattern in reposted_patterns:
                                        if re.search(pattern, page_text, re.IGNORECASE):
                                            posting_status.append('Yeniden Yayınlandı')
                                            break
                            
                            # İlan durumunu kaydet
                            if posting_status:
                                job['posting_status'] = ', '.join(posting_status)
                            else:
                                job['posting_status'] = ''
                        except:
                            job['posting_status'] = ''
                            pass
                        
                        # Tüm bilgileri logla
                        print(f"      ✅ Detaylar alındı:")
                        print(f"         📌 Başlık: {job.get('title', 'N/A')[:50]}")
                        print(f"         🏢 Şirket: {job.get('company', 'N/A')}")
                        print(f"         📍 Lokasyon: {job.get('location', 'N/A')}")
                        print(f"         📅 Tarih: {job.get('posted_date', 'N/A')}")
                        print(f"         👥 Başvuru: {job.get('applicants', 'N/A')}")
                        print(f"         👤 İşe Alım: {job.get('recruiter_info', 'N/A')}")
                        print(f"         📊 Yanıt İçgörüsü: {job.get('response_insight', 'N/A')}")
                        print(f"         💼 Çalışma Şekli: {job.get('work_type', 'N/A')}")
                        print(f"         ⏰ İş Tipi: {job.get('employment_type', 'N/A')}")
                        print(f"         💰 Maaş: {job.get('salary', 'N/A')}")
                        if job.get('posting_status'):
                            print(f"         🔄 İlan Durumu: {job.get('posting_status', 'N/A')}")
                    
                    except Exception as e:
                        print(f"      ⚠️ Detay sayfası hatası: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"      ✅ Bilgiler mevcut, detay sayfasına gidilmiyor (daha hızlı)")
                
                enhanced_jobs.append(job)
                
                # Her ilanda bir kısa mola (LinkedIn rate limiting'i önlemek için) - daha kısa
                if idx < max_jobs:
                    time.sleep(0.5)
            
            # Ana sayfaya geri dön
            print(f"\n✅ Tüm ilanlar için detaylı bilgiler çıkarıldı")
            return enhanced_jobs
        
        return result
    
    def extract_job_ids_manually(self, max_jobs=30):
        """Manuel olarak sayfadan job ID'leri çıkar"""
        jobs = []
        job_ids = set()
        
        try:
            # Sayfayı daha fazla kaydır (max_jobs ilan için)
            scroll_count = max(15, max_jobs // 2)  # En az 15, veya max_jobs/2 kadar scroll
            print(f"      📜 Sayfa kaydırılıyor ({max_jobs} ilan için, {scroll_count} scroll)...")
            for i in range(scroll_count):  # Dinamik scroll sayısı
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                
                # "Daha fazla göster" butonlarını tıkla
                try:
                    show_more_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Daha fazla') or contains(text(), 'Show more') or contains(@aria-label, 'Daha fazla')]")
                    for btn in show_more_buttons:
                        try:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(1)
                        except:
                            pass
                except:
                    pass
                
                # Her 5 scroll'da bir mevcut job sayısını göster
                if (i + 1) % 5 == 0:
                    current_links = self.driver.find_elements(By.TAG_NAME, "a")
                    current_count = len([l for l in current_links if '/jobs/view/' in (l.get_attribute('href') or '')])
                    print(f"         📊 Scroll {i+1}/{scroll_count}: {len(job_ids)} benzersiz job ID bulundu, {current_count} link tespit edildi")
            
            # Tüm linkleri bul
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute('href') or ''
                    if '/jobs/view/' in href:
                        import re
                        match = re.search(r'/jobs/view/(\d+)', href)
                        if match:
                            job_id = match.group(1)
                            if job_id not in job_ids:
                                job_ids.add(job_id)
                                jobs.append({
                                    'title': f'İlan #{job_id}',
                                    'company': '',
                                    'location': '',
                                    'posted_date': '',
                                    'applicants': '',
                                    'recruiter_info': '',
                                    'response_insight': '',
                                    'job_description': '',
                                    'work_type': '',
                                    'employment_type': '',
                                    'salary': '',
                                    'link': f'https://www.linkedin.com/jobs/view/{job_id}/'
                                })
                except:
                    continue
            
            # Sayfa kaynağından da job ID'leri ara (daha kapsamlı)
            print("      🔍 Sayfa kaynağından job ID'leri aranıyor...")
            page_source = self.driver.page_source
            import re
            matches = re.findall(r'/jobs/view/(\d+)', page_source)
            print(f"         📊 Sayfa kaynağında {len(matches)} job ID pattern'i bulundu")
            for job_id in matches:
                if job_id not in job_ids:
                    job_ids.add(job_id)
                    jobs.append({
                        'title': f'İlan #{job_id}',
                        'company': '',
                        'location': '',
                        'posted_date': '',
                        'applicants': '',
                        'recruiter_info': '',
                        'response_insight': '',
                        'job_description': '',
                        'work_type': '',
                        'employment_type': '',
                        'salary': '',
                        'link': f'https://www.linkedin.com/jobs/view/{job_id}/'
                    })
            
            # Data attribute'lardan da job ID'leri ara
            try:
                data_elements = self.driver.find_elements(By.XPATH, "//*[@data-job-id or @data-occludable-job-id or @data-job-id-base]")
                for el in data_elements:
                    job_id = el.get_attribute('data-job-id') or el.get_attribute('data-occludable-job-id') or el.get_attribute('data-job-id-base')
                    if job_id and job_id not in job_ids:
                        job_ids.add(job_id)
                        jobs.append({
                        'title': f'İlan #{job_id}',
                        'company': '',
                        'location': '',
                        'posted_date': '',
                        'applicants': '',
                        'recruiter_info': '',
                        'response_insight': '',
                        'job_description': '',
                        'work_type': '',
                        'employment_type': '',
                        'salary': '',
                        'link': f'https://www.linkedin.com/jobs/view/{job_id}/'
                        })
            except:
                pass
            
            print(f"      ✅ Toplam {len(job_ids)} benzersiz job ID bulundu")
            
        except Exception as e:
            print(f"⚠️ Manuel job ID çıkarma hatası: {e}")
        
        return jobs
    
    def get_extractor_js(self):
        """collections_extractor.js kodunu oku"""
        extractor_path = os.path.join(self.base_dir, 'collections_extractor.js')
        try:
            with open(extractor_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ {extractor_path} bulunamadı, basit extractor kullanılıyor")
            return """
                const jobs = [];
                const links = document.querySelectorAll('a[href*="/jobs/view/"]');
                links.forEach(link => {
                    const href = link.href;
                    const jobId = href.match(/\\/jobs\\/view\\/(\\d+)/);
                    if (jobId) {
                        jobs.push({
                        title: link.textContent.trim() || `İlan #${jobId[1]}`,
                        company: '',
                        location: '',
                        posted_date: '',
                        applicants: '',
                        link: href
                        });
                    }
                });
                window.linkedinJobs = jobs;
            """
    
    def save_jobs(self, jobs, filename='jobs.json'):
        """İlanları JSON dosyasına kaydet"""
        output_path = os.path.join(self.base_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(jobs)} ilan kaydedildi: {output_path}")
        return output_path
    
    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()
            print("✅ Browser kapatıldı")

def main():
    print("=" * 80)
    print("LinkedIn Otomatik Ghost Job Analyzer")
    print("=" * 80)
    
    # URL kontrolü
    url = None
    email = None
    password = None
    max_jobs = 30  # Varsayılan ilan sayısı
    
    if len(sys.argv) < 2:
        print("Kullanım: python3 auto_analyzer.py <url> [email] [password] [max_jobs]")
        print("Örnek: python3 auto_analyzer.py \"https://www.linkedin.com/jobs/search/...\" \"email@example.com\" \"password\" 50")
        print("\nParametreler:")
        print("  url        : LinkedIn iş ilanları sayfası URL'i (zorunlu)")
        print("  email      : LinkedIn email adresi (opsiyonel, varsayılan: cekubest@gmail.com)")
        print("  password   : LinkedIn şifresi (opsiyonel, varsayılan: 1987baba)")
        print("  max_jobs   : Taranacak maksimum ilan sayısı (opsiyonel, varsayılan: 30)")
        return 1
    
    url = sys.argv[1]
    email = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None
    
    # max_jobs parametresini al (4. parametre)
    if len(sys.argv) > 4:
        try:
            max_jobs = int(sys.argv[4])
            if max_jobs < 1:
                print("⚠️ max_jobs 1'den küçük olamaz, varsayılan 30 kullanılıyor")
                max_jobs = 30
        except ValueError:
            print(f"⚠️ Geçersiz max_jobs değeri: {sys.argv[4]}, varsayılan 30 kullanılıyor")
            max_jobs = 30
    
    # Varsayılan email/şifre
    if not email:
        email = 'cekubest@gmail.com'
    if not password:
        password = '1987baba'
    
    print(f"📄 URL: {url}")
    print(f"📊 Maksimum ilan sayısı: {max_jobs}")
    
    extractor = LinkedInAutoExtractor(email=email, password=password)
    
    # Email/şifre varsa session bilgilerini yükleme
    if email and password:
        print(f"📧 Email/şifre ile giriş yapılacak: {email}")
        # Session bilgilerini yükleme, direkt driver setup
        if not extractor.setup_driver():
            print("\n❌ Chrome driver başlatılamadı!")
            return 1
    else:
        # Session bilgilerini yükle
        if not extractor.load_session_info():
            return 1
        # Driver'ı kur
        if not extractor.setup_driver():
            return 1
    
    # Önce mevcut Chrome'a bağlanmayı dene (sadece email/şifre yoksa)
    if not (email and password):
        use_existing = False
        if len(sys.argv) > 2 and sys.argv[2] == '--use-existing':
            use_existing = True
        
        # Driver'ı kur
        if not extractor.setup_driver(use_existing_chrome=use_existing):
            if use_existing:
                print("\n💡 Remote debugging modunda Chrome başlatmak için:")
                print("   Mac: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
                print("   Windows: chrome.exe --remote-debugging-port=9222")
                print("\n   Sonra scripti tekrar çalıştırın: python3 auto_analyzer.py --use-existing")
                return 1
            else:
                return 1
    
    try:
        # İlanları çıkar
        print("\n" + "="*80)
        print("🔍 ADIM 2: İş İlanları Çıkarılıyor...")
        print("="*80)
        print(f"📊 Maksimum {max_jobs} ilan taranacak")
        jobs = extractor.extract_jobs(url, max_jobs=max_jobs)
        
        if not jobs:
            print("⚠️ Hiç ilan bulunamadı!")
            return 1
        
        # JSON'a kaydet
        jobs_file = extractor.save_jobs(jobs)
        
        # Analiz yap
        print("\n" + "=" * 80)
        print("📊 Ghost Job Analizi Başlatılıyor...")
        print("=" * 80)
        
        # linkedin_analyzer'ı import et ve çalıştır
        sys.path.insert(0, extractor.base_dir)
        
        # linkedin_analyzer.main() fonksiyonunu çağır
        # main() fonksiyonu sys.argv bekliyor, bu yüzden geçici olarak değiştiriyoruz
        original_argv = sys.argv
        try:
            sys.argv = ['linkedin_analyzer.py', jobs_file]
            linkedin_analyzer.main()
        finally:
            sys.argv = original_argv
        
        print("\n✅ Tüm işlemler tamamlandı!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ İşlem kullanıcı tarafından durduruldu")
        return 1
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        extractor.close()

if __name__ == '__main__':
    sys.exit(main())

