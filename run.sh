#!/bin/bash
# LinkedIn Ghost Job Analyzer - Çalıştırma Scripti

cd "/Users/serdar/Desktop/Makale_Video/Super Mario-New/exam/Linkedin"

echo "=================================================================================="
echo "LinkedIn Ghost Job Analyzer"
echo "=================================================================================="
echo ""

# Kullanım kontrolü
if [ $# -eq 0 ]; then
    echo "Kullanım:"
    echo "  ./run.sh jobs.json              - JSON dosyasından analiz yap"
    echo ""
    echo "Örnek:"
    echo "  ./run.sh jobs.json              # Mevcut JSON dosyasını analiz et"
    echo ""
    echo "💡 JSON dosyası oluşturmak için:"
    echo "   1. Chrome'da LinkedIn iş ilanları sayfasını açın"
    echo "   2. F12 ile Developer Tools'u açın"
    echo "   3. Console sekmesine gidin"
    echo "   4. linkedin_extractor.js kodunu yapıştırın ve Enter'a basın"
    echo "   5. JSON çıktısını kopyalayın ve jobs.json dosyasına kaydedin"
    exit 1
fi

echo "📊 Analiz başlatılıyor: $1"
python3 linkedin_analyzer.py "$1"

echo ""
echo "✅ İşlem tamamlandı!"

