#!/bin/bash
# Quick demo/test script for auto-summarization feature

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Safe Journalist Auto-Summarization Demo ===${NC}\n"

# Setup
DEMO_DIR="./demo-data"
BASE_URL="http://localhost:8000"

echo -e "${YELLOW}Step 1: Clearing demo data directory${NC}"
rm -rf "$DEMO_DIR"
mkdir -p "$DEMO_DIR"
echo -e "${GREEN}✓ Demo directory ready${NC}\n"

echo -e "${YELLOW}Step 2: Check initial status${NC}"
curl -s "$BASE_URL/status" | python3 -m json.tool
echo -e "\n"

echo -e "${YELLOW}Step 3: Creating Entry 1${NC}"
curl -s -X POST "$BASE_URL/entries" \
  -H "Content-Type: application/json" \
  -d '{"text":"Arrived at protest site. Crowd estimated 200+ people. Police presence minimal."}'
echo -e "\n${GREEN}✓ Entry 1 created${NC}\n"

echo -e "${YELLOW}Step 4: Creating Entry 2${NC}"
curl -s -X POST "$BASE_URL/entries" \
  -H "Content-Type: application/json" \
  -d '{"text":"Tension rising. Police reinforcements arriving. Crowd chanting loudly."}'
echo -e "\n${GREEN}✓ Entry 2 created${NC}\n"

echo -e "${YELLOW}Step 5: Check status (should show 2 entries, 0 summaries)${NC}"
curl -s "$BASE_URL/status" | python3 -m json.tool
echo -e "\n"

echo -e "${YELLOW}Step 6: Creating Entry 3 (SHOULD TRIGGER SUMMARIZATION!)${NC}"
curl -s -X POST "$BASE_URL/entries" \
  -H "Content-Type: application/json" \
  -d '{"text":"Police using tear gas. Situation escalating. Moving to safe location."}'
echo -e "\n${GREEN}✓ Entry 3 created - summarization should trigger!${NC}\n"

echo -e "${YELLOW}Step 7: Wait for background summarization to complete${NC}"
sleep 3
echo -e "${GREEN}✓ Waited 3 seconds${NC}\n"

echo -e "${YELLOW}Step 8: Check final status${NC}"
curl -s "$BASE_URL/status" | python3 -m json.tool
echo -e "\n"

echo -e "${YELLOW}Step 9: Show created files${NC}"
echo "Entries:"
ls -lh "$DEMO_DIR/entries/" 2>/dev/null || echo "No entries directory"
echo ""
echo "Summaries:"
ls -lh "$DEMO_DIR/summaries/" 2>/dev/null || echo "No summaries directory"
echo ""

if [ -d "$DEMO_DIR/summaries" ]; then
    echo -e "${YELLOW}Step 10: Display AI-generated summary${NC}"
    echo -e "${BLUE}================================${NC}"
    cat "$DEMO_DIR/summaries/"*.md 2>/dev/null || echo "No summaries found"
    echo -e "${BLUE}================================${NC}\n"
    echo -e "${GREEN}✓ Demo completed successfully!${NC}"
else
    echo -e "${YELLOW}⚠ No summary was generated. Check if MAPLE_API_KEY is set and server logs for errors.${NC}"
fi
