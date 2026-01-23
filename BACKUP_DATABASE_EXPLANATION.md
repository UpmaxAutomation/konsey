# 💾 Backup Branch ve Veritabanı Açıklaması

## ⚠️ Önemli: Git Branch'leri Sadece Kod İçerir

**Git branch'leri (backup branch dahil) sadece kod dosyalarını içerir:**
- ✅ Python kodları
- ✅ JavaScript/React kodları
- ✅ Konfigürasyon dosyaları
- ✅ README, dokümantasyon
- ❌ **Veritabanı verileri YOK**
- ❌ **SQL kayıtları YOK**

## Veritabanı Nerede?

Veritabanınız **Supabase**'de (cloud servis):
- Production database: `rdjxqrrnhfbekpbsjgjk.supabase.co`
- Bu veritabanı Git repository'den **tamamen bağımsız**
- Branch'lerden etkilenmez

## Sadece Klasörü Alarak Çalışabilir misiniz?

### ✅ Evet, Ama...

**Klasörü alarak:**
1. ✅ Tüm kod dosyalarını alırsınız
2. ✅ Uygulamayı çalıştırabilirsiniz
3. ✅ `.env` dosyasını düzenleyerek farklı database'e bağlanabilirsiniz

**Ama:**
- ❌ Veritabanı verileri (konuşmalar, kullanıcılar, API keys) gelmez
- ❌ Yeni bir database bağlantısı gerekir
- ❌ Veya mevcut Supabase database'ine bağlanmanız gerekir

## Senaryolar

### Senaryo 1: Sadece Kodu Yedeklemek İstiyorsunuz

```bash
# Backup branch'i clone et
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-backup
cd llm-council-backup
git checkout backup/production-stable

# .env dosyasını düzenle
cp .env.example .env
# DATABASE_URL'i ayarla (mevcut Supabase veya yeni bir database)
```

**Sonuç:** Kod çalışır ama veritabanı boş olur (veya mevcut Supabase'e bağlanır)

### Senaryo 2: Veritabanı Verilerini de Yedeklemek İstiyorsunuz

**1. Supabase'den Export:**
```bash
# Supabase Dashboard'dan:
# Settings → Database → Export Data
# veya
# SQL Editor'den:
pg_dump -h aws-0-us-east-1.pooler.supabase.com -U postgres.rdjxqrrnhfbekpbsjgjk -d postgres > backup.sql
```

**2. Yeni Database'e Import:**
```bash
# Yeni bir Supabase project oluştur
# veya local PostgreSQL kullan
psql -h localhost -U postgres -d llm_council < backup.sql
```

**3. Kodu Clone Et:**
```bash
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-backup
cd llm-council-backup
git checkout backup/production-stable
# .env dosyasını yeni database'e göre ayarla
```

### Senaryo 3: Tamamen Bağımsız Çalışmak

**1. Yeni Supabase Project:**
- Supabase'de yeni bir project oluştur
- Yeni `DATABASE_URL` al

**2. Kodu Clone Et:**
```bash
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-dev
cd llm-council-dev
git checkout feature/development
```

**3. .env Dosyasını Ayarla:**
```bash
DATABASE_URL="postgresql+asyncpg://postgres.[YENI_PROJECT]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
USE_DATABASE=true
ENVIRONMENT="development"
```

**4. Database Migration:**
```bash
# Backend'i çalıştır, tablolar otomatik oluşur
cd backend
python -m uvicorn main:app --reload
```

## Mevcut Durumunuz

**Backup branch'inde:**
- ✅ Tüm kod dosyaları var
- ✅ `.env.example` var (template)
- ❌ `.env` dosyası YOK (gitignore'da)
- ❌ Veritabanı verileri YOK

**Çalıştırmak için:**
1. `.env` dosyası oluştur
2. `DATABASE_URL` ayarla (mevcut Supabase veya yeni)
3. Backend'i başlat

## Hızlı Test

Backup branch'i alıp çalıştırmak için:

```bash
# 1. Clone et
cd ~
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-backup
cd llm-council-backup
git checkout backup/production-stable

# 2. .env dosyası oluştur
cp .env.example .env
# .env dosyasını düzenle:
# DATABASE_URL="mevcut Supabase connection string"
# USE_DATABASE=true

# 3. Dependencies yükle
cd backend
pip install -r requirements.txt

# 4. Backend'i başlat
python -m uvicorn main:app --reload
```

## Veritabanı Yedeği Almak İçin

### Supabase Dashboard'dan:
1. Supabase Dashboard'a gidin
2. Settings → Database
3. "Export Data" veya "Backup" seçeneğini kullanın

### SQL Dump:
```bash
# Supabase connection string ile
pg_dump "postgresql://postgres.rdjxqrrnhfbekpbsjgjk:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" > backup.sql
```

### Supabase CLI:
```bash
# Supabase CLI kur
npm install -g supabase

# Login
supabase login

# Database dump
supabase db dump -f backup.sql
```

## Özet

| Öğe | Backup Branch'te Var mı? |
|-----|-------------------------|
| Kod dosyaları | ✅ Evet |
| .env.example | ✅ Evet |
| .env (gerçek) | ❌ Hayır (gitignore) |
| Veritabanı verileri | ❌ Hayır |
| Konuşmalar | ❌ Hayır |
| Kullanıcılar | ❌ Hayır |
| API Keys | ❌ Hayır |

**Sonuç:** Backup branch'i alarak kodu çalıştırabilirsiniz, ama veritabanı verileri için ayrı yedek almanız gerekir.
