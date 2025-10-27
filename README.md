# parmak_izi_minitue

parmakizi-projesi
Bu proje, NBIS (NIST Biometric Image Software) araçlarını kullanan bir Python FastAPI backend servisidir. İki parmak izi dosyasını (.wsq dahil) alıp karşılaştırır, aralarındaki eşleşme skorunu 0-100 arası bir yüzdeye çevirir ve parmak izi üzerindeki "minutiae" (ayırt edici noktalar) verilerini görselleştirilmiş bir PNG olarak döndürür.

Ana Özellikler
Parmak İzi Yükleme: .wsq, .png, .jpg gibi farklı formatlardaki dosyaları işleyebilir.

Minutiae Çıkarımı: mindtct aracını kullanarak parmak izlerinden .xyt formatında ayırt edici nokta verilerini çıkarır.

Kalite Skoru: nfiq2 aracını kullanarak yüklenen parmak izlerinin NFIQ2 kalite skorlarını (1-100) hesaplar.

Yüzdelik Eşleşme Skoru: bozorth3'ten gelen ham eşleşme skorunu (örn: 472) alır ve bunu backend_app.py içinde tanımlanan MIN_MATCH_THRESHOLD (40.0) ve MAX_SATURATION_SCORE (500.0) değerlerine göre 0-100 arasında anlamlı bir yüzdelik skora normalize eder.

Görselleştirme: Yüklenen parmak izi görüntülerini .png formatına çevirir ve mindtct tarafından bulunan tüm ayırt edici noktaları (minutiae) yeşil daireler halinde çizerek base64 formatında frontend'e gönderir.

Mimari
Proje, tüm ağır işi yapan bir Backend (FastAPI) servisinden oluşur. Bu servis, NBIS komut satırı araçlarını (mindtct, bozorth3 vb.) subprocess kullanarak çalıştırır, dosya dönüştürme (örn: WSQ -> PNG) ve skor hesaplama işlemlerini yapar, sonuçları JSON formatında sunar.

Kurulum ve Çalıştırma
1. Ön Gereksinim: NBIS

Bu backend'in çalışması için NBIS kütüphanesinin sisteminizde kurulu ve derlenmiş olması zorunludur.

backend_utils.py dosyasının ihtiyaç duyduğu spesifik NBIS araçları şunlardır:

mindtct

bozorth3

nfseg

dwsq

imginfo

rdimgwh

nfiq2

Bu araçların bulunduğu bin klasörünün yolunu bir sonraki adım için not edin.

2. Backend (FastAPI) Kurulumu

Projeyi klonlayın ve backend klasörüne gidin:

Bash
git clone <proje-linkiniz>
cd parmakizi-projesi/
Python sanal ortamı oluşturun ve aktifleştirin (Önerilir):

Bash
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate
requirements.txt dosyasındaki  temel bağımlılıkları yükleyin:

Bash
pip install -r requirements.txt
ÖNEMLİ: backend_utils.py dosyasının kullandığı ancak requirements.txt'de listelenmeyen ek kütüphaneleri yükleyin:

Bash
pip install opencv-python numpy Pillow
3. Ortam Değişkenleri (.env)

Projenin NBIS araçlarını bulabilmesi için bir .env dosyası oluşturmanız şarttır. Proje ana dizininde (backend_app.py ile aynı yerde) .env adında bir dosya oluşturun ve içini backend_utils.py dosyasındaki varsayılan yollara benzer şekilde doldurun:

Kod snippet'i
# .env DOSYASI ÖRNEĞİ
# Bu yolları KENDİ SİSTEMİNİZE göre güncelleyin!
NBIS_BIN=/Users/efegurmarmara/Documents/NBIS/bin
NFIQ2_PATH=/Users/efegurmarmara/Documents/NBIS/bin/nfiq2

# Frontend'inizin çalıştığı adresi buraya ekleyin (CORS için)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
4. Sunucuyu Başlatma

Kurulum tamamlandığında, sunucuyu uvicorn  ile başlatabilirsiniz:

Bash
uvicorn backend_app:app --reload --port 8000
Sunucu artık http://localhost:8000 adresinde çalışıyor olacaktır.

API Endpoints
GET /health: NBIS araçlarının sistemde doğru yapılandırılıp yapılandırılmadığını kontrol eder.

POST /analyze: Tek bir parmak izi dosyası alır, nfiq2 kalite skorunu hesaplar ve döndürür.

POST /compare: İki adet parmak izi dosyası (file1 ve file2) alır. Karşılaştırma yapar ve aşağıdaki formatta bir JSON yanıtı döndürür:

bozorth3_score: Yüzdeliğe çevrilmiş eşleşme skoru (float).

a_quality / b_quality: Dosyaların NFIQ2 kalite bilgileri (dict).

quality_summary: İki dosyanın ortalama kalite skoru (str).

a_png_b64 / b_png_b64: Üzerinde tüm minutiae noktaları yeşil ile çizilmiş olan, base64 formatında PNG görselleri (str).


Eng:

parmakizi-projesi
This project is a Python FastAPI backend service that utilizes NBIS (NIST Biometric Image Software) tools. It compares two fingerprint files (including .wsq), converts the raw match score into a percentage (0-100), and returns a PNG visualizing the "minutiae" (distinguishing points) on the fingerprint.

Key Features
File Upload: Can process files in various formats like .wsq, .png, and .jpg.

Minutiae Extraction: Uses the mindtct tool to extract distinguishing point data in .xyt format from fingerprints.

Quality Score: Calculates the NFIQ2 quality score (1-100) for uploaded fingerprints using the nfiq2 tool.

Percentage Match Score: Takes the raw match score (e.g., 472) from bozorth3 and normalizes it to a meaningful 0-100 percentage score based on MIN_MATCH_THRESHOLD (40.0) and MAX_SATURATION_SCORE (500.0) defined in backend_app.py.

Visualization: Converts uploaded fingerprint images to PNG format, draws all detected minutiae points (from mindtct) as green circles, and returns them to the frontend in base64 format.

Architecture
The project consists of a Backend (FastAPI) service that does all the heavy lifting. It runs the NBIS command-line tools (mindtct, bozorth3, etc.) using subprocess, handles file conversions (e.g., WSQ to PNG) and score calculations, and serves the results as JSON.

Setup and Running
1. Prerequisite: NBIS

Installation and compilation of the NBIS library on your system is mandatory for this backend to work.

The specific NBIS tools required by backend_utils.py are:

mindtct

bozorth3

nfseg

dwsq

imginfo

rdimgwh

nfiq2

Take note of the path to the bin directory containing these tools for the next step.

2. Backend (FastAPI) Setup

Clone the project and navigate to the backend folder:

Bash
git clone <your-project-link>
cd parmakizi-projesi/
Create and activate a Python virtual environment (Recommended):

Bash
python -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate
Install the base dependencies from requirements.txt:

Bash
pip install -r requirements.txt
IMPORTANT: Install the additional libraries used by backend_utils.py but not listed in requirements.txt:

Bash
pip install opencv-python numpy Pillow
3. Environment Variables (.env)

You must create a .env file for the project to find the NBIS tools. Create a file named .env in the project's root directory (same place as backend_app.py) and fill it in, similar to the defaults in backend_utils.py:

Kod snippet'i
# .env FILE EXAMPLE
# Update these paths to match YOUR SYSTEM!
NBIS_BIN=/Users/efegurmarmara/Documents/NBIS/bin
NFIQ2_PATH=/Users/efegurmarmara/Documents/NBIS/bin/nfiq2

# Add your frontend's origin here (for CORS)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
4. Start the Server

Once the setup is complete, you can start the server with uvicorn:

Bash
uvicorn backend_app:app --reload --port 8000
The server will now be running at http://localhost:8000.

API Endpoints
GET /health: Checks if the NBIS tools are correctly configured in the system.

POST /analyze: Takes a single fingerprint file, calculates its nfiq2 quality score, and returns it.

POST /compare: Takes two fingerprint files (file1 and file2). It performs the comparison and returns a JSON response in the following format:

bozorth3_score: The percentage-normalized match score (float).

a_quality / b_quality: The NFIQ2 quality information for the files (dict).

quality_summary: The average quality score of the two files (str).

a_png_b64 / b_png_b64: Base64-encoded PNG images with all minutiae points drawn in green (str).
