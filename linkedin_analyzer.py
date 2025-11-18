#!/usr/bin/env python3
"""
LinkedIn Ghost Job Analyzer - Browser Console JavaScript Yöntemi
Tüm LinkedIn analiz fonksiyonlarını içeren modül.

KULLANIM:
1. Chrome'da LinkedIn iş ilanları sayfasını açın
2. F12 ile Developer Tools'u açın
3. Console sekmesine gidin
4. linkedin_extractor.js kodunu yapıştırın ve Enter'a basın
5. JSON çıktısını kopyalayın ve jobs.json dosyasına kaydedin
6. python3 linkedin_analyzer.py jobs.json komutunu çalıştırın
"""

import json
import csv
import re
import os
import sys
from datetime import datetime
from typing import List, Dict

# ============================================================================
# GHOST JOB PARAMETRELERİ VE KURALLAR
# ============================================================================

# Ghost Job Tespit Parametreleri - Güncellenmiş Kriterler
GHOST_JOB_PARAMETERS = {
    "posting_duration": {
        "threshold_days": 30,
        "levels": {
            "low_risk": "0-30 days",
            "medium_risk": "31-60 days",
            "high_risk": "61+ days"
        }
    },
    "job_description_quality": {
        "undefined_roles": True,
        "too_broad_scope": True,
        "combined_irrelevant_responsibilities": True,
        "must_have_stack_overload": True
    },
    "reposted_frequency": {
        "repeat_listing_count": None,
        "is_reposted_often": True,
        "repost_interval_days": None
    },
    "communication_delay": {
        "no_feedback_days": 14,
        "slow_interview_process": True,
        "status_updates_missing": True
    },
    "salary_transparency": {
        "salary_provided": False,
        "salary_range_accuracy": "unknown"
    },
    "requirement_anomalies": {
        "senior_experience_for_junior_title": True,
        "unrealistic_years_of_experience": True,
        "mixed_role_expectations": True
    },
    "company_signals": {
        "recent_layoffs": False,
        "hiring_freeze": False,
        "budget_approval_missing": True
    },
    "linkedIn_behavior": {
        "multiple_open_positions_no_headcount_change": True,
        "employees_commenting_no_active_hiring": False,
        "departman_exists": True
    }
}

# Ghost Job Tespit Kuralları ve Puanları (0-10 arası puanlama için referans)
GHOST_JOB_RULES = {
    "yayin_tarihi_ve_suresi": {
        "aciklama": "İlan uzun süredir (örneğin aylardır) yayında ise veya yayın tarihi belirtilmemişse şüpheli olabilir. Eski ilanlar genellikle doldurulmaz.",
        "puan": 2.0,  # 0-10 arası puanlama sisteminde
    },
    "ilan_aciklama_kalitesi": {
        "aciklama": "Açıklama çok genel, belirsiz veya kopyala-yapıştır gibi görünüyorsa (örneğin spesifik görevler, maaş aralığı veya şirket kültürü detayları eksikse) ghost olma olasılığı yüksektir.",
        "puan": 2.5,
    },
    "maas_ve_detay_eksikligi": {
        "aciklama": "Gerçek ilanlarda genellikle maaş aralığı, faydalar veya çalışma koşulları belirtilir; ghostlarda bunlar atlanır.",
        "puan": 2.0,
    },
    "yuksek_basvuru_sayisi_ama_hareketsizlik": {
        "aciklama": "İlan çok başvuru almış gibi görünse de doldurulmuyor.",
        "puan": 1.5,
    },
    "yanit_alamama": {
        "aciklama": "Başvuruya hızlı yanıt gelmiyorsa veya hiç gelmiyorsa, ghost iş olabilir.",
        "puan": 1.0,
    },
    "gereksinim_anomalileri": {
        "aciklama": "Junior pozisyon için senior deneyim bekleniyorsa veya gerçekçi olmayan yıl deneyimi varsa.",
        "puan": 1.0,
    }
}

# ============================================================================
# LINK DÜZELTME FONKSİYONLARI
# ============================================================================

def fix_linkedin_link(link: str) -> str:
    """LinkedIn linkini düzelt"""
    if not link:
        return ""
    
    if link.startswith('http'):
        job_id_match = re.search(r'/jobs/view/(\d+)', link) or \
                      re.search(r'currentJobId=(\d+)', link) or \
                      re.search(r'jobId=(\d+)', link) or \
                      re.search(r'/jobs/collections/.*?currentJobId=(\d+)', link)
        if job_id_match:
            return f"https://www.linkedin.com/jobs/view/{job_id_match.group(1)}/"
        return link
    
    if link.isdigit():
        return f"https://www.linkedin.com/jobs/view/{link}/"
    
    if link.startswith('/'):
        return f"https://www.linkedin.com{link}"
    
    return link

# ============================================================================
# ANALİZ SINIFI
# ============================================================================

class LinkedInGhostJobAnalyzer:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.report_dir = os.path.join(self.base_dir, "report")
        # Report dizinini oluştur
        os.makedirs(self.report_dir, exist_ok=True)
    
    def get_date_suffix(self) -> str:
        """Tarih ve zaman suffix'i oluştur (YYYYMMDD_HHMMSS formatında)"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_date_to_filename(self, filename: str) -> str:
        """Dosya adına tarih ve zaman ekle"""
        name, ext = os.path.splitext(filename)
        date_suffix = self.get_date_suffix()
        return f"{name}_{date_suffix}{ext}"
        
    def parse_job_date(self, date_str: str) -> Dict:
        """İlan tarihini parse et ve analiz et - Güncellenmiş kriterler:
        - >30 gün: Şüpheli (1 puan)
        - 60 gün: Yüksek risk (3 puan)
        - 90 gün: %90 ghost (5 puan)
        - 2-6 ay arası: Ghost ihtimali yüksek (3-5 puan)
        """
        if not date_str or date_str.lower() in ['bilinmiyor', 'tarih bulunamadı', 'unknown', '']:
            return {'months_old': None, 'days_old': None, 'risk': 0}
        
        date_str_lower = date_str.lower()
        
        month_match = re.search(r'(\d+)\s*(month|ay|mo)', date_str_lower)
        if month_match:
            months = int(month_match.group(1))
            days = months * 30
            # Yeni kriterler: 2-6 ay arası ghost ihtimali yüksek
            if months >= 3:  # 90+ gün = %90 ghost
                risk = 5
            elif months >= 2:  # 60+ gün = yüksek risk
                risk = 3
            elif months >= 1:  # 30+ gün = şüpheli
                risk = 1
            else:
                risk = 0
            return {'months_old': months, 'days_old': days, 'risk': risk, 'text': date_str}
        
        week_match = re.search(r'(\d+)\s*(week|hafta|w)', date_str_lower)
        if week_match:
            weeks = int(week_match.group(1))
            days = weeks * 7
            months = days / 30
            # 30 günden fazla ise şüpheli
            if days >= 90:  # 90+ gün = %90 ghost
                risk = 5
            elif days >= 60:  # 60+ gün = yüksek risk
                risk = 3
            elif days >= 30:  # 30+ gün = şüpheli
                risk = 1
            else:
                risk = 0
            return {'months_old': round(months, 1), 'days_old': days, 'risk': risk, 'text': date_str}
        
        day_match = re.search(r'(\d+)\s*(day|gün|d)', date_str_lower)
        if day_match:
            days = int(day_match.group(1))
            months = days / 30
            # Yeni kriterler: 30 gün şüpheli, 60 gün yüksek risk, 90 gün %90 ghost
            if days >= 90:  # 90+ gün = %90 ghost
                risk = 5
            elif days >= 60:  # 60+ gün = yüksek risk
                risk = 3
            elif days >= 30:  # 30+ gün = şüpheli
                risk = 1
            else:
                risk = 0
            return {'months_old': round(months, 1), 'days_old': days, 'risk': risk, 'text': date_str}
        
        year_match = re.search(r'(\d+)\s*(year|yıl|yr)', date_str_lower)
        if year_match:
            years = int(year_match.group(1))
            months = years * 12
            days = months * 30
            return {'months_old': months, 'days_old': days, 'risk': 5, 'text': date_str}
        
        if any(term in date_str_lower for term in ['just now', 'now', 'recently', 'az önce', 'yeni']):
            return {'months_old': 0, 'days_old': 0, 'risk': 0, 'text': date_str}
        
        return {'months_old': None, 'days_old': None, 'risk': 0, 'text': date_str}
    
    def parse_applicant_count(self, applicant_str: str) -> Dict:
        """Başvuru sayısını parse et"""
        if not applicant_str or applicant_str.lower() in ['bilinmiyor', 'unknown', 'n/a', '']:
            return {'count': None, 'risk': 0}
        
        applicant_lower = applicant_str.lower()
        
        # "100+ applicants" formatı
        plus_match = re.search(r'(\d+)\s*\+', applicant_lower)
        if plus_match:
            count = int(plus_match.group(1))
            risk = 5 if count >= 200 else 3 if count >= 100 else 2 if count >= 50 else 0
            return {'count': count, 'risk': risk, 'text': applicant_str}
        
        # Sadece sayı
        num_match = re.search(r'(\d+)', applicant_lower)
        if num_match:
            count = int(num_match.group(1))
            risk = 5 if count >= 200 else 3 if count >= 100 else 2 if count >= 50 else 0
            return {'count': count, 'risk': risk, 'text': applicant_str}
        
        return {'count': None, 'risk': 0, 'text': applicant_str}
    
    def analyze_job_description_quality(self, job_description: str, title: str) -> Dict:
        """Görev tanımı kalitesini analiz et - Yeni kriter:
        - Belirsiz, genel, kopyala-yapıştır gibi görünüyorsa şüpheli
        - Tanımsız veya aşırı geniş görev tanımı
        - Başlık ve görev tanımı tutarsızlığı
        """
        if not job_description or len(job_description.strip()) < 50:
            return {'risk': 2, 'indicators': ['Görev tanımı çok kısa veya eksik']}
        
        desc_lower = job_description.lower()
        title_lower = title.lower()
        risk = 0
        indicators = []
        
        # Belirsiz/genel ifadeler
        vague_phrases = [
            'dinamik ekip', 'dinamik çalışma ortamı', 'her şeyi yapabilen',
            'çok yönlü', 'esnek', 'genel', 'çeşitli görevler', 'farklı projeler',
            'various', 'multiple', 'general', 'flexible', 'versatile',
            'her türlü', 'tüm', 'genel olarak', 'çeşitli', 'farklı'
        ]
        
        vague_count = sum(1 for phrase in vague_phrases if phrase in desc_lower)
        if vague_count >= 3:
            risk += 2
            indicators.append('Görev tanımı çok genel/belirsiz')
        elif vague_count >= 1:
            risk += 1
            indicators.append('Görev tanımında belirsiz ifadeler var')
        
        # Aşırı geniş görev tanımı (teknik + idari + müşteri ilişkileri gibi)
        role_types = {
            'teknik': ['yazılım', 'kod', 'programlama', 'geliştirme', 'teknik', 'software', 'code', 'development'],
            'idari': ['idari', 'yönetim', 'raporlama', 'planlama', 'administrative', 'management'],
            'müşteri': ['müşteri', 'satış', 'pazarlama', 'customer', 'sales', 'marketing'],
            'muhasebe': ['muhasebe', 'finans', 'mali', 'accounting', 'finance', 'financial']
        }
        
        found_types = []
        for role_type, keywords in role_types.items():
            if any(keyword in desc_lower for keyword in keywords):
                found_types.append(role_type)
        
        # 3 veya daha fazla farklı rol tipi varsa şüpheli
        if len(found_types) >= 3:
            risk += 2
            indicators.append(f'Görev tanımı çok geniş (teknik+idari+müşteri ilişkileri gibi: {", ".join(found_types)})')
        
        # Başlık ve görev tanımı tutarsızlığı
        title_keywords = {
            'senior': ['senior', 'kıdemli', 'lead', 'principal', 'architect'],
            'junior': ['junior', 'entry', 'başlangıç', 'yeni mezun', 'stajyer'],
            'manager': ['manager', 'yönetici', 'müdür', 'head', 'director'],
            'specialist': ['specialist', 'uzman', 'analyst', 'analist']
        }
        
        title_level = None
        for level, keywords in title_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                title_level = level
                break
        
        # Görev tanımında zıt seviye beklentisi varsa
        if title_level == 'senior':
            if any(term in desc_lower for term in ['junior', 'entry level', 'yeni mezun', 'başlangıç']):
                risk += 1
                indicators.append('Başlık "senior" ama görev tanımı "junior" seviye')
        elif title_level == 'junior':
            if any(term in desc_lower for term in ['senior', 'kıdemli', '5 yıl', '10 yıl', 'deneyimli']):
                risk += 1
                indicators.append('Başlık "junior" ama görev tanımı "senior" seviye')
        
        # Gereksiz derecede yüksek nitelik bekleme
        if any(term in desc_lower for term in ['5 yıl', '10 yıl', '15 yıl', '5 years', '10 years']):
            if title_level == 'junior' or 'junior' in title_lower or 'entry' in title_lower:
                risk += 2
                indicators.append('Gereksiz derecede yüksek nitelik bekleniyor (junior pozisyon için 5+ yıl)')
        
        # Maaş, ekip bilgisi veya yöneticiler hakkında net bilgi eksikliği
        specific_info_keywords = ['maaş', 'salary', 'ücret', 'ekip', 'team', 'yönetici', 'manager', 'supervisor']
        has_specific_info = any(keyword in desc_lower for keyword in specific_info_keywords)
        
        # "Rekabetçi maaş", "Dinamik ekip" gibi boş cümleler
        empty_phrases = ['rekabetçi maaş', 'competitive salary', 'dinamik ekip', 'dynamic team', 'uygun maaş']
        has_empty_phrases = any(phrase in desc_lower for phrase in empty_phrases)
        
        if has_empty_phrases and not has_specific_info:
            risk += 1
            indicators.append('Maaş/ekip bilgisi belirsiz ("rekabetçi maaş", "dinamik ekip" gibi)')
        
        return {'risk': min(risk, 3), 'indicators': indicators}
    
    def analyze_job(self, job: Dict) -> Dict:
        """Bir iş ilanını analiz et ve ghost job risk skoru hesapla - Güncellenmiş kriterler"""
        title = job.get('title', '').lower()
        company = job.get('company', '').lower()
        location = job.get('location', '').lower()
        posted_date = job.get('posted_date', '')
        applicants = job.get('applicants', '')
        link = job.get('link', '')
        job_description = job.get('job_description', '')
        recruiter_info = job.get('recruiter_info', '').lower()
        response_insight = job.get('response_insight', '').lower()
        salary = job.get('salary', '').lower()
        posting_status = job.get('posting_status', '').lower()
        
        risk_score = 0
        indicators = []
        detailed_analysis = {}
        
        # Tarih analizi - Güncellenmiş kriterler
        date_analysis = self.parse_job_date(posted_date)
        days_old = date_analysis.get('days_old', 0) or 0
        is_old_posting = days_old >= 30  # 30 gün (1 ay) ve üzeri
        
        # 30 günden fazla açıksa ve yeniden yayınlandıysa → Çok şüpheli
        if is_old_posting and posting_status:
            if 'yeniden yayınlandı' in posting_status or 'reposted' in posting_status or 'ilan yenilendi' in posting_status:
                risk_score += 3.0  # Yüksek şüphe puanı (30+ gün + yeniden yayınlandı)
                indicators.append(f'30+ gün açık + yeniden yayınlandı (çok şüpheli)')
        
        if date_analysis['risk'] > 0:
            # 30 günden az açıksa, risk puanını azalt (false positive önlemek için)
            if not is_old_posting:
                # Yeni ilanlar için daha az agresif puanlama
                risk_score += date_analysis['risk'] * 0.5  # Risk puanını yarıya indir
            else:
                # Eski ilanlar için normal puanlama
                risk_score += date_analysis['risk']
            
            if days_old and days_old >= 90:
                indicators.append(f"İlan 90+ gün açık (%90 ghost ihtimali)")
            elif days_old and days_old >= 60:
                indicators.append(f"İlan 60+ gün açık (yüksek risk)")
            elif days_old and days_old >= 30:
                indicators.append(f"İlan 30+ gün açık (şüpheli)")
            else:
                indicators.append(f"Eski ilan ({date_analysis.get('text', posted_date)})")
        detailed_analysis['date_analysis'] = date_analysis
        
        # Başvuru sayısı analizi
        applicant_analysis = self.parse_applicant_count(applicants)
        if applicant_analysis['risk'] > 0:
            # 30 günden az açıksa, başvuru sayısı riskini azalt (yeni ilanlar normal olabilir)
            if not is_old_posting:
                risk_score += applicant_analysis['risk'] * 0.5  # Risk puanını yarıya indir
            else:
                risk_score += applicant_analysis['risk']
            indicators.append(f"Çok fazla başvuru ({applicant_analysis.get('text', applicants)})")
        detailed_analysis['applicant_analysis'] = applicant_analysis
        
        # Yüksek başvuru sayısı ama hareketsizlik - Yeni kriter
        # Sadece 30+ gün açık ilanlar için geçerli (yeni ilanlar için false positive önlemek için)
        if is_old_posting and applicant_analysis.get('count', 0) and applicant_analysis['count'] >= 100:
            if 'henüz yanıt içgörüsü yok' in response_insight or 'no response insight' in response_insight:
                risk_score += 1
                indicators.append('30+ gün açık + yüksek başvuru ama yanıt yok (hareketsizlik)')
        
        # Görev tanımı kalitesi analizi - Yeni kriter
        # 30 günden az açıksa, görev tanımı kalitesi riskini azalt (yeni ilanlar henüz tamamlanmamış olabilir)
        if job_description:
            desc_analysis = self.analyze_job_description_quality(job_description, job.get('title', ''))
            if desc_analysis['risk'] > 0:
                if not is_old_posting:
                    risk_score += desc_analysis['risk'] * 0.5  # Yeni ilanlar için daha az agresif
                else:
                    risk_score += desc_analysis['risk']
                indicators.extend(desc_analysis.get('indicators', []))
                detailed_analysis['description_analysis'] = desc_analysis
        
        # Maaş şeffaflığı analizi - Yeni kriter
        # 30 günden az açıksa, maaş eksikliği daha az şüpheli (yeni ilanlar henüz maaş bilgisi eklenmemiş olabilir)
        if not salary or salary.strip() == '':
            if is_old_posting:
                risk_score += 2  # Eski ilanlarda maaş yoksa şüpheli
                indicators.append('30+ gün açık ama maaş bilgisi yok (şeffaflık eksikliği)')
            else:
                risk_score += 0.5  # Yeni ilanlarda daha az şüpheli
        else:
            # Maaş bilgisi var ama belirsiz mi kontrol et
            vague_salary_phrases = ['rekabetçi', 'competitive', 'uygun', 'negotiable', 'görüşülür', 'belirlenecek']
            if any(phrase in salary for phrase in vague_salary_phrases):
                if is_old_posting:
                    risk_score += 1
                    indicators.append('30+ gün açık + belirsiz maaş bilgisi')
                else:
                    risk_score += 0.5  # Yeni ilanlarda daha az şüpheli
        
        # İletişim gecikmesi analizi - Yeni kriter
        # Sadece 30+ gün açık ilanlar için geçerli (yeni ilanlar için false positive önlemek için)
        if is_old_posting and ('henüz yanıt içgörüsü yok' in response_insight or 'no response insight' in response_insight):
            if days_old and days_old >= 14:
                risk_score += 1
                indicators.append('30+ gün açık + yanıt içgörüsü yok (iletişim gecikmesi)')
        
        # Gereksinim anomalileri analizi - Yeni kriter
        # Her zaman kontrol et (yeni veya eski ilan fark etmez)
        title_lower = title
        if any(term in title_lower for term in ['junior', 'entry', 'başlangıç', 'yeni mezun', 'stajyer']):
            if job_description:
                if any(term in job_description.lower() for term in ['5 yıl', '10 yıl', '15 yıl', '5 years', '10 years', 'senior', 'kıdemli']):
                    risk_score += 2
                    indicators.append('Junior pozisyon ama senior deneyim bekleniyor (gereksinim anomalisi)')
        
        # Şirket adı analizi - daha detaylı
        # Şirket adı analizi her zaman geçerli (yeni veya eski ilan fark etmez)
        suspicious_companies = ['recruiting', 'staffing', 'talent', 'hr', 'human resources', 
                               'headhunter', 'executive search', 'placement', 'consulting']
        company_risk = 0
        for term in suspicious_companies:
            if term in company:
                company_risk += 2
                indicators.append(f"Şüpheli şirket adı (içerir: {term})")
                break
        risk_score += company_risk
        
        # Başlık analizi - daha detaylı
        # Başlık analizi her zaman geçerli (yeni veya eski ilan fark etmez)
        vague_titles = ['various', 'multiple', 'various positions', 'çeşitli', 'birden fazla',
                       'urgent', 'immediate', 'acil', 'hemen', 'entry level', 'junior']
        title_risk = 0
        for term in vague_titles:
            if term in title:
                title_risk += 1
                indicators.append(f"Belirsiz/genel başlık (içerir: {term})")
        risk_score += min(title_risk, 3)  # Maksimum 3 puan
        
        # Lokasyon analizi - daha detaylı
        # 30+ gün açıksa ve genel lokasyon + çok başvuru varsa şüpheli
        if not location or location in ['remote', 'uzaktan', 'anywhere', 'worldwide', 'türkiye', 'turkey']:
            if is_old_posting and applicant_analysis.get('count', 0) and applicant_analysis['count'] > 100:
                risk_score += 1
                indicators.append("30+ gün açık + genel lokasyon + çok başvuru")
            elif not location or location in ['türkiye', 'turkey']:
                # Sadece ülke adı varsa (şehir yoksa) - sadece 30+ gün açıksa şüpheli
                if is_old_posting and applicant_analysis.get('count', 0) and applicant_analysis['count'] > 50:
                    risk_score += 1
                    indicators.append("30+ gün açık + genel lokasyon (sadece ülke)")
        
        # Başlık uzunluğu analizi
        if len(title) < 10:
            risk_score += 1
            indicators.append("Çok kısa başlık")
        elif len(title) > 100:
            risk_score += 1
            indicators.append("Çok uzun başlık")
        
        # Şirket adı analizi - çok kısa veya çok uzun
        if company:
            if len(company) < 3:
                risk_score += 1
                indicators.append("Çok kısa şirket adı")
            elif len(company) > 80:
                risk_score += 1
                indicators.append("Çok uzun şirket adı")
        
        # Başvuru durumu analizi - "aktif olarak inceleniyor" gibi belirsiz ifadeler
        # Sadece 30+ gün açık ilanlar için geçerli
        if is_old_posting and applicants and 'aktif olarak inceleniyor' in applicants.lower():
            if not applicant_analysis.get('count'):  # Sayı yoksa daha şüpheli
                risk_score += 1
                indicators.append("30+ gün açık + belirsiz başvuru durumu (sayı yok)")
        
        # Tarih bilgisi yoksa şüpheli (her zaman)
        if not posted_date or posted_date == '':
            risk_score += 1
            indicators.append("Tarih bilgisi yok")
        
        # Başvuru sayısı bilgisi yoksa şüpheli (özellikle eski ilanlarda)
        if is_old_posting and (not applicants or applicants == ''):
            if date_analysis.get('months_old', 0) and date_analysis['months_old'] > 3:
                risk_score += 1
                indicators.append("3+ ay açık ama başvuru bilgisi yok")
        
        # Link analizi - geçersiz veya eksik link
        if not link or 'linkedin.com/jobs/view' not in link:
            risk_score += 1
            indicators.append("Geçersiz veya eksik link")
        
        # İşe alım uzmanı bilgisi analizi - Yeni kriter
        # Sadece 30+ gün açık ilanlar için geçerli (yeni ilanlar için false positive önlemek için)
        if is_old_posting and ('tanıtılıyor' in recruiter_info or 'promoted' in recruiter_info):
            # İşe alım uzmanı tarafından tanıtılıyorsa, yüksek başvuru ile birlikte şüpheli
            if applicant_analysis.get('count', 0) and applicant_analysis['count'] >= 100:
                risk_score += 1
                indicators.append('30+ gün açık + işe alım uzmanı tanıtımı + yüksek başvuru (şüpheli)')
        
        # İlan durumu analizi - Yeniden yayınlandı, Genel Başvuru vb. (Yeni kriter)
        # 30+ gün açık + yeniden yayınlandı kombinasyonu yukarıda zaten kontrol edildi
        # Burada sadece diğer durumları kontrol et
        if posting_status:
            # Genel başvuru - her zaman şüpheli (ama 30+ gün açıksa daha şüpheli)
            if 'genel başvuru' in posting_status or 'general application' in posting_status or 'sürekli alıyoruz' in posting_status:
                if is_old_posting:
                    risk_score += 2.5  # 30+ gün + genel başvuru = çok şüpheli
                    indicators.append('30+ gün açık + genel başvuru (çok şüpheli)')
                else:
                    risk_score += 1.0  # Yeni ilanlarda daha az şüpheli
                    indicators.append('Genel başvuru (sürekli alım - şüpheli)')
            
            # Tekrarlanan yayın - sadece 30+ gün açıksa şüpheli
            if is_old_posting and ('tekrarlanan yayın' in posting_status or 'repeat' in posting_status):
                risk_score += 1.5
                indicators.append('30+ gün açık + tekrarlanan yayın (şüpheli)')
        
        # Risk skoruna göre ghost job olup olmadığını belirle
        # 30+ gün açık ilanlar için eşik: 3 puan
        # 30 günden az açık ilanlar için eşik: 4 puan (false positive önlemek için)
        if is_old_posting:
            is_ghost = risk_score >= 3  # Eski ilanlar için daha hassas
        else:
            is_ghost = risk_score >= 4  # Yeni ilanlar için daha yüksek eşik
        
        # Detaylı puanlama (0-10 arası) - 10'luk taban puanlama sistemi
        detailed_score = self.calculate_detailed_ghost_score(job, date_analysis, applicant_analysis, 
                                                               job_description, salary, response_insight)
        
        # Ana risk skorunu normalize et (0-10 arası)
        normalized_risk_score = min(risk_score, 10)
        
        # Final skor: İki puanlama sisteminin ortalaması (daha dengeli)
        # Kullanıcı 10'luk taban istediği için, her iki skor da 0-10 arası
        final_score = (normalized_risk_score + detailed_score) / 2
        
        return {
            'risk_score': round(normalized_risk_score, 1),  # 0-10 arası (eski sistem)
            'detailed_score': detailed_score,  # 0-10 arası detaylı puan (yeni sistem)
            'final_score': round(final_score, 1),  # 0-10 arası final puan (ortalaması)
            'is_ghost_job': is_ghost,
            'indicators': indicators,
            'date_analysis': date_analysis,
            'applicant_analysis': applicant_analysis,
            'detailed_analysis': detailed_analysis,
            'ghost_parameters': self.extract_ghost_parameters(job, date_analysis, applicant_analysis, 
                                                             job_description, salary, response_insight),
            'is_old_posting': is_old_posting,  # 30+ gün açık mı?
            'days_old': days_old  # Kaç gün açık
        }
    
    def calculate_detailed_ghost_score(self, job: Dict, date_analysis: Dict, applicant_analysis: Dict,
                                      job_description: str, salary: str, response_insight: str) -> float:
        """Detaylı ghost job puanı hesapla (0-10 arası) - 10'luk taban puanlama sistemi
        
        Puanlama Kriterleri (toplam 10 puan):
        - Yayın tarihi ve süresi: 0-2 puan
        - İlan açıklama kalitesi: 0-2.5 puan
        - Maaş şeffaflığı: 0-2 puan
        - Yüksek başvuru ama hareketsizlik: 0-1.5 puan
        - Yanıt alamama: 0-1 puan
        - Gereksinim anomalileri: 0-1 puan
        """
        score = 0.0
        
        # 1. Yayın tarihi ve süresi (0-2 puan)
        days_old = date_analysis.get('days_old', 0) or 0
        is_old_posting = days_old >= 30
        
        if days_old and days_old > 30:
            if days_old >= 90:  # 90+ gün = %90 ghost
                score += 2.0  # Maksimum puan
            elif days_old >= 60:  # 60+ gün = yüksek risk
                score += 1.5
            else:  # 30-60 gün arası
                score += 1.0
        elif not job.get('posted_date'):
            score += 1.5  # Tarih bilgisi yok
        
        # 2. İlan açıklama kalitesi (0-2.5 puan)
        desc_quality_score = 0.0
        if job_description:
            desc_len = len(job_description.strip())
            if desc_len < 200:
                desc_quality_score = 2.5  # Çok kısa açıklama
            elif desc_len < 500:
                desc_quality_score = 1.5  # Kısa açıklama
            else:
                # Belirsiz ifadeler kontrolü (sadece uzun açıklamalarda)
                vague_count = sum(1 for phrase in ['genel', 'çeşitli', 'farklı', 'various', 'multiple', 
                                                 'dinamik ekip', 'her şeyi yapabilen'] 
                                if phrase in job_description.lower())
                if vague_count >= 3:
                    desc_quality_score = 2.0  # Çok belirsiz
                elif vague_count >= 1:
                    desc_quality_score = 1.0  # Belirsiz ifadeler var
        else:
            desc_quality_score = 2.5  # Açıklama yok
        
        score += desc_quality_score
        
        # 3. Maaş şeffaflığı (0-2 puan)
        # 30+ gün açıksa daha şüpheli, yeni ilanlarda daha az şüpheli
        if not salary or salary.strip() == '':
            if is_old_posting:
                score += 2.0  # 30+ gün açık ama maaş bilgisi yok
            else:
                score += 0.5  # Yeni ilanlarda daha az şüpheli
        elif any(phrase in salary.lower() for phrase in ['rekabetçi', 'competitive', 'görüşülür', 'negotiable', 'belirlenecek']):
            if is_old_posting:
                score += 1.0  # 30+ gün açık + belirsiz maaş
            else:
                score += 0.5  # Yeni ilanlarda daha az şüpheli
        
        # 4. Yüksek başvuru sayısı ama hareketsizlik (0-1.5 puan)
        # Sadece 30+ gün açık ilanlar için geçerli
        if is_old_posting:
            applicant_count = applicant_analysis.get('count', 0) or 0
            if applicant_count and applicant_count >= 100:
                if 'henüz yanıt içgörüsü yok' in response_insight.lower() or 'no response insight' in response_insight.lower():
                    score += 1.5  # 30+ gün + yüksek başvuru + yanıt yok
                else:
                    score += 0.5  # 30+ gün + yüksek başvuru var ama yanıt var
        
        # 5. Yanıt alamama / İletişim gecikmesi (0-1 puan)
        # Sadece 30+ gün açık ilanlar için geçerli
        if is_old_posting and ('henüz yanıt içgörüsü yok' in response_insight.lower() or 'no response insight' in response_insight.lower()):
            if days_old and days_old >= 14:
                score += 1.0  # 30+ gün açık + yanıt yok
        
        # 6. Gereksinim anomalileri (0-1 puan)
        title_lower = job.get('title', '').lower()
        if any(term in title_lower for term in ['junior', 'entry', 'başlangıç', 'yeni mezun', 'stajyer']):
            if job_description:
                if any(term in job_description.lower() for term in ['5 yıl', '10 yıl', '15 yıl', '5 years', '10 years', 'senior', 'kıdemli', 'deneyimli']):
                    score += 1.0  # Junior pozisyon ama senior deneyim bekleniyor
        
        # 7. İlan durumu - Yeniden yayınlandı, Genel Başvuru (0-2 puan)
        posting_status_lower = job.get('posting_status', '').lower()
        if posting_status_lower:
            # 30+ gün açık + yeniden yayınlandı kombinasyonu çok şüpheli
            if is_old_posting and ('yeniden yayınlandı' in posting_status_lower or 'reposted' in posting_status_lower or 'ilan yenilendi' in posting_status_lower):
                score += 2.0  # 30+ gün + yeniden yayınlandı = çok şüpheli
            
            # Genel başvuru - 30+ gün açıksa daha şüpheli
            if 'genel başvuru' in posting_status_lower or 'general application' in posting_status_lower or 'sürekli alıyoruz' in posting_status_lower:
                if is_old_posting:
                    score += 1.5  # 30+ gün + genel başvuru
                else:
                    score += 0.5  # Yeni ilanlarda daha az şüpheli
            
            # Tekrarlanan yayın - sadece 30+ gün açıksa şüpheli
            if is_old_posting and 'tekrarlanan yayın' in posting_status_lower:
                score += 1.0
        
        # Maksimum 10 puan
        return round(min(score, 10.0), 1)
    
    def extract_ghost_parameters(self, job: Dict, date_analysis: Dict, applicant_analysis: Dict,
                                job_description: str, salary: str, response_insight: str) -> Dict:
        """Ghost job parametrelerini çıkar - JSON formatında"""
        days_old = date_analysis.get('days_old', 0)
        
        params = {
            "posting_duration": {
                "days_old": days_old if days_old else 0,
                "level": "low_risk" if (days_old and days_old <= 30) else ("medium_risk" if (days_old and days_old <= 60) else "high_risk") if days_old else "unknown",
                "threshold_exceeded": days_old and days_old > GHOST_JOB_PARAMETERS["posting_duration"]["threshold_days"]
            },
            "job_description_quality": {
                "has_description": bool(job_description and len(job_description.strip()) > 50),
                "description_length": len(job_description.strip()) if job_description else 0,
                "is_too_short": job_description and len(job_description.strip()) < 200,
                "has_vague_phrases": bool(job_description and any(phrase in job_description.lower() 
                    for phrase in ['genel', 'çeşitli', 'various', 'multiple', 'dinamik ekip'])),
                "too_broad_scope": False,  # analyze_job_description_quality'den alınabilir
                "combined_irrelevant_responsibilities": False  # analyze_job_description_quality'den alınabilir
            },
            "communication_delay": {
                "no_feedback": 'henüz yanıt içgörüsü yok' in response_insight.lower() or 'no response insight' in response_insight.lower(),
                "days_without_feedback": days_old if (days_old and 'henüz yanıt içgörüsü yok' in response_insight.lower()) else 0,
                "threshold_exceeded": days_old and days_old >= GHOST_JOB_PARAMETERS["communication_delay"]["no_feedback_days"]
            },
            "salary_transparency": {
                "salary_provided": bool(salary and salary.strip()),
                "salary_range_accuracy": "specific" if salary and any(char.isdigit() for char in salary) else "vague" if salary else "unknown"
            },
            "requirement_anomalies": {
                "senior_experience_for_junior_title": False,  # analyze_job_description_quality'den alınabilir
                "unrealistic_years_of_experience": False,  # analyze_job_description_quality'den alınabilir
                "mixed_role_expectations": False  # analyze_job_description_quality'den alınabilir
            },
            "high_applicants_no_movement": {
                "applicant_count": applicant_analysis.get('count') if applicant_analysis.get('count') else 0,
                "has_high_applicants": applicant_analysis.get('count') and applicant_analysis.get('count') >= 100,
                "has_response_insight": 'henüz yanıt içgörüsü yok' not in response_insight.lower(),
                "is_suspicious": applicant_analysis.get('count') and applicant_analysis.get('count') >= 100 and 'henüz yanıt içgörüsü yok' in response_insight.lower()
            }
        }
        
        # Görev tanımı analizi varsa ekle
        if job_description:
            desc_analysis = self.analyze_job_description_quality(job_description, job.get('title', ''))
            if 'too_broad_scope' in str(desc_analysis.get('indicators', [])):
                params["job_description_quality"]["too_broad_scope"] = True
            if 'combined' in str(desc_analysis.get('indicators', [])):
                params["job_description_quality"]["combined_irrelevant_responsibilities"] = True
            if 'senior' in str(desc_analysis.get('indicators', [])) or 'junior' in str(desc_analysis.get('indicators', [])):
                params["requirement_anomalies"]["senior_experience_for_junior_title"] = True
                params["requirement_anomalies"]["unrealistic_years_of_experience"] = True
            if 'geniş' in str(desc_analysis.get('indicators', [])):
                params["requirement_anomalies"]["mixed_role_expectations"] = True
        
        return params
    
    def save_results(self, jobs: List[Dict], filename: str) -> str:
        """Analiz sonuçlarını JSON dosyasına kaydet"""
        output_file = os.path.join(self.report_dir, self.add_date_to_filename(filename))
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(jobs)} ilan kaydedildi: {output_file}")
        return output_file
    
    def format_results(self, jobs: List[Dict]) -> str:
        """Analiz sonuçlarını formatla"""
        if not jobs:
            return "✅ Şüpheli ilan bulunamadı."
        
        output = []
        output.append("=" * 80)
        output.append("ŞÜPHELİ İLANLAR (Ghost Job Potansiyeli)")
        output.append("=" * 80)
        output.append("")
        
        for idx, job in enumerate(jobs, 1):
            analysis = job.get('analysis', {})
            risk_score = analysis.get('risk_score', 0)
            indicators = analysis.get('indicators', [])
            
            output.append(f"{idx}. {job.get('title', 'Bilinmeyen')}")
            output.append(f"   Şirket: {job.get('company', 'Bilinmeyen')}")
            output.append(f"   Lokasyon: {job.get('location', 'Bilinmeyen')}")
            output.append(f"   Risk Skoru: {risk_score}/10")
            if indicators:
                output.append(f"   İşaretler: {', '.join(indicators)}")
            output.append(f"   Link: {fix_linkedin_link(job.get('link', ''))}")
            output.append("")
        
        return "\n".join(output)

# ============================================================================
# ANALİZ FONKSİYONLARI
# ============================================================================

def analyze_jobs(jobs: List[Dict]) -> tuple:
    """Tüm iş ilanlarını analiz et"""
    analyzer = LinkedInGhostJobAnalyzer()
    
    all_analyzed = []
    ghost_jobs = []
    
    for job in jobs:
        # Link'i düzelt
        if 'link' in job:
            job['link'] = fix_linkedin_link(job['link'])
        
        # Analiz yap
        analysis = analyzer.analyze_job(job)
        job['analysis'] = analysis
        
        all_analyzed.append(job)
        
        # Ghost job olarak işaretle (eşik değeri 3'e düşürüldü)
        if analysis['is_ghost_job'] or analysis['risk_score'] >= 3:
            ghost_jobs.append(job)
    
    return ghost_jobs, all_analyzed

# ============================================================================
# CSV DÖNÜŞTÜRME FONKSİYONLARI
# ============================================================================

def json_to_csv(json_file: str, csv_filename: str) -> bool:
    """JSON dosyasını CSV'ye dönüştür"""
    try:
        analyzer = LinkedInGhostJobAnalyzer()
        output_file = os.path.join(analyzer.report_dir, analyzer.add_date_to_filename(csv_filename))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        if not jobs:
            print(f"⚠️ {json_file} dosyası boş")
            return False
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Şirket', 'Başlık', 'Lokasyon', 'Yayın Tarihi', 'Yayın Süresi', 
                'Başvuru Sayısı', 'Başvuru Durumu', 'Risk Skoru', 'Şüpheli İşaretler', 'İlan Linki'
            ])
            writer.writeheader()
            
            for job in jobs:
                analysis = job.get('analysis', {})
                indicators = analysis.get('indicators', [])
                indicators_str = '; '.join(indicators) if indicators else 'Yok'
                link = fix_linkedin_link(job.get('link', ''))
                
                # Tarih analizi
                date_analysis = analysis.get('date_analysis', {})
                posted_date = job.get('posted_date', '')
                date_text = date_analysis.get('text', posted_date) if date_analysis else posted_date
                months_old = date_analysis.get('months_old', None) if date_analysis else None
                
                # Süre bilgisi
                duration = ''
                if months_old is not None:
                    if months_old >= 12:
                        duration = f"{int(months_old // 12)} yıl {int(months_old % 12)} ay"
                    elif months_old >= 1:
                        duration = f"{int(months_old)} ay"
                    else:
                        days = int(months_old * 30)
                        if days >= 7:
                            duration = f"{int(days // 7)} hafta"
                        else:
                            duration = f"{days} gün"
                elif posted_date:
                    duration = posted_date
                else:
                    duration = 'Bilinmiyor'
                
                # Başvuru analizi
                applicant_analysis = analysis.get('applicant_analysis', {})
                applicants = job.get('applicants', '')
                applicant_count = applicant_analysis.get('count', None) if applicant_analysis else None
                applicant_text = applicant_analysis.get('text', applicants) if applicant_analysis else applicants
                
                row = {
                    'Şirket': job.get('company', ''),
                    'Başlık': job.get('title', ''),
                    'Lokasyon': job.get('location', ''),
                    'Yayın Tarihi': date_text,
                    'Yayın Süresi': duration,
                    'Başvuru Sayısı': applicant_count if applicant_count else applicant_text,
                    'Başvuru Durumu': applicant_text if applicant_text else 'Bilinmiyor',
                    'Risk Skoru': analysis.get('final_score', analysis.get('risk_score', 0)),  # 0-10 arası
                    'Şüpheli İşaretler': indicators_str,
                    'İlan Linki': link
                }
                writer.writerow(row)
        
        print(f"✅ {len(jobs)} ilan CSV'ye dönüştürüldü: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def create_detailed_csv(json_file: str, csv_filename: str) -> bool:
    """Detaylı CSV raporu oluştur"""
    try:
        analyzer = LinkedInGhostJobAnalyzer()
        output_file = os.path.join(analyzer.report_dir, analyzer.add_date_to_filename(csv_filename))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        if not jobs:
            return False
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Şirket', 'Başlık', 'Lokasyon', 'Yayın Tarihi', 'Yayın Süresi',
                'Başvuru Sayısı', 'Başvuru Durumu', 'Risk Skoru', 'Ghost Job?', 
                'Tarih Analizi', 'Başvuru Analizi', 'Şüpheli İşaretler', 'İlan Linki'
            ])
            writer.writeheader()
            
            for job in jobs:
                analysis = job.get('analysis', {})
                date_analysis = analysis.get('date_analysis', {})
                applicant_analysis = analysis.get('applicant_analysis', {})
                indicators = analysis.get('indicators', [])
                indicators_str = '; '.join(indicators) if indicators else 'Yok'
                link = fix_linkedin_link(job.get('link', ''))
                
                # Tarih analizi
                posted_date = job.get('posted_date', '')
                date_text = date_analysis.get('text', posted_date) if date_analysis else posted_date
                months_old = date_analysis.get('months_old', None) if date_analysis else None
                
                # Süre bilgisi
                duration = ''
                if months_old is not None:
                    if months_old >= 12:
                        duration = f"{int(months_old // 12)} yıl {int(months_old % 12)} ay"
                    elif months_old >= 1:
                        duration = f"{int(months_old)} ay"
                    else:
                        days = int(months_old * 30)
                        if days >= 7:
                            duration = f"{int(days // 7)} hafta"
                        else:
                            duration = f"{days} gün"
                elif posted_date:
                    duration = posted_date
                else:
                    duration = 'Bilinmiyor'
                
                # Başvuru analizi
                applicants = job.get('applicants', '')
                applicant_count = applicant_analysis.get('count', None) if applicant_analysis else None
                applicant_text = applicant_analysis.get('text', applicants) if applicant_analysis else applicants
                
                row = {
                    'Şirket': job.get('company', ''),
                    'Başlık': job.get('title', ''),
                    'Lokasyon': job.get('location', ''),
                    'Yayın Tarihi': date_text,
                    'Yayın Süresi': duration,
                    'Başvuru Sayısı': applicant_count if applicant_count else applicant_text,
                    'Başvuru Durumu': applicant_text if applicant_text else 'Bilinmiyor',
                    'Risk Skoru': analysis.get('final_score', analysis.get('risk_score', 0)),  # 0-10 arası
                    'Ghost Job?': 'Evet' if analysis.get('is_ghost_job', False) else 'Hayır',
                    'Tarih Analizi': date_analysis.get('text', ''),
                    'Başvuru Analizi': applicant_analysis.get('text', ''),
                    'Şüpheli İşaretler': indicators_str,
                    'İlan Linki': link
                }
                writer.writerow(row)
        
        print(f"✅ Detaylı CSV oluşturuldu: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

def create_sorted_csv(json_file: str, csv_filename: str) -> bool:
    """Risk skoruna göre sıralı CSV oluştur"""
    try:
        analyzer = LinkedInGhostJobAnalyzer()
        output_file = os.path.join(analyzer.report_dir, analyzer.add_date_to_filename(csv_filename))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        if not jobs:
            return False
        
        # Risk skoruna göre sırala (yüksekten düşüğe)
        sorted_jobs = sorted(jobs, key=lambda x: x.get('analysis', {}).get('risk_score', 0), reverse=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Şirket', 'Başlık', 'Lokasyon', 'Yayın Tarihi', 'Yayın Süresi',
                'Başvuru Sayısı', 'Başvuru Durumu', 'Risk Skoru', 'Şüpheli İşaretler', 'İlan Linki'
            ])
            writer.writeheader()
            
            for job in sorted_jobs:
                analysis = job.get('analysis', {})
                indicators = analysis.get('indicators', [])
                indicators_str = '; '.join(indicators) if indicators else 'Yok'
                link = fix_linkedin_link(job.get('link', ''))
                
                # Tarih analizi
                date_analysis = analysis.get('date_analysis', {})
                posted_date = job.get('posted_date', '')
                date_text = date_analysis.get('text', posted_date) if date_analysis else posted_date
                months_old = date_analysis.get('months_old', None) if date_analysis else None
                
                # Süre bilgisi
                duration = ''
                if months_old is not None:
                    if months_old >= 12:
                        duration = f"{int(months_old // 12)} yıl {int(months_old % 12)} ay"
                    elif months_old >= 1:
                        duration = f"{int(months_old)} ay"
                    else:
                        days = int(months_old * 30)
                        if days >= 7:
                            duration = f"{int(days // 7)} hafta"
                        else:
                            duration = f"{days} gün"
                elif posted_date:
                    duration = posted_date
                else:
                    duration = 'Bilinmiyor'
                
                # Başvuru analizi
                applicant_analysis = analysis.get('applicant_analysis', {})
                applicants = job.get('applicants', '')
                applicant_count = applicant_analysis.get('count', None) if applicant_analysis else None
                applicant_text = applicant_analysis.get('text', applicants) if applicant_analysis else applicants
                
                row = {
                    'Şirket': job.get('company', ''),
                    'Başlık': job.get('title', ''),
                    'Lokasyon': job.get('location', ''),
                    'Yayın Tarihi': date_text,
                    'Yayın Süresi': duration,
                    'Başvuru Sayısı': applicant_count if applicant_count else applicant_text,
                    'Başvuru Durumu': applicant_text if applicant_text else 'Bilinmiyor',
                    'Risk Skoru': analysis.get('final_score', analysis.get('risk_score', 0)),  # 0-10 arası
                    'Şüpheli İşaretler': indicators_str,
                    'İlan Linki': link
                }
                writer.writerow(row)
        
        print(f"✅ {len(sorted_jobs)} ilan CSV'ye dönüştürüldü: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

# ============================================================================
# TÜRKİYE IT FİLTRELEME
# ============================================================================

class TurkeyITJobFilter:
    def __init__(self):
        self.turkey_keywords = [
            'turkey', 'türkiye', 'istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 
            'adana', 'gaziantep', 'konya', 'kayseri', 'mersin', 'eskisehir', 
            'remote turkey', 'türkiye remote', 'istanbul remote', 'ankara remote'
        ]
        
        self.it_keywords = [
            'it', 'software', 'yazılım', 'developer', 'geliştirici', 'engineer', 'mühendis',
            'devops', 'cloud', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'k8s',
            'python', 'java', 'javascript', 'react', 'angular', 'node.js',
            'system administrator', 'database', 'dba', 'security', 'cybersecurity',
            'data engineer', 'data scientist', 'machine learning', 'ai'
        ]
    
    def is_turkey_location(self, location: str) -> bool:
        """Lokasyonun Türkiye'de olup olmadığını kontrol et"""
        if not location:
            return False
        location_lower = location.lower()
        return any(keyword in location_lower for keyword in self.turkey_keywords) or \
               bool(re.search(r'\btr\b|\btr-\d+\b', location_lower))
    
    def is_it_related(self, title: str, company: str = None) -> bool:
        """İş başlığının IT/yazılım/DevOps/cloud ile ilgili olup olmadığını kontrol et"""
        if not title:
            return False
        combined = f"{title.lower()} {(company or '').lower()}"
        return any(keyword in combined for keyword in self.it_keywords)
    
    def filter_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """İş ilanlarını filtrele"""
        filtered = []
        for job in jobs:
            if self.is_turkey_location(job.get('location', '')) and \
               self.is_it_related(job.get('title', ''), job.get('company')):
                job['filter_reason'] = f"Türkiye ({job.get('location')}) + IT/Yazılım/DevOps/Cloud"
                filtered.append(job)
        return filtered

# ============================================================================
# ANA SCRIPT
# ============================================================================

def main():
    """Ana script - JSON dosyasından analiz yapar"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 80)
    print("LinkedIn Ghost Job Analyzer")
    print("=" * 80)
    print()
    
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        
        if not os.path.exists(input_file):
            print(f"❌ Dosya bulunamadı: {input_file}")
            print("\n💡 Önce linkedin_extractor.js kodunu browser console'da çalıştırın")
            print("   ve JSON çıktısını jobs.json dosyasına kaydedin")
            return
        
        # JSON dosyasını oku
        print(f"📄 JSON dosyası okunuyor: {input_file}")
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                jobs_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON dosyası geçersiz: {e}")
            print("\n💡 JSON dosyasının doğru formatta olduğundan emin olun")
            return
        except Exception as e:
            print(f"❌ Dosya okunamadı: {e}")
            return
        
        if not jobs_data:
            print("❌ JSON dosyası boş!")
            return
        
        print(f"✅ {len(jobs_data)} iş ilanı yüklendi.\n")
        print("Analiz ediliyor...\n")
        
        # Analiz et
        ghost_jobs, all_jobs = analyze_jobs(jobs_data)
        analyzer = LinkedInGhostJobAnalyzer()
        
        # Sonuçları kaydet
        if ghost_jobs:
            print(analyzer.format_results(ghost_jobs))
            ghost_json = analyzer.save_results(ghost_jobs, "ghost_jobs_report.json")
        else:
            print("✅ Şüpheli ilan bulunamadı.")
        
        all_json = analyzer.save_results(all_jobs, "all_jobs_analysis.json")
        
        # Türkiye IT filtreleme
        print("\n🇹🇷 Türkiye IT filtreleme yapılıyor...")
        filter_tool = TurkeyITJobFilter()
        filtered = filter_tool.filter_jobs(all_jobs)
        
        if filtered:
            for job in filtered:
                if 'analysis' not in job:
                    job['analysis'] = analyzer.analyze_job(job)
        
        # Tüm ilanları kategorize et ve tek bir CSV'de topla
        print("\n📊 Master CSV raporu oluşturuluyor...")
        
        # Her ilana kategori ekle
        for job in all_jobs:
            categories = []
            if job.get('analysis', {}).get('is_ghost_job', False) or job.get('analysis', {}).get('risk_score', 0) >= 3:
                categories.append('Ghost Job')
            
            is_turkey_it = False
            if filtered:
                for f_job in filtered:
                    if f_job.get('link') == job.get('link'):
                        is_turkey_it = True
                        categories.append('Türkiye IT')
                        break
            
            job['category'] = ', '.join(categories) if categories else 'Normal'
        
        # Risk skoruna göre sırala (yüksekten düşüğe)
        sorted_jobs = sorted(all_jobs, key=lambda x: x.get('analysis', {}).get('risk_score', 0), reverse=True)
        
        # Master CSV oluştur
        master_csv_file = os.path.join(analyzer.report_dir, analyzer.add_date_to_filename("linkedin_jobs_master_report.csv"))
        
        with open(master_csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Kategori', 'Risk Skoru', 'Ghost Job?', 'Şirket', 'Başlık', 'Lokasyon', 
                'Yayın Tarihi', 'Yayın Süresi', 'Başvuru Sayısı', 'Başvuru Durumu',
                'İşe Alım Uzmanı', 'Yanıt İçgörüsü', 'Çalışma Şekli', 'İş Tipi', 'Maaş',
                'İlan Durumu', 'Tarih Analizi', 'Başvuru Analizi', 'Şüpheli İşaretler', 'İlan Linki'
            ])
            writer.writeheader()
            
            for job in sorted_jobs:
                analysis = job.get('analysis', {})
                date_analysis = analysis.get('date_analysis', {})
                applicant_analysis = analysis.get('applicant_analysis', {})
                indicators = analysis.get('indicators', [])
                indicators_str = '; '.join(indicators) if indicators else 'Yok'
                link = fix_linkedin_link(job.get('link', ''))
                
                # Tarih analizi
                posted_date = job.get('posted_date', '')
                date_text = date_analysis.get('text', posted_date) if date_analysis else posted_date
                months_old = date_analysis.get('months_old', None) if date_analysis else None
                
                # Süre bilgisi
                duration = ''
                if months_old is not None:
                    if months_old >= 12:
                        duration = f"{int(months_old // 12)} yıl {int(months_old % 12)} ay"
                    elif months_old >= 1:
                        duration = f"{int(months_old)} ay"
                    else:
                        days = int(months_old * 30)
                        if days >= 7:
                            duration = f"{int(days // 7)} hafta"
                        else:
                            duration = f"{days} gün"
                elif posted_date:
                    duration = posted_date
                else:
                    duration = 'Bilinmiyor'
                
                # Başvuru analizi
                applicants = job.get('applicants', '')
                applicant_count = applicant_analysis.get('count', None) if applicant_analysis else None
                applicant_text = applicant_analysis.get('text', applicants) if applicant_analysis else applicants
                
                row = {
                    'Kategori': job.get('category', 'Normal'),
                    'Risk Skoru': analysis.get('final_score', analysis.get('risk_score', 0)),  # 0-10 arası
                    'Ghost Job?': 'Evet' if analysis.get('is_ghost_job', False) else 'Hayır',
                    'Şirket': job.get('company', ''),
                    'Başlık': job.get('title', ''),
                    'Lokasyon': job.get('location', ''),
                    'Yayın Tarihi': date_text,
                    'Yayın Süresi': duration,
                    'Başvuru Sayısı': applicant_count if applicant_count else applicant_text,
                    'Başvuru Durumu': applicant_text if applicant_text else 'Bilinmiyor',
                    'İşe Alım Uzmanı': job.get('recruiter_info', ''),
                    'Yanıt İçgörüsü': job.get('response_insight', ''),
                    'Çalışma Şekli': job.get('work_type', ''),
                    'İş Tipi': job.get('employment_type', ''),
                    'Maaş': job.get('salary', ''),
                    'İlan Durumu': job.get('posting_status', ''),  # Yeniden yayınlandı, Genel Başvuru vb.
                    'Tarih Analizi': date_analysis.get('text', ''),
                    'Başvuru Analizi': applicant_analysis.get('text', ''),
                    'Şüpheli İşaretler': indicators_str,
                    'İlan Linki': link
                }
                writer.writerow(row)
        
        print(f"✅ {len(sorted_jobs)} ilan tek bir CSV dosyasında toplandı: {os.path.basename(master_csv_file)}")
        
        # İstatistikler
        ghost_count = len([j for j in all_jobs if j.get('analysis', {}).get('is_ghost_job', False) or j.get('analysis', {}).get('risk_score', 0) >= 3])
        turkey_it_count = len(filtered) if filtered else 0
        
        print(f"\n📊 Özet:")
        print(f"   - Toplam İlan: {len(all_jobs)}")
        print(f"   - Ghost Job Potansiyeli: {ghost_count}")
        print(f"   - Türkiye IT: {turkey_it_count}")
        
        print("\n✅ Analiz tamamlandı!")
        print(f"\n📁 Master rapor: '{master_csv_file}'")
    else:
        print("Kullanım:")
        print("  python3 linkedin_analyzer.py <json_dosyası>")
        print("\nÖrnek:")
        print("  python3 linkedin_analyzer.py jobs.json")
        print("\n💡 JSON dosyası oluşturmak için:")
        print("   1. Chrome'da LinkedIn iş ilanları sayfasını açın")
        print("   2. F12 ile Developer Tools'u açın")
        print("   3. Console sekmesine gidin")
        print("   4. linkedin_extractor.js kodunu yapıştırın ve Enter'a basın")
        print("   5. JSON çıktısını kopyalayın ve jobs.json dosyasına kaydedin")

if __name__ == "__main__":
    main()
