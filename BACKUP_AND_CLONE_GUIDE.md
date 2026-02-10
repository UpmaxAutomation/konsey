# 💾 Uygulama Yedekleme ve Klonlama Rehberi

## Mevcut Durum

Şu anda `feature/deploy-vercel-railway` branch'indesiniz ve uygulama production'da çalışıyor.

## Yedekleme Seçenekleri

### ✅ Seçenek 1: Git Tag Oluştur (Önerilen)

Mevcut versiyonu bir tag ile işaretleyin:

```bash
# Mevcut versiyonu tag'le
git tag -a v1.0.0-production -m "Production ready version - Vercel + Railway deployment"

# Tag'i GitHub'a push et
git push origin v1.0.0-production
```

**Avantajlar:**
- Mevcut versiyon korunur
- İstediğiniz zaman bu tag'e geri dönebilirsiniz
- Branch'ler üzerinde çalışmaya devam edebilirsiniz

**Geri dönmek için:**
```bash
git checkout v1.0.0-production
```

### ✅ Seçenek 2: Yeni Branch Oluştur

Mevcut branch'i koruyup yeni bir branch'te çalışın:

```bash
# Mevcut branch'ten yeni bir branch oluştur
git checkout -b feature/development

# Veya mevcut branch'i korumak için backup branch oluştur
git checkout -b backup/production-stable
git checkout feature/deploy-vercel-railway
```

**Avantajlar:**
- Production branch korunur
- Yeni branch'te denemeler yapabilirsiniz
- İstediğiniz zaman production branch'e geri dönebilirsiniz

### ✅ Seçenek 3: Ayrı Klasöre Clone

Uygulamayı başka bir klasöre clone edin:

```bash
# Yeni bir klasöre clone yap
cd ~
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-backup
cd llm-council-backup
git checkout feature/deploy-vercel-railway

# Veya sadece mevcut klasörü kopyala
cd ~
cp -r llm-council llm-council-backup
```

**Avantajlar:**
- Tam bir yedek
- Bağımsız çalışabilirsiniz
- Farklı environment variable'lar kullanabilirsiniz

### ✅ Seçenek 4: GitHub Release Oluştur

GitHub'da bir release oluşturun:

1. GitHub repository'ye gidin
2. "Releases" → "Create a new release"
3. Tag: `v1.0.0-production`
4. Title: "Production Ready Version"
5. Description: Deployment bilgileri
6. "Publish release" butonuna tıklayın

**Avantajlar:**
- GitHub'da görünür
- ZIP dosyası olarak indirilebilir
- Versiyon geçmişi tutulur

## Önerilen Yaklaşım

**En iyi pratik:** Hem tag hem de backup branch oluşturun:

```bash
# 1. Tag oluştur (versiyon işareti)
git tag -a v1.0.0-production -m "Production ready - Vercel + Railway"
git push origin v1.0.0-production

# 2. Backup branch oluştur (güvenlik için)
git checkout -b backup/production-stable
git push origin backup/production-stable

# 3. Development branch'e geç
git checkout -b feature/development
```

## Klon Üzerinde Çalışmak

### Senaryo 1: Aynı Repository, Farklı Branch

```bash
# Mevcut klasörde
git checkout feature/development
# Artık development branch'indesiniz
# Değişiklikler production'u etkilemez
```

### Senaryo 2: Ayrı Klasör, Aynı Repository

```bash
# Yeni klasör oluştur
cd ~
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-dev
cd llm-council-dev
git checkout feature/development

# Farklı .env dosyası kullan
cp .env.example .env
# .env dosyasını düzenle (farklı database, port, vs.)
```

### Senaryo 3: Fork Repository

1. GitHub'da repository'yi fork edin
2. Fork'u local'e clone edin:
   ```bash
   git clone https://github.com/YOUR_USERNAME/konsey.git llm-council-fork
   ```

## Environment Variables

Klon üzerinde çalışırken farklı environment variables kullanın:

**Production (.env):**
```bash
DATABASE_URL="postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:..."
ENVIRONMENT="production"
VITE_API_URL="https://konsey-production-b999.up.railway.app"
```

**Development (.env):**
```bash
DATABASE_URL="postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:..." # veya local DB
ENVIRONMENT="development"
VITE_API_URL="http://localhost:8001"
```

## Hızlı Komutlar

### Mevcut Versiyonu Tag'le
```bash
git tag -a v1.0.0-production -m "Production ready version"
git push origin v1.0.0-production
```

### Backup Branch Oluştur
```bash
git checkout -b backup/production-stable
git push origin backup/production-stable
git checkout feature/deploy-vercel-railway
```

### Yeni Klasöre Clone
```bash
cd ~
git clone https://github.com/UpmaxAutomation/konsey.git llm-council-dev
cd llm-council-dev
```

### Tag'e Geri Dön
```bash
git checkout v1.0.0-production
```

## Önemli Notlar

1. **Production branch'i koruyun** - Asla doğrudan production branch'inde çalışmayın
2. **Tag'leri kullanın** - Önemli versiyonları tag'leyin
3. **Environment variables** - Her environment için farklı .env kullanın
4. **Database** - Development için ayrı database kullanın (production'u etkilememek için)

## Sorun Giderme

**Tag göremiyorum:**
```bash
git fetch --tags
git tag -l
```

**Branch değiştiremiyorum:**
```bash
git stash  # Değişiklikleri sakla
git checkout feature/development
git stash pop  # Değişiklikleri geri getir
```

**Clone yaparken hata:**
```bash
# SSH kullan
git clone git@github.com:UpmaxAutomation/konsey.git llm-council-dev
```
