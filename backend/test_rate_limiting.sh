#!/bin/bash
# Test Rate Limiting on Authentication Endpoints

echo "🔒 Testing Rate Limiting - Login Endpoint (10 requests/minute limit)"
echo "================================================================"
echo ""

# Test login rate limiting
for i in {1..12}; do
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/login \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"test$i\", \"password\": \"wrong$i\"}")
  
  if [ "$http_code" = "429" ]; then
    echo "Request $i: HTTP $http_code ✓ RATE LIMITED (Expected after 10 requests)"
    echo ""
    echo "✅ Login Rate Limiting: WORKING"
    break
  elif [ "$http_code" = "401" ]; then
    echo "Request $i: HTTP $http_code - Failed login (expected)"
  else
    echo "Request $i: HTTP $http_code - Unexpected response"
  fi
done

echo ""
echo "🔒 Testing Rate Limiting - Register Endpoint (5 requests/minute limit)"
echo "====================================================================="
echo ""

# Test register rate limiting
for i in {1..7}; do
  http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/register \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"newuser$i\", \"email\": \"test$i@example.com\", \"password\": \"Test123!@#\", \"full_name\": \"Test User $i\"}")
  
  if [ "$http_code" = "429" ]; then
    echo "Request $i: HTTP $http_code ✓ RATE LIMITED (Expected after 5 requests)"
    echo ""
    echo "✅ Register Rate Limiting: WORKING"
    break
  elif [ "$http_code" = "200" ] || [ "$http_code" = "400" ]; then
    echo "Request $i: HTTP $http_code - Registration processed"
  else
    echo "Request $i: HTTP $http_code - Response"
  fi
done

echo ""
echo "📊 Rate Limiting Test Summary"
echo "=============================="
echo "Login endpoint: 10 requests/minute - TESTED"
echo "Register endpoint: 5 requests/minute - TESTED"
