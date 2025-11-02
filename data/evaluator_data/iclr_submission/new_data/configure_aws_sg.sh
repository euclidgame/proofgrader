#!/bin/bash

# Script to configure AWS Security Group via CLI

echo "🔧 AWS Security Group Configuration Helper"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found"
    echo ""
    echo "Please configure the Security Group via AWS Console:"
    echo "https://console.aws.amazon.com/ec2/"
    echo ""
    exit 1
fi

# Get instance ID
echo "📍 Detecting instance information..."
INSTANCE_ID=$(ec2-metadata --instance-id 2>/dev/null | cut -d " " -f 2)

if [ -z "$INSTANCE_ID" ]; then
    echo "⚠️  Could not auto-detect instance ID"
    echo ""
    echo "Please run manually:"
    echo ""
    echo "# Get your instance ID"
    echo "aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress]' --output table"
    echo ""
    echo "# Get security group for that instance"
    echo "aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text"
    echo ""
    echo "# Add rule to security group"
    echo "aws ec2 authorize-security-group-ingress \\"
    echo "    --group-id YOUR_SECURITY_GROUP_ID \\"
    echo "    --protocol tcp \\"
    echo "    --port 7860 \\"
    echo "    --cidr 0.0.0.0/0 \\"
    echo "    --group-name 'Gradio Math Viewer'"
    echo ""
    exit 1
fi

echo "✅ Instance ID: $INSTANCE_ID"

# Get security group ID
SG_ID=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text 2>/dev/null)

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    echo "❌ Could not get Security Group ID"
    echo ""
    echo "Please use AWS Console instead:"
    echo "https://console.aws.amazon.com/ec2/"
    exit 1
fi

echo "✅ Security Group ID: $SG_ID"
echo ""

# Check if rule already exists
echo "🔍 Checking existing rules..."
EXISTING_RULE=$(aws ec2 describe-security-groups --group-ids "$SG_ID" --query "SecurityGroups[0].IpPermissions[?FromPort==\`7860\`]" --output text)

if [ -n "$EXISTING_RULE" ]; then
    echo "✅ Port 7860 rule already exists!"
    echo ""
    aws ec2 describe-security-groups --group-ids "$SG_ID" --query "SecurityGroups[0].IpPermissions[?FromPort==\`7860\`]" --output table
    echo ""
    echo "If you still can't connect, check that the source is 0.0.0.0/0"
    exit 0
fi

# Add the rule
echo "➕ Adding port 7860 to Security Group..."
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 7860 \
    --cidr 0.0.0.0/0 \
    --tag-specifications "ResourceType=security-group-rule,Tags=[{Key=Name,Value=Gradio Math Viewer}]" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Security Group rule added successfully!"
    echo ""
    echo "🎉 You should now be able to access:"
    echo "   http://$(curl -s ifconfig.me):7860"
    echo ""
else
    echo "❌ Failed to add rule (insufficient permissions?)"
    echo ""
    echo "Please use AWS Console instead:"
    echo "https://console.aws.amazon.com/ec2/"
    echo ""
fi

