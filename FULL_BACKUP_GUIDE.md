# 💾 Tam Yedekleme Rehberi (Kod + Veritabanı)

## Hedef

Hem kodu hem de veritabanı verilerini yedeklemek ve istediğiniz zaman geri yükleyebilmek.

## Yöntem 1: Supabase Dump + Git Clone (Önerilen)

### Adım 1: Veritabanı Dump'ı Al

**Seçenek A: Supabase Dashboard'dan**

1. Supabase Dashboard'a gidin: https://supabase.com/dashboard
2. Project seçin: `rdjxqrrnhfbekpbsjgjk`
3. Settings → Database → "Backups" sekmesi
4. "Download backup" butonuna tıklayın
5. Veya "Create backup" ile yeni bir backup oluşturun

**Seçenek B: pg_dump ile (Komut Satırı)**

```bash
# Connection string ile dump al
pg_dump "postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5%24%24J1vbZmqX%24c@aws-0-us-east-1.pooler.supabase.com:6543/postgres" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  -f backup_$(date +%Y%m%d_%H%M%S).sql
```

**Seçenek C: Supabase CLI ile**

```bash
# Supabase CLI kur
npm install -g supabase

# Login
supabase login

# Project link
supabase link --project-ref rdjxqrrnhfbekpbsjgjk

# Database dump
supabase db dump -f backup.sql
```

### Adım 2: Kodu Clone Et

```bash
cd ~
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-backup
cd llm-council-backup
git checkout backup/production-stable
```

### Adım 3: Backup Dosyalarını Organize Et

```bash
# Backup klasörü oluştur
mkdir -p backups/database
mkdir -p backups/config

# SQL dump'ı taşı
mv backup_*.sql backups/database/

# .env dosyasını yedekle (mevcut ise)
cp .env backups/config/.env.backup 2>/dev/null || echo ".env not found, will create from example"
```

### Adım 4: README Oluştur

```bash
cat > backups/README.md << 'EOF'
# Backup Information

## Backup Date
$(date)

## Database
- Source: Supabase Production
- Project: rdjxqrrnhfbekpbsjgjk
- Backup File: backups/database/backup_*.sql

## Code
- Branch: backup/production-stable
- Commit: $(git rev-parse HEAD)
- Tag: v1.0.0-production

## Restore Instructions
See RESTORE_GUIDE.md
EOF
```

## Yöntem 2: Yeni Supabase Project + Restore

### Adım 1: Yeni Supabase Project Oluştur

1. Supabase Dashboard → "New Project"
2. Project name: `llm-council-backup` veya `llm-council-dev`
3. Database password seçin
4. Region seçin
5. "Create new project" butonuna tıklayın

### Adım 2: Backup'ı Restore Et

**Supabase Dashboard'dan:**

1. Yeni project'e gidin
2. SQL Editor → "New query"
3. Backup SQL dosyasını açın ve içeriğini kopyalayın
4. SQL Editor'e yapıştırın ve "Run" butonuna tıklayın

**Komut Satırından:**

```bash
# Yeni project'in connection string'ini al
NEW_DATABASE_URL="postgresql://postgres.[YENI_PROJECT_REF]:[YENI_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Restore et
psql "$NEW_DATABASE_URL" < backups/database/backup_*.sql
```

### Adım 3: Kodu Yeni Database'e Bağla

```bash
cd llm-council-backup

# .env dosyası oluştur
cp .env.example .env

# .env dosyasını düzenle
cat > .env << EOF
DATABASE_URL="$NEW_DATABASE_URL"
USE_DATABASE=true
ENVIRONMENT="development"
SECRET_KEY="your-secret-key-here"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
EOF
```

## Yöntem 3: Local PostgreSQL + Restore

### Adım 1: Local PostgreSQL Kur

```bash
# macOS
brew install postgresql@14
brew services start postgresql@14

# Database oluştur
createdb llm_council_backup
```

### Adım 2: Backup'ı Restore Et

```bash
# Local PostgreSQL'e restore
psql llm_council_backup < backups/database/backup_*.sql
```

### Adım 3: Kodu Local Database'e Bağla

```bash
# .env dosyası
cat > .env << EOF
DATABASE_URL="postgresql+asyncpg://$(whoami):@localhost:5432/llm_council_backup"
USE_DATABASE=true
ENVIRONMENT="development"
EOF
```

## Otomatik Backup Script

```bash
#!/bin/bash
# backup_full.sh - Tam yedekleme script'i

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/config"

echo "📦 Starting full backup..."

# 1. Database dump
echo "📊 Backing up database..."
pg_dump "postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5%24%24J1vbZmqX%24c@aws-0-us-east-1.pooler.supabase.com:6543/postgres" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  -f "$BACKUP_DIR/database/backup.sql"

# 2. Git commit hash
echo "📝 Saving git information..."
git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt"
git branch --show-current > "$BACKUP_DIR/git_branch.txt"

# 3. .env.example (gerçek .env gitignore'da)
echo "⚙️ Saving configuration template..."
cp .env.example "$BACKUP_DIR/config/.env.example" 2>/dev/null || true

# 4. README
cat > "$BACKUP_DIR/README.md" << EOF
# Full Backup - $(date)

## Database
- Source: Supabase Production (rdjxqrrnhfbekpbsjgjk)
- Backup File: database/backup.sql
- Size: $(du -h "$BACKUP_DIR/database/backup.sql" | cut -f1)

## Code
- Branch: $(cat "$BACKUP_DIR/git_branch.txt")
- Commit: $(cat "$BACKUP_DIR/git_commit.txt")
- Date: $(date)

## Restore
See RESTORE_GUIDE.md in project root.
EOF

echo "✅ Backup completed: $BACKUP_DIR"
echo "📁 Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
```

## Restore Rehberi

```bash
# restore_backup.sh - Yedekten geri yükleme

BACKUP_DIR="backups/20250123_120000"  # Backup klasörünü seçin
NEW_DATABASE_URL="$1"  # Yeni database connection string

if [ -z "$NEW_DATABASE_URL" ]; then
  echo "Usage: ./restore_backup.sh <NEW_DATABASE_URL>"
  exit 1
fi

echo "🔄 Restoring backup from $BACKUP_DIR..."

# 1. Database restore
echo "📊 Restoring database..."
psql "$NEW_DATABASE_URL" < "$BACKUP_DIR/database/backup.sql"

# 2. Code checkout
echo "📝 Checking out code..."
git checkout $(cat "$BACKUP_DIR/git_commit.txt")

# 3. .env setup
echo "⚙️ Setting up .env..."
cp "$BACKUP_DIR/config/.env.example" .env
# DATABASE_URL'i düzenle
sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=\"$NEW_DATABASE_URL\"|" .env

echo "✅ Restore completed!"
```

## Hızlı Başlangıç

### Tam Yedek Almak İçin:

```bash
# 1. Script'i çalıştırılabilir yap
chmod +x backup_full.sh

# 2. Backup al
./backup_full.sh

# 3. Backup klasörünü kontrol et
ls -lh backups/
```

### Yedekten Geri Yüklemek İçin:

```bash
# 1. Yeni Supabase project oluştur (Dashboard'dan)
# 2. Connection string'i al
NEW_DB="postgresql://postgres.[YENI_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# 3. Restore et
./restore_backup.sh "$NEW_DB"
```

## Önerilen Yapı

```
llm-council-backup/
├── backups/
│   ├── 20250123_120000/
│   │   ├── database/
│   │   │   └── backup.sql
│   │   ├── config/
│   │   │   └── .env.example
│   │   ├── git_commit.txt
│   │   ├── git_branch.txt
│   │   └── README.md
│   └── README.md
├── backend/
├── frontend/
├── .env
└── RESTORE_GUIDE.md
```

## Önemli Notlar

1. **Backup Boyutu**: Database dump'ları büyük olabilir (100MB+)
2. **Şifreleme**: API keys encrypted, restore sonrası çalışır
3. **User ID'ler**: Restore sonrası user ID'ler aynı kalır
4. **Migration**: Yeni database'de migration gerekmez (dump zaten schema içerir)

## Güvenlik

- Backup dosyalarını güvenli bir yerde saklayın
- `.env` dosyalarını Git'e commit etmeyin
- Backup script'lerini `.gitignore`'a ekleyin (eğer içinde password varsa)
