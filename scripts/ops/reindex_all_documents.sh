#!/bin/bash
# Reindex All Documents Script
# Fixes documents marked 'indexed' but missing Elasticsearch/Qdrant IDs

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_URL="${API_URL:-http://localhost:8000}"

echo "📚 Document Reindexing Script"
echo "============================="
echo ""

# Check if backend is running
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo "❌ Backend not running at $API_URL"
    echo "   Start with: make local-e2e"
    exit 1
fi

# Login as admin
echo "1. Logging in as admin..."
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  --form 'username=admin' \
  --form 'password=Admin123!' | \
  python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    exit 1
fi
echo "   ✅ Logged in"

# Trigger reindexing
echo ""
echo "2. Finding broken documents (marked 'indexed' but missing ES/Qdrant IDs)..."
RESULT=$(curl -s -X POST "$API_URL/api/v1/admin/reindex-all-broken" \
  -H "Authorization: Bearer $TOKEN")

COUNT=$(echo "$RESULT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("count", 0))')
MESSAGE=$(echo "$RESULT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("message", ""))')

echo "   $MESSAGE"
echo "   Documents queued: $COUNT"

if [ "$COUNT" -eq "0" ]; then
    echo ""
    echo "✅ No broken documents found - all documents are properly indexed!"
    exit 0
fi

# Wait for processing
echo ""
echo "3. Processing documents..."
echo "   This may take 1-2 minutes for $COUNT documents"
echo "   (Text extraction → ES indexing → Qdrant embeddings)"
echo ""

# Show progress
for i in {1..12}; do
    sleep 10
    PROCESSED=$(curl -s "$API_URL/api/v1/files/list?limit=1000" \
      -H "Authorization: Bearer $TOKEN" | \
      python3 -c 'import sys,json; docs=json.load(sys.stdin).get("documents",[]); print(sum(1 for d in docs if d.get("elasticsearch_id")))')
    echo "   Progress: $PROCESSED documents have Elasticsearch IDs..."
done

# Verify results
echo ""
echo "4. Verification..."
FINAL_INDEXED=$(curl -s "$API_URL/api/v1/files/list?status=indexed&limit=1000" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c 'import sys,json; docs=json.load(sys.stdin).get("documents",[]); properly_indexed=sum(1 for d in docs if d.get("elasticsearch_id") and d.get("qdrant_id")); print(properly_indexed)')

echo "   Properly indexed documents: $FINAL_INDEXED"

# Test search
echo ""
echo "5. Testing search functionality..."
curl -s -X POST "$API_URL/api/v1/search/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}' | \
  python3 -c 'import sys,json; r=json.load(sys.stdin); print(f"   Search returned: {len(r.get(\"results\", []))} results")'

echo ""
echo "✅ Reindexing complete!"
echo ""
echo "Next steps:"
echo "  - Test search in UI"
echo "  - Test chat functionality"
echo "  - Verify ZX-10R documents are findable"

