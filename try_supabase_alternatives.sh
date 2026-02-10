#!/bin/bash
# Try common Supabase hostname formats

PROJECT_REF="rdjxqrrnhfbekpbsjgjk"
PASSWORD="3yJ5%24%24J1vbZmqX%24c"

echo "Trying different Supabase hostname formats..."
echo ""

# Format 1: Direct connection
HOST1="db.${PROJECT_REF}.supabase.co"
echo "Testing: $HOST1"
if nslookup "$HOST1" >/dev/null 2>&1; then
    echo "✓ $HOST1 resolves!"
    echo "Connection: postgresql+asyncpg://postgres:${PASSWORD}@${HOST1}:5432/postgres"
else
    echo "✗ $HOST1 does not resolve"
fi

# Format 2: Without db prefix
HOST2="${PROJECT_REF}.supabase.co"
echo ""
echo "Testing: $HOST2"
if nslookup "$HOST2" >/dev/null 2>&1; then
    echo "✓ $HOST2 resolves!"
    echo "Connection: postgresql+asyncpg://postgres:${PASSWORD}@${HOST2}:5432/postgres"
else
    echo "✗ $HOST2 does not resolve"
fi

# Format 3: Pooler (common regions)
for region in us-east-1 us-west-1 eu-west-1 ap-southeast-1; do
    HOST3="aws-0-${region}.pooler.supabase.com"
    echo ""
    echo "Testing pooler: $HOST3"
    if nslookup "$HOST3" >/dev/null 2>&1; then
        echo "✓ $HOST3 resolves!"
        echo "Connection: postgresql+asyncpg://postgres.${PROJECT_REF}:${PASSWORD}@${HOST3}:6543/postgres"
    fi
done
