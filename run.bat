@echo off
REM LinkedIn Ghost Job Analyzer - Windows Çalıştırma Scripti

cd /d "%~dp0"

echo ================================================================================
echo LinkedIn Ghost Job Analyzer
echo ================================================================================
echo.

REM Kullanım kontrolü
if "%~1"=="" (
    echo Kullanım:
    echo   run.bat jobs.json              - JSON dosyasından analiz yap
    echo.
    echo Örnek:
    echo   run.bat jobs.json              # Mevcut JSON dosyasını analiz et
    echo.
    echo 💡 JSON dosyası oluşturmak için:
    echo    1. Chrome'da LinkedIn iş ilanları sayfasını açın
    echo    2. F12 ile Developer Tools'u açın
    echo    3. Console sekmesine gidin
    echo    4. linkedin_extractor.js kodunu yapıştırın ve Enter'a basın
    echo    5. JSON çıktısını kopyalayın ve jobs.json dosyasına kaydedin
    pause
    exit /b 1
)

echo 📊 Analiz başlatılıyor: %1
python linkedin_analyzer.py "%1"

echo.
echo ✅ İşlem tamamlandı!
echo.
pause
