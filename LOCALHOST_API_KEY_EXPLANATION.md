# 🔑 Localhost'ta API Key Görünmüyor - Açıklama

## Sorun

Online versiyonda (production) API key'inizi girdiniz ama localhost'ta göremiyorsunuz.

## Neden?

**Localhost ve production farklı veritabanları kullanıyor:**

1. **Production (Railway)**: Supabase production database kullanıyor
   - `DATABASE_URL` → Supabase production connection string
   - API keys burada saklanıyor

2. **Localhost**: Farklı bir database kullanıyor
   - Ya local PostgreSQL
   - Ya farklı bir Supabase project
   - Ya da JSON file storage (eğer `USE_DATABASE=false` ise)

3. **API Keys User-Specific**: API keys `user_api_keys` tablosunda, kullanıcı ID'si ile saklanıyor
   - Her environment'ta farklı user ID'leri olabilir
   - Encryption key (`SECRET_KEY`) farklı olabilir

## Çözümler

### ✅ Çözüm 1: Localhost'ta Tekrar Girin (Önerilen)

En basit ve güvenli çözüm:

1. Localhost'ta giriş yapın: `http://localhost:5173`
2. Settings → API Keys bölümüne gidin
3. OpenRouter API key'inizi tekrar girin
4. Kaydedin

**Avantajlar:**
- Hızlı ve kolay
- Güvenli (production database'e erişim gerekmez)
- Her environment kendi keys'ini yönetir

### ⚠️ Çözüm 2: Aynı Database'i Kullan (Geliştirme İçin)

Eğer localhost'ta da production database'i kullanmak istiyorsanız:

1. `.env` dosyanızı açın
2. `DATABASE_URL` değerini production Supabase connection string ile değiştirin:
   ```bash
   DATABASE_URL="postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5%24%24J1vbZmqX%24c@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ```
3. `USE_DATABASE=true` olduğundan emin olun
4. Backend'i yeniden başlatın

**⚠️ Dikkat:**
- Production database'i kullanmak riskli olabilir
- Test verileri production'a karışabilir
- Sadece geliştirme için önerilir

### 🔄 Çözüm 3: Database Migration (Gelişmiş)

Eğer API keys'i localhost'a migrate etmek istiyorsanız:

1. Production database'den API keys'i export edin
2. Localhost database'e import edin
3. User ID mapping yapın (production user ID → localhost user ID)

**Not:** Bu işlem karmaşık ve genellikle gerekli değil.

## Hangi Database Kullanılıyor?

Localhost'ta hangi database kullanıldığını kontrol etmek için:

1. `.env` dosyanızı kontrol edin:
   ```bash
   cat .env | grep DATABASE_URL
   cat .env | grep USE_DATABASE
   ```

2. Eğer `USE_DATABASE=false` ise → JSON file storage kullanılıyor
3. Eğer `USE_DATABASE=true` ise → `DATABASE_URL`'deki database kullanılıyor

## Öneri

**En iyi pratik:** Her environment'ta (localhost, staging, production) API keys'i ayrı ayrı yönetin. Bu:
- Güvenli (her environment izole)
- Esnek (farklı keys kullanabilirsiniz)
- Basit (migration gerekmez)

## Hızlı Test

Localhost'ta API key'inizin olup olmadığını kontrol etmek için:

1. Browser console'u açın (F12)
2. Network tab'ına gidin
3. Settings sayfasında API Keys bölümüne gidin
4. `GET /api/keys` request'ini kontrol edin
5. Response'da `has_key: false` görüyorsanız → Key yok, tekrar girmeniz gerekiyor
