#!/bin/bash
# Validate and Fix S3 Dual-Write Configuration

echo "🔍 AWS S3 DUAL-WRITE DIAGNOSTIC"
echo "========================================================================"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    echo "   Install: brew install awscli"
    exit 1
fi

echo "✅ AWS CLI installed"

# Check current credentials
echo ""
echo "📋 Current AWS Configuration:"
aws configure list

# Test credentials
echo ""
echo "🧪 Testing AWS Credentials..."
if aws sts get-caller-identity &>/dev/null; then
    echo "✅ AWS credentials are VALID"
    aws sts get-caller-identity
else
    echo "❌ AWS credentials are INVALID"
    echo ""
    echo "💡 TO FIX:"
    echo "   1. Go to: https://console.aws.amazon.com/iam"
    echo "   2. Navigate to: Users → Your User → Security Credentials"
    echo "   3. Create new Access Key"
    echo "   4. Update .env file with new credentials:"
    echo ""
    echo "      cd /Users/Collins/iDo/Projects/indoc"
    echo "      nano .env"
    echo ""
    echo "      Update these lines:"
    echo "      S3_ACCESS_KEY_ID=<your-new-access-key>"
    echo "      S3_SECRET_ACCESS_KEY=<your-new-secret-key>"
    echo ""
    exit 1
fi

# Test bucket access
echo ""
echo "🪣 Testing S3 Bucket Access..."
BUCKET="shaoxy-indoc"

if aws s3 ls "s3://$BUCKET/" &>/dev/null; then
    echo "✅ Can access bucket: $BUCKET"
    echo ""
    echo "📊 Current bucket contents:"
    aws s3 ls "s3://$BUCKET/" --recursive | wc -l | xargs echo "   Files:"
    aws s3 ls "s3://$BUCKET/" --recursive --summarize | grep "Total Size" || echo ""
else
    echo "❌ Cannot access bucket: $BUCKET"
    echo ""
    echo "💡 POSSIBLE CAUSES:"
    echo "   1. Bucket doesn't exist in this AWS account"
    echo "   2. IAM user lacks s3:ListBucket permission"
    echo "   3. Bucket is in different AWS account"
    echo ""
    echo "   Run: aws s3 ls"
    echo "   To see which buckets you CAN access"
    exit 1
fi

# Test write permission
echo ""
echo "✍️  Testing S3 Write Permission..."
TEST_KEY="test-$(date +%s).txt"
TEST_CONTENT="inDoc dual-write test"

if echo "$TEST_CONTENT" | aws s3 cp - "s3://$BUCKET/$TEST_KEY" &>/dev/null; then
    echo "✅ Can WRITE to bucket: $BUCKET"
    
    # Clean up test file
    aws s3 rm "s3://$BUCKET/$TEST_KEY" &>/dev/null
    echo "✅ Test file cleaned up"
else
    echo "❌ Cannot WRITE to bucket: $BUCKET"
    echo ""
    echo "💡 IAM user needs s3:PutObject permission"
    exit 1
fi

# Summary
echo ""
echo "========================================================================"
echo "✅ ALL CHECKS PASSED - DUAL-WRITE IS READY!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "  1. Update .env with validated credentials (if different)"
echo "  2. Restart backend: make stop && make local-e2e"
echo "  3. Upload seed data: conda run -n indoc python tools/migrate_seed_data_to_s3.py --yes"
echo ""

