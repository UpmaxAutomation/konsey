#!/bin/bash
# restore_backup.sh - Yedekten geri yükleme script'i

set -e

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parametreler
BACKUP_DIR="$1"
NEW_DATABASE_URL="$2"

# Kullanım
if [ -z "$BACKUP_DIR" ] || [ -z "$NEW_DATABASE_URL" ]; then
    echo -e "${RED}Usage: ./restore_backup.sh <BACKUP_DIR> <NEW_DATABASE_URL>${NC}"
    echo ""
    echo "Example:"
    echo "  ./restore_backup.sh backups/20250123_120000 \"postgresql://postgres.xxx:pass@host:5432/postgres\""
    echo ""
    echo "Available backups:"
    ls -d backups/*/ 2>/dev/null | sed 's|backups/||' | sed 's|/$||' | while read dir; do
        echo "  - $dir"
    done
    exit 1
fi

# Backup dizini kontrolü
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}❌ Backup directory not found: $BACKUP_DIR${NC}"
    exit 1
fi

BACKUP_SQL="$BACKUP_DIR/database/backup.sql"
if [ ! -f "$BACKUP_SQL" ]; then
    echo -e "${RED}❌ Backup SQL file not found: $BACKUP_SQL${NC}"
    exit 1
fi

echo -e "${BLUE}🔄 Starting restore from $BACKUP_DIR...${NC}"
echo ""

# 1. Git bilgilerini göster
if [ -f "$BACKUP_DIR/git_commit.txt" ]; then
    echo -e "${YELLOW}📝 Backup Information:${NC}"
    echo "  Branch: $(cat "$BACKUP_DIR/git_branch.txt" 2>/dev/null || echo 'unknown')"
    echo "  Commit: $(cat "$BACKUP_DIR/git_commit.txt" 2>/dev/null || echo 'unknown')"
    echo "  Tag: $(cat "$BACKUP_DIR/git_tag.txt" 2>/dev/null || echo 'unknown')"
    echo ""
fi

# 2. Onay iste
echo -e "${YELLOW}⚠️  This will restore database to:${NC}"
echo "  $NEW_DATABASE_URL"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled.${NC}"
    exit 0
fi

# 3. Database restore
echo -e "${YELLOW}📊 Restoring database...${NC}"
psql "$NEW_DATABASE_URL" < "$BACKUP_SQL" 2>&1 | while read line; do
    echo "  $line"
done

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database restore completed${NC}"
else
    echo -e "${RED}❌ Database restore failed${NC}"
    exit 1
fi

# 4. Code checkout (opsiyonel)
if [ -f "$BACKUP_DIR/git_commit.txt" ]; then
    COMMIT=$(cat "$BACKUP_DIR/git_commit.txt")
    if [ "$COMMIT" != "not-a-git-repo" ] && git rev-parse --verify "$COMMIT" >/dev/null 2>&1; then
        echo ""
        echo -e "${YELLOW}📝 Checking out code to commit: $COMMIT${NC}"
        read -p "Checkout code? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git checkout "$COMMIT"
            echo -e "${GREEN}✅ Code checkout completed${NC}"
        fi
    fi
fi

# 5. .env setup
echo ""
echo -e "${YELLOW}⚙️  Setting up .env...${NC}"
if [ -f "$BACKUP_DIR/config/.env.example" ]; then
    cp "$BACKUP_DIR/config/.env.example" .env
    # DATABASE_URL'i güncelle
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=\"$NEW_DATABASE_URL\"|" .env
    else
        # Linux
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=\"$NEW_DATABASE_URL\"|" .env
    fi
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${BLUE}   Please review and update other variables if needed${NC}"
else
    echo -e "${YELLOW}⚠️  .env.example not found in backup${NC}"
fi

echo ""
echo -e "${GREEN}✅ Restore completed!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Review .env file: cat .env"
echo "  2. Start backend: cd backend && python -m uvicorn main:app --reload"
echo "  3. Test the application"
