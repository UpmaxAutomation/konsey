#!/bin/bash
# backup_full.sh - Tam yedekleme script'i (Kod + Veritabanı)

set -e

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/config"

echo -e "${BLUE}📦 Starting full backup...${NC}"

# 1. Database dump
echo -e "${YELLOW}📊 Backing up database...${NC}"

# DATABASE_URL'i .env'den oku
if [ -f .env ]; then
    DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")
else
    echo -e "${YELLOW}⚠️  .env file not found. Using example connection string.${NC}"
    echo -e "${YELLOW}Please set DATABASE_URL in .env file or pass as argument.${NC}"
    echo "Usage: ./backup_full.sh [DATABASE_URL]"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL not found in .env${NC}"
    if [ -n "$1" ]; then
        DATABASE_URL="$1"
        echo -e "${BLUE}Using DATABASE_URL from argument${NC}"
    else
        echo "Please provide DATABASE_URL as argument or set in .env"
        exit 1
    fi
fi

# pg_dump ile backup al
pg_dump "$DATABASE_URL" \
  --no-owner \
  --no-acl \
  --clean \
  --if-exists \
  -f "$BACKUP_DIR/database/backup.sql" 2>&1 | while read line; do
    echo "  $line"
  done

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database backup completed${NC}"
else
    echo -e "${YELLOW}⚠️  Database backup failed. Continuing with code backup...${NC}"
fi

# 2. Git commit hash
echo -e "${YELLOW}📝 Saving git information...${NC}"
git rev-parse HEAD > "$BACKUP_DIR/git_commit.txt" 2>/dev/null || echo "not-a-git-repo" > "$BACKUP_DIR/git_commit.txt"
git branch --show-current > "$BACKUP_DIR/git_branch.txt" 2>/dev/null || echo "unknown" > "$BACKUP_DIR/git_branch.txt"
git describe --tags --always > "$BACKUP_DIR/git_tag.txt" 2>/dev/null || echo "no-tag" > "$BACKUP_DIR/git_tag.txt"

# 3. .env.example
echo -e "${YELLOW}⚙️  Saving configuration template...${NC}"
if [ -f .env.example ]; then
    cp .env.example "$BACKUP_DIR/config/.env.example"
else
    echo "# .env.example not found" > "$BACKUP_DIR/config/.env.example"
fi

# 4. README
cat > "$BACKUP_DIR/README.md" << EOF
# Full Backup - $(date)

## Database
- Source: Supabase Production
- Backup File: database/backup.sql
- Size: $(du -h "$BACKUP_DIR/database/backup.sql" 2>/dev/null | cut -f1 || echo "N/A")

## Code
- Branch: $(cat "$BACKUP_DIR/git_branch.txt")
- Commit: $(cat "$BACKUP_DIR/git_commit.txt")
- Tag: $(cat "$BACKUP_DIR/git_tag.txt")
- Date: $(date)

## Restore Instructions

### Option 1: Restore to New Supabase Project

1. Create new Supabase project
2. Get connection string
3. Run: \`psql "NEW_DATABASE_URL" < database/backup.sql\`

### Option 2: Restore to Local PostgreSQL

\`\`\`bash
createdb llm_council_backup
psql llm_council_backup < database/backup.sql
\`\`\`

### Option 3: Use restore_backup.sh

\`\`\`bash
./restore_backup.sh "NEW_DATABASE_URL"
\`\`\`

## Files
- \`database/backup.sql\` - Full database dump
- \`config/.env.example\` - Configuration template
- \`git_*.txt\` - Git version information
EOF

# 5. Backup summary
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "N/A")
DB_SIZE=$(du -h "$BACKUP_DIR/database/backup.sql" 2>/dev/null | cut -f1 || echo "N/A")

echo ""
echo -e "${GREEN}✅ Backup completed!${NC}"
echo -e "${BLUE}📁 Location: $BACKUP_DIR${NC}"
echo -e "${BLUE}📊 Database size: $DB_SIZE${NC}"
echo -e "${BLUE}💾 Total size: $BACKUP_SIZE${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review backup: cat $BACKUP_DIR/README.md"
echo "  2. Test restore to new database"
echo "  3. Store backup in safe location"
