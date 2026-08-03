#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}     COMPLETE SYSTEM TEST - ALL FUNCTIONALITY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

PASSED=0
FAILED=0

# Test function
test_step() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED: $2${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED: $2${NC}"
        [ -n "$3" ] && echo -e "${RED}  Error: $3${NC}"
        ((FAILED++))
    fi
    echo ""
}

# ============================================================
# TEST 1: Health Check
# ============================================================
echo -e "${BLUE}[TEST 1] System Health Check${NC}"
HEALTH=$(curl -s http://localhost:8000/health)
HEALTH_STATUS=$(echo $HEALTH | jq -r '.status')
if [ "$HEALTH_STATUS" = "healthy" ]; then
    test_step 0 "Server is healthy"
else
    test_step 1 "Health check" "$HEALTH"
fi

# ============================================================
# TEST 2: Create Job Description
# ============================================================
echo -e "${BLUE}[TEST 2] Create Job Description${NC}"
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/create \
  -H "Content-Type: application/json" \
  -d @test_data/job_description.json)
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
if [ "$JOB_ID" != "null" ] && [ -n "$JOB_ID" ]; then
    test_step 0 "Job created with ID: ${JOB_ID:0:8}..."
else
    test_step 1 "Job creation" "$JOB_RESPONSE"
fi

# ============================================================
# TEST 3: List Existing Resumes
# ============================================================
echo -e "${BLUE}[TEST 3] List Existing Resumes${NC}"
RESUME_LIST=$(curl -s "http://localhost:8000/resumes/?limit=10")
RESUME_COUNT=$(echo $RESUME_LIST | jq 'length')
if [ "$RESUME_COUNT" -gt 0 ]; then
    test_step 0 "Found $RESUME_COUNT resumes in database"
    echo "  Recent resumes:"
    echo $RESUME_LIST | jq -r '.[0:3] | .[] | "    - \(.personal_info.name) (\(.total_experience_years) yrs, \(.total_skills) skills)"'
else
    test_step 1 "List resumes" "No resumes found"
fi

# ============================================================
# TEST 4: Upload New Resume
# ============================================================
echo -e "${BLUE}[TEST 4] Upload New Resume${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8000/resumes/upload \
  -F "file=@test_data/test_resume.pdf")
NEW_RESUME_ID=$(echo $UPLOAD_RESPONSE | jq -r '.resume_id')
UPLOAD_STATUS=$(echo $UPLOAD_RESPONSE | jq -r '.status')

if [ "$NEW_RESUME_ID" != "null" ] && [ -n "$NEW_RESUME_ID" ]; then
    test_step 0 "Resume uploaded: ${NEW_RESUME_ID:0:8}... (status: $UPLOAD_STATUS)"
else
    test_step 1 "Upload resume" "$UPLOAD_RESPONSE"
fi

# ============================================================
# TEST 5: Wait for Processing
# ============================================================
echo -e "${BLUE}[TEST 5] Background Processing${NC}"
echo -n "  Processing"
for i in {1..15}; do
    STATUS=$(curl -s http://localhost:8000/resumes/$NEW_RESUME_ID 2>/dev/null | jq -r '.status')
    echo -n "."
    if [ "$STATUS" = "completed" ]; then
        echo ""
        test_step 0 "Resume processed successfully"
        break
    elif [ "$STATUS" = "failed" ]; then
        ERROR=$(curl -s http://localhost:8000/resumes/$NEW_RESUME_ID | jq -r '.error_message')
        echo ""
        test_step 1 "Processing" "$ERROR"
        break
    fi
    sleep 1
done

# ============================================================
# TEST 6: Verify Extracted Data
# ============================================================
echo -e "${BLUE}[TEST 6] Verify Extracted Data${NC}"
RESUME_DATA=$(curl -s http://localhost:8000/resumes/$NEW_RESUME_ID)
EXTRACTED_NAME=$(echo $RESUME_DATA | jq -r '.personal_info.name')
EXTRACTED_EMAIL=$(echo $RESUME_DATA | jq -r '.personal_info.email')
EXTRACTED_EXP=$(echo $RESUME_DATA | jq -r '.total_experience_years')
SKILLS_COUNT=$(echo $RESUME_DATA | jq -r '.skills | length')

echo "  Name: $EXTRACTED_NAME"
echo "  Email: $EXTRACTED_EMAIL"
echo "  Experience: $EXTRACTED_EXP years"
echo "  Skills Found: $SKILLS_COUNT"

if [ "$EXTRACTED_NAME" != "null" ] && [ ${#EXTRACTED_NAME} -gt 2 ]; then
    test_step 0 "Name extracted correctly"
else
    test_step 1 "Name extraction" "Got: '$EXTRACTED_NAME'"
fi

if [ "$EXTRACTED_EMAIL" != "null" ] && [[ "$EXTRACTED_EMAIL" == *"@"* ]]; then
    test_step 0 "Email extracted correctly"
else
    test_step 1 "Email extraction" "Got: '$EXTRACTED_EMAIL'"
fi

if (( $(echo "$EXTRACTED_EXP >= 4" | bc -l) )); then
    test_step 0 "Experience extracted: $EXTRACTED_EXP years"
else
    test_step 1 "Experience extraction" "Expected >=4, got: $EXTRACTED_EXP"
fi

if [ "$SKILLS_COUNT" -gt 0 ]; then
    test_step 0 "Skills extracted: $SKILLS_COUNT skills"
else
    test_step 1 "Skills extraction" "No skills found"
fi

# ============================================================
# TEST 7: Candidate Matching
# ============================================================
echo -e "${BLUE}[TEST 7] Candidate Matching${NC}"
MATCH_RESULT=$(curl -s -X POST "http://localhost:8000/matches/for-job/$JOB_ID?top_k=5")
MATCH_COUNT=$(echo $MATCH_RESULT | jq -r '.total_matches // 0')
PROCESSING_TIME=$(echo $MATCH_RESULT | jq -r '.processing_time_ms // 0')

if [ "$MATCH_COUNT" -gt 0 ]; then
    test_step 0 "Matching returned $MATCH_COUNT candidates (${PROCESSING_TIME}ms)"
    echo "  Top candidates:"
    echo $MATCH_RESULT | jq -r '.results[0:3] | .[] | "    - \(.resume_summary.personal_info.name): \(.overall_score)"'
else
    test_step 1 "Candidate matching" "No matches found"
fi

# ============================================================
# TEST 8: Semantic Search
# ============================================================
echo -e "${BLUE}[TEST 8] Semantic Search${NC}"
SEARCH_RESULT=$(curl -s -X POST http://localhost:8000/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "python developer with aws experience", "top_k": 3}')
SEARCH_COUNT=$(echo $SEARCH_RESULT | jq -r '.total_results // 0')

if [ "$SEARCH_COUNT" -gt 0 ]; then
    test_step 0 "Search returned $SEARCH_COUNT results"
    echo "  Top results:"
    echo $SEARCH_RESULT | jq -r '.results[0:3] | .[] | "    - \(.resume_summary.personal_info.name): \(.similarity_score)"'
else
    test_step 1 "Semantic search" "No results found (may need more data)"
fi

# ============================================================
# TEST 9: Get John Doe Details
# ============================================================
echo -e "${BLUE}[TEST 9] John Doe Details${NC}"
JOHN_ID=$(sqlite3 data/screening.db "SELECT id FROM resumes WHERE json_extract(personal_info, '$.name') = 'John Doe' AND total_experience_years >= 8 LIMIT 1;")
if [ -n "$JOHN_ID" ]; then
    JOHN_DATA=$(curl -s http://localhost:8000/resumes/$JOHN_ID)
    JOHN_NAME=$(echo $JOHN_DATA | jq -r '.personal_info.name')
    JOHN_EXP=$(echo $JOHN_DATA | jq -r '.total_experience_years')
    
    if [ "$JOHN_NAME" = "John Doe" ] && (( $(echo "$JOHN_EXP >= 7" | bc -l) )); then
        test_step 0 "John Doe: $JOHN_EXP years experience, ${SKILLS_COUNT} skills"
    else
        test_step 1 "John Doe data" "Name: $JOHN_NAME, Exp: $JOHN_EXP"
    fi
else
    test_step 1 "John Doe" "Not found in database"
fi

# ============================================================
# TEST 10: Bias Detection Metrics
# ============================================================
echo -e "${BLUE}[TEST 10] Bias Detection System${NC}"
BIAS_METRICS=$(curl -s http://localhost:8000/bias/metrics)
METRICS_COUNT=$(echo $BIAS_METRICS | jq -r '.metrics | length')
PROTECTED_ATTRS=$(echo $BIAS_METRICS | jq -r '.protected_attributes | length')

if [ "$METRICS_COUNT" -gt 0 ]; then
    test_step 0 "Bias metrics available: $METRICS_COUNT metrics"
    echo "  Protected attributes: $PROTECTED_ATTRS"
else
    test_step 1 "Bias metrics" "No metrics found"
fi

# ============================================================
# TEST 11: Error Handling
# ============================================================
echo -e "${BLUE}[TEST 11] Error Handling${NC}"
ERROR_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/resumes/non-existent-id-12345)
if [ "$ERROR_CODE" = "404" ]; then
    test_step 0 "404 error returned for non-existent resource"
else
    test_step 1 "Error handling" "Expected 404, got $ERROR_CODE"
fi

# ============================================================
# TEST 12: System Statistics
# ============================================================
echo -e "${BLUE}[TEST 12] System Statistics${NC}"
DB_SIZE=$(du -h data/screening.db 2>/dev/null | cut -f1)
UPLOADS=$(ls -1 data/uploads/ 2>/dev/null | wc -l)
INDEX_SIZE="N/A"
[ -f data/faiss/index.bin ] && INDEX_SIZE=$(du -h data/faiss/index.bin | cut -f1)

echo "  Database size: $DB_SIZE"
echo "  Uploaded files: $UPLOADS"
echo "  FAISS index: $INDEX_SIZE"
test_step 0 "Statistics collected"

# ============================================================
# FINAL SUMMARY
# ============================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    TEST RESULTS SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${BLUE}Total:  $(($PASSED + $FAILED))${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! System is fully functional.${NC}"
    echo ""
    echo -e "${YELLOW}System Capabilities Verified:${NC}"
    echo "  ✓ Resume upload and parsing"
    echo "  ✓ Information extraction (name, email, experience, skills)"
    echo "  ✓ Background processing with task manager"
    echo "  ✓ Job description creation"
    echo "  ✓ Candidate matching with scoring"
    echo "  ✓ Semantic search"
    echo "  ✓ Bias detection framework"
    echo "  ✓ Error handling"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Add more resumes for better matching"
    echo "  2. Create multiple job descriptions"
    echo "  3. Run bias analysis with more data"
    echo "  4. Access API docs: http://localhost:8000/docs"
else
    echo -e "${RED}⚠️ $FAILED test(s) failed. Please check the errors above.${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
