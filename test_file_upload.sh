#!/bin/bash

# Test script for file upload functionality

BASE_URL="http://localhost:8001/api"

echo "=== Testing File Upload Functionality ==="
echo ""

# Step 1: Create a conversation
echo "1. Creating a new conversation..."
CONV_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations" \
  -H "Content-Type: application/json" \
  -d '{}')
CONV_ID=$(echo $CONV_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Created conversation: $CONV_ID"
echo ""

# Step 2: Create a test file
echo "2. Creating test file..."
cat > /tmp/test_code.py << 'EOF'
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test the function
for i in range(10):
    print(f"fib({i}) = {fibonacci(i)}")
EOF
echo "Created /tmp/test_code.py"
echo ""

# Step 3: Upload the file
echo "3. Uploading file to conversation..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations/$CONV_ID/upload" \
  -F "file=@/tmp/test_code.py")
echo "Upload response:"
echo "$UPLOAD_RESPONSE" | python3 -m json.tool
echo ""

# Step 4: List files in conversation
echo "4. Listing files in conversation..."
LIST_RESPONSE=$(curl -s "$BASE_URL/conversations/$CONV_ID/files")
echo "$LIST_RESPONSE" | python3 -m json.tool
echo ""

# Step 5: Get file content
echo "5. Getting file content..."
CONTENT_RESPONSE=$(curl -s "$BASE_URL/conversations/$CONV_ID/files/test_code.py")
echo "$CONTENT_RESPONSE"
echo ""

# Step 6: Send a message with the file attached
echo "6. Sending message with attached file..."
MESSAGE_RESPONSE=$(curl -s -X POST "$BASE_URL/conversations/$CONV_ID/message" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Analyze this Python code and suggest improvements.",
    "attached_files": ["test_code.py"]
  }')
echo "Message sent. Response contains:"
echo "$MESSAGE_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Stage1: {len(d.get('stage1', []))} responses\"); print(f\"Stage2: {len(d.get('stage2', []))} rankings\"); print(f\"Stage3: {d.get('stage3', {}).get('model', 'N/A')}\")"
echo ""

# Step 7: Download the file
echo "7. Downloading file..."
curl -s "$BASE_URL/conversations/$CONV_ID/files/test_code.py" -o /tmp/downloaded_test.py
echo "Downloaded to /tmp/downloaded_test.py"
echo "File contents match: $(diff /tmp/test_code.py /tmp/downloaded_test.py && echo 'YES' || echo 'NO')"
echo ""

# Step 8: Delete the file
echo "8. Deleting file from conversation..."
DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/conversations/$CONV_ID/files/test_code.py")
echo "$DELETE_RESPONSE" | python3 -m json.tool
echo ""

# Step 9: Verify file was deleted
echo "9. Verifying file was deleted..."
LIST_AFTER_DELETE=$(curl -s "$BASE_URL/conversations/$CONV_ID/files")
FILE_COUNT=$(echo "$LIST_AFTER_DELETE" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
echo "Files remaining: $FILE_COUNT (should be 0)"
echo ""

# Cleanup
rm -f /tmp/test_code.py /tmp/downloaded_test.py

echo "=== Test Complete ==="
