# 🔄 Yedekten Geri Yükleme Rehberi

## Hızlı Başlangıç

### 1. Tam Yedek Almak

```bash
# Script'i çalıştırılabilir yap (ilk sefer)
chmod +x backup_full.sh

# Backup al
./backup_full.sh

# Veya DATABASE_URL'i parametre olarak ver
./backup_full.sh "postgresql://postgres.xxx:pass@host:5432/postgres"
```

**Çıktı:**
```
📦 Starting full backup...
📊 Backing up database...
✅ Database backup completed
📝 Saving git information...
⚙️  Saving configuration template...
✅ Backup completed!
📁 Location: backups/20250123_120000
```

### 2. Yedekten Geri Yüklemek

#### Seçenek A: Yeni Supabase Project'e

```bash
# 1. Yeni Supabase project oluştur (Dashboard'dan)
# 2. Connection string'i al
NEW_DB="postgresql://postgres.[YENI_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# 3. Restore et
./restore_backup.sh backups/20250123_120000 "$NEW_DB"
```

#### Seçenek B: Local PostgreSQL'e

```bash
# 1. Local database oluştur
createdb llm_council_backup

# 2. Restore et
./restore_backup.sh backups/20250123_120000 "postgresql://$(whoami):@localhost:5432/llm_council_backup"
```

## Detaylı Adımlar

### Adım 1: Backup Klasörünü Seç

```bash
# Mevcut backup'ları listele
ls -lh backups/

# Örnek çıktı:
# backups/
#   ├── 20250123_120000/
#   ├── 20250123_150000/
#   └── 20250123_180000/
```

### Adım 2: Yeni Database Hazırla

**Supabase:**
1. https://supabase.com/dashboard
2. "New Project"
3. Project name: `llm-council-backup`
4. Password seç
5. "Create new project"
6. Settings → Database → Connection string'i kopyala

**Local PostgreSQL:**
```bash
# PostgreSQL kur (macOS)
brew install postgresql@14
brew services start postgresql@14

# Database oluştur
createdb llm_council_backup
```

### Adım 3: Restore Et

```bash
./restore_backup.sh backups/20250123_120000 "YOUR_DATABASE_URL"
```

Script otomatik olarak:
- ✅ Database'i restore eder
- ✅ Code'u checkout eder (opsiyonel)
- ✅ .env dosyası oluşturur

### Adım 4: Test Et

```bash
# Backend'i başlat
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload

# Frontend'i başlat
cd frontend
npm install
npm run dev
```

## Manuel Restore

Eğer script kullanmak istemiyorsanız:

### 1. Database Restore

```bash
# SQL dosyasını restore et
psql "YOUR_DATABASE_URL" < backups/20250123_120000/database/backup.sql
```

### 2. Code Checkout

```bash
# Git commit'e geri dön
git checkout $(cat backups/20250123_120000/git_commit.txt)
```

### 3. .env Setup

```bash
# .env dosyası oluştur
cp backups/20250123_120000/config/.env.example .env

# DATABASE_URL'i düzenle
nano .env  # veya vim, code, vs.
```

## Sorun Giderme

### "pg_dump: command not found"

```bash
# macOS
brew install postgresql@14

# Linux
sudo apt-get install postgresql-client
```

### "psql: connection refused"

- Database URL'ini kontrol edin
- Database'in çalıştığından emin olun
- Firewall/network ayarlarını kontrol edin

### "permission denied"

```bash
# Script'leri çalıştırılabilir yap
chmod +x backup_full.sh restore_backup.sh
```

### "database does not exist"

```bash
# Database oluştur
createdb llm_council_backup
```

## Backup Yapısı

```
backups/
└── 20250123_120000/
    ├── database/
    │   └── backup.sql          # Full database dump
    ├── config/
    │   └── .env.example       # Configuration template
    ├── git_commit.txt          # Git commit hash
    ├── git_branch.txt          # Git branch name
    ├── git_tag.txt             # Git tag
    └── README.md               # Backup information
```

## Güvenlik Notları

1. **Backup dosyalarını güvenli saklayın**
   - Şifrelenmiş disk kullanın
   - Cloud storage'a yükleyin (şifreli)
   - Git'e commit etmeyin

2. **Connection string'leri güvenli tutun**
   - .env dosyalarını Git'e commit etmeyin
   - Backup script'lerinde password'ları hardcode etmeyin

3. **Restore sonrası**
   - .env dosyasını kontrol edin
   - API keys'leri yeniden ayarlayın (gerekirse)
   - Test edin

## Otomatik Backup (Cron)

Her gün otomatik backup almak için:

```bash
# Crontab düzenle
crontab -e

# Her gün saat 02:00'de backup al
0 2 * * * cd /Users/sezars/llm-council && ./backup_full.sh >> backups/backup.log 2>&1
```

## Öneriler

1. **Düzenli backup alın** - Haftalık veya günlük
2. **Birden fazla backup tutun** - Son 7 günün backup'larını saklayın
3. **Test restore yapın** - Backup'ların çalıştığından emin olun
4. **Backup'ları farklı yerlere kopyalayın** - Local + Cloud
