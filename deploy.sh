#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "=== Git Pull ==="
git pull origin master

echo ""
echo "=== 배포 대상 선택 ==="
echo "1) 백엔드만"
echo "2) 프론트엔드만"
echo "3) 둘 다"
read -p "선택 (1/2/3): " choice

# 백엔드 배포
deploy_backend() {
    echo ""
    echo "=== 백엔드 배포 시작 ==="
    cd back
    sam build
    sam deploy \
        --stack-name fridge-recipe-api \
        --resolve-s3 \
        --resolve-image-repos \
        --capabilities CAPABILITY_IAM \
        --region ap-northeast-2 \
        --no-confirm-changeset
    cd ..
    echo "✅ 백엔드 배포 완료"
}

# 프론트엔드 배포
deploy_frontend() {
    echo ""
    echo "=== 프론트엔드 배포 시작 ==="
    cd front
    vercel --prod --yes
    cd ..
    echo "✅ 프론트엔드 배포 완료"
}

case $choice in
    1) deploy_backend ;;
    2) deploy_frontend ;;
    3) deploy_backend && deploy_frontend ;;
    *) echo "잘못된 선택"; exit 1 ;;
esac

echo ""
echo "=== 배포 완료 ==="
echo "백엔드: https://764h9o2e6j.execute-api.ap-northeast-2.amazonaws.com"
echo "프론트: https://front-vert-nine.vercel.app"
