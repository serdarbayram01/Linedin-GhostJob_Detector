/**
 * LinkedIn Collections/Recommended Sayfası İçin Özel Extractor
 * 
 * Bu kod LinkedIn'in "collections/recommended" sayfasından iş ilanlarını çıkarır
 * Sayfa dinamik yüklendiği için sayfayı kaydırır ve tüm ilanları toplar
 */

(async function() {
console.log('🚀 LinkedIn Collections Extractor başlatılıyor...');
console.log('📄 Sayfa URL:', window.location.href);

const jobs = [];
const jobIds = new Set();
let lastScrollHeight = 0;
const maxScrollAttempts = 40; // 40 scroll yeterli (30 ilan için)

// URL'den mevcut job ID'yi al
const urlParams = new URLSearchParams(window.location.search);
const currentJobId = urlParams.get('currentJobId');
if (currentJobId) {
    jobIds.add(currentJobId);
    console.log(`✅ URL'den job ID bulundu: ${currentJobId}`);
}

// Sayfayı kaydırarak tüm ilanları yükle
console.log('\n📜 Sayfa kaydırılıyor (TÜM SAYFALARDAKİ ilanları yüklemek için)...');
console.log('⚠️ Bu işlem birkaç dakika sürebilir. Lütfen bekleyin...\n');

let consecutiveNoNewJobs = 0;
const maxConsecutiveNoNewJobs = 5; // 5 kez üst üste yeni ilan bulunamazsa dur (daha hızlı)

// "Daha fazla göster" butonlarını tıkla
const clickShowMoreButtons = () => {
const showMoreSelectors = [
    'button[aria-label*="Daha fazla"]',
    'button[aria-label*="Show more"]',
    'button[aria-label*="daha fazla"]',
    'button:contains("Daha fazla")',
    'button:contains("Show more")',
    '.jobs-search-results-list__pagination button',
    'button[data-test-pagination-page-btn]'
];

for (const selector of showMoreSelectors) {
    try {
        const buttons = document.querySelectorAll(selector);
        buttons.forEach(btn => {
            if (btn && btn.offsetParent !== null) { // Görünür mü kontrol et
                btn.click();
                console.log('   ✅ "Daha fazla" butonuna tıklandı');
            }
        });
    } catch(e) {}
}
};

for (let i = 0; i < maxScrollAttempts; i++) {
// Mevcut scroll yüksekliğini kaydet
const currentScrollHeight = document.body.scrollHeight;
const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;

// Sayfayı kaydır - daha agresif
window.scrollTo({
    top: currentScrollHeight,
    behavior: 'smooth'
});

// "Daha fazla göster" butonlarını tıkla
clickShowMoreButtons();

// 0.5 saniye bekle (daha hızlı)
await new Promise(resolve => setTimeout(resolve, 500));

// Tekrar en alta kaydır
window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
});

// Tekrar "Daha fazla" butonlarını kontrol et
clickShowMoreButtons();

// Yeni job ID'leri bul
const foundBefore = jobIds.size;

// Tüm linkleri tara - daha agresif
const allLinks = document.querySelectorAll('a[href]');
allLinks.forEach(link => {
    const href = link.href || link.getAttribute('href') || '';
    
    // /jobs/view/ içeren linklerden job ID çıkar
    const viewMatch = href.match(/\/jobs\/view\/(\d+)/);
    if (viewMatch) {
        jobIds.add(viewMatch[1]);
    }
    
    // /jobs/search/ içeren linklerden currentJobId çıkar
    const searchMatch = href.match(/\/jobs\/search\/.*currentJobId=(\d+)/);
    if (searchMatch) {
        jobIds.add(searchMatch[1]);
    }
    
    // currentJobId veya jobId parametrelerinden job ID çıkar
    const paramMatch = href.match(/currentJobId=(\d+)/) || 
                      href.match(/jobId=(\d+)/) ||
                      href.match(/[\?&]id=(\d+)/);
    if (paramMatch) {
        jobIds.add(paramMatch[1]);
    }
});

// Tüm elementlerin innerHTML'inde job ID ara
const allElements = document.querySelectorAll('*');
allElements.forEach(el => {
    const html = el.innerHTML || '';
    // /jobs/view/123456/ pattern'ini ara
    const htmlMatches = html.match(/\/jobs\/view\/(\d+)/g);
    if (htmlMatches) {
        htmlMatches.forEach(match => {
            const idMatch = match.match(/(\d+)/);
            if (idMatch) {
                jobIds.add(idMatch[1]);
            }
        });
    }
    // currentJobId=123456 pattern'ini ara
    const paramMatches = html.match(/currentJobId=(\d+)/g);
    if (paramMatches) {
        paramMatches.forEach(match => {
            const idMatch = match.match(/(\d+)/);
            if (idMatch) {
                jobIds.add(idMatch[1]);
            }
        });
    }
});

// Data attribute'lardan job ID'leri bul
const dataElements = document.querySelectorAll('[data-job-id], [data-occludable-job-id], [data-job-id-base]');
dataElements.forEach(el => {
    const jobId = el.getAttribute('data-job-id') || 
                 el.getAttribute('data-occludable-job-id') ||
                 el.getAttribute('data-job-id-base');
    if (jobId) {
        jobIds.add(jobId);
    }
});

// React component'lerinden job ID'leri bul (innerHTML'de arama)
const allDivs = document.querySelectorAll('div, li, article');
allDivs.forEach(el => {
    const html = el.innerHTML || '';
    const matches = html.match(/jobId["\']?\s*[:=]\s*["\']?(\d+)/gi);
    if (matches) {
        matches.forEach(match => {
            const idMatch = match.match(/(\d+)/);
            if (idMatch) {
                jobIds.add(idMatch[1]);
            }
        });
    }
});

const foundAfter = jobIds.size;
const newJobs = foundAfter - foundBefore;
const newScrollHeight = document.body.scrollHeight;

console.log(`   📊 Scroll ${i + 1}/${maxScrollAttempts}: ${foundAfter} job ID bulundu (${newJobs} yeni)`);

// Yeni ilan bulunamadıysa
if (newJobs === 0) {
    consecutiveNoNewJobs++;
    if (consecutiveNoNewJobs >= maxConsecutiveNoNewJobs) {
        console.log(`   ✅ ${maxConsecutiveNoNewJobs} kez üst üste yeni ilan bulunamadı, kaydırma durduruluyor...`);
        break;
    }
} else {
    consecutiveNoNewJobs = 0;
}

// Scroll yüksekliği değişmediyse ve yeni ilan yoksa dur
if (newScrollHeight === lastScrollHeight && newJobs === 0) {
    consecutiveNoNewJobs++;
    if (consecutiveNoNewJobs >= 3) {
        console.log('   ✅ Sayfa sonuna ulaşıldı (scroll yüksekliği değişmiyor)');
        break;
    }
} else {
    consecutiveNoNewJobs = 0;
}

lastScrollHeight = newScrollHeight;

// Her 5 scroll'da bir özet göster
if ((i + 1) % 5 === 0) {
    console.log(`\n   📈 İlerleme: ${foundAfter} ilan bulundu, ${i + 1} scroll tamamlandı\n`);
}
}

console.log(`\n✅ Toplam ${jobIds.size} farklı job ID bulundu`);

if (jobIds.size === 0) {
console.log('\n⚠️ Hiç job ID bulunamadı!');
window.linkedinJobs = [];
return;
}

// Hızlı mod: Sadece job ID'lerini topla, detayları Python'da çıkaracağız
console.log('\n⚡ Hızlı mod: Sadece job ID'leri toplanıyor, detaylar Python'da çıkarılacak...');
const jobs = [];

for (const jobId of jobIds) {
jobs.push({
    title: `İlan #${jobId}`, // Geçici başlık, Python'da güncellenecek
    company: '',
    location: '',
    posted_date: '',
    applicants: '',
    recruiter_info: '',
    response_insight: '',
    job_description: '',
    work_type: '',
    employment_type: '',
    salary: '',
    link: `https://www.linkedin.com/jobs/view/${jobId}/`
});
}

console.log(`✅ ${jobs.length} ilan için minimal bilgiler oluşturuldu`);

// Detaylı bilgi toplama kaldırıldı - Python'da yapılacak
// window.linkedinJobs'u ayarla
window.linkedinJobs = jobs;

console.log(`\n✅ ${jobs.length} ilan bulundu ve window.linkedinJobs'a atandı`);
console.log('💡 Detaylı bilgiler Python scripti tarafından çıkarılacak');

// Eski detaylı işleme kodu kaldırıldı - Python'da yapılacak
// window.linkedinJobs zaten yukarıda ayarlandı

console.log('\n✅ İşlem tamamlandı!');
})();
