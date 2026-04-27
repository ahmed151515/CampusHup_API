################################################################################
#  CampusHub – Contents API Live Test
#  Run from the backend directory:
#     .\venv\Scripts\Activate.ps1  (optional)
#     .\test_contents_api.ps1
#
#  Pre-requisites:
#    - Server running:  python manage.py runserver --settings=config.settings.dev
#    - Seeded DB (seed command already run)
#    - Student 2022030001 enrolled in CS50 (done via shell above)
################################################################################

$BASE      = "http://127.0.0.1:8000/api/v1"
$COURSE    = "CS50"
$PASS = 0
$FAIL = 0

# ── colours ──────────────────────────────────────────────────────────────────
function Green($msg) { Write-Host $msg -ForegroundColor Green }
function Red($msg)   { Write-Host $msg -ForegroundColor Red }
function Cyan($msg)  { Write-Host $msg -ForegroundColor Cyan }
function Yellow($msg){ Write-Host $msg -ForegroundColor Yellow }

function Check($label, $got, $want) {
    if ($got -eq $want) {
        Green  "  PASS  $label  →  $got"
        $script:PASS++
    } else {
        Red    "  FAIL  $label  →  got $got, expected $want"
        $script:FAIL++
    }
}

# ── HTTP helpers ──────────────────────────────────────────────────────────────
function Invoke-Api($method, $url, $body=$null, $token=$null, $multipart=$false) {
    $headers = @{ "Accept" = "application/json" }
    if ($token) { $headers["Authorization"] = "Bearer $token" }

    try {
        if ($multipart) {
            # body is already a System.Net.Http.MultipartFormDataContent
            $resp = Invoke-WebRequest -Uri $url -Method $method `
                        -Headers $headers -Body $body `
                        -ContentType $body.Headers.ContentType.ToString() `
                        -ErrorAction Stop
            return [PSCustomObject]@{
                StatusCode = $resp.StatusCode
                Data       = $resp.Content | ConvertFrom-Json
            }
        } elseif ($body) {
            $resp = Invoke-RestMethod -Uri $url -Method $method `
                        -Headers $headers -Body ($body | ConvertTo-Json) `
                        -ContentType "application/json" -ErrorAction Stop
            return [PSCustomObject]@{ StatusCode = 200; Data = $resp }
        } else {
            $resp = Invoke-RestMethod -Uri $url -Method $method `
                        -Headers $headers -ErrorAction Stop
            return [PSCustomObject]@{ StatusCode = 200; Data = $resp }
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        $raw  = $null
        try {
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = [System.IO.StreamReader]::new($stream)
            $raw = $reader.ReadToEnd() | ConvertFrom-Json
        } catch {}
        return [PSCustomObject]@{ StatusCode = $code; Data = $raw }
    }
}

function Get-Token($collegeId, $password) {
    $r = Invoke-Api POST "$BASE/auth/login/" @{ college_id=$collegeId; password=$password }
    if ($r.Data.access) { return $r.Data.access }
    Red "  Could not get token for $collegeId"
    return $null
}

# Build a minimal valid PDF as bytes
function New-MinimalPdfBytes {
    $pdf = "%PDF-1.4`n" +
           "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj`n" +
           "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj`n" +
           "3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj`n" +
           "xref`n0 4`n" +
           "0000000000 65535 f `n" +
           "0000000009 00000 n `n" +
           "0000000058 00000 n `n" +
           "0000000115 00000 n `n" +
           "trailer<</Size 4/Root 1 0 R>>`n" +
           "startxref`n190`n%%EOF"
    return [System.Text.Encoding]::ASCII.GetBytes($pdf)
}

function New-Multipart($title, $filename, $bytes, $contentType="application/pdf") {
    Add-Type -AssemblyName System.Net.Http
    $mp   = [System.Net.Http.MultipartFormDataContent]::new()
    $sc   = [System.Net.Http.StringContent]::new($title)
    $mp.Add($sc, "title")
    $bc   = [System.Net.Http.ByteArrayContent]::new($bytes)
    $bc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new($contentType)
    $mp.Add($bc, "file", $filename)
    return $mp
}

################################################################################
Cyan "`n══════════════════════════════════════════════════════"
Cyan "  CampusHub · Contents API · Live Endpoint Tests"
Cyan "══════════════════════════════════════════════════════`n"

# ── STEP 1: Obtain tokens ─────────────────────────────────────────────────────
Cyan "[ STEP 1 ]  Obtain JWT tokens"

$facultyToken  = Get-Token "dr001"       "dr001"
$studentToken  = Get-Token "2022030001"  "2022030001"

if (-not $facultyToken)  { Red "Cannot continue without faculty token.";  exit 1 }
if (-not $studentToken)  { Red "Cannot continue without student token.";  exit 1 }

Green "  Faculty token obtained"
Green "  Student token obtained"

# ── STEP 2: POST – Faculty uploads a valid PDF → 201 ─────────────────────────
Cyan "`n[ STEP 2 ]  POST /$COURSE/contents/  as Faculty (valid PDF) → expect 201"

$pdfBytes = New-MinimalPdfBytes
$mp       = New-Multipart "Week 1 Lecture" "lecture1.pdf" $pdfBytes
$r2       = Invoke-Api POST "$BASE/$COURSE/contents/" -body $mp -token $facultyToken -multipart $true

Check "Upload valid PDF → 201" $r2.StatusCode 201

$materialId = $null
if ($r2.StatusCode -eq 201) {
    $materialId = $r2.Data.id
    Yellow "    Material ID: $materialId"
    Yellow "    type:        $($r2.Data.type)"
    Yellow "    size_bytes:  $($r2.Data.size_bytes)"
    Yellow "    course:      $($r2.Data.course)"
    Yellow "    uploaded_by: $($r2.Data.uploaded_by)"
    Check  "type field is 'pdf'"              $r2.Data.type          "pdf"
    Check  "size_bytes > 0"                   ($r2.Data.size_bytes -gt 0) $true
    Check  "course comes from URL (not body)" $r2.Data.course        $COURSE
}

# ── STEP 3: POST – Faculty uploads a .txt file → 400 ────────────────────────
Cyan "`n[ STEP 3 ]  POST /$COURSE/contents/  as Faculty (wrong extension .txt) → expect 400"

$txtBytes = [System.Text.Encoding]::UTF8.GetBytes("This is plain text, not a PDF.")
$mp3      = New-Multipart "Bad File" "notes.txt" $txtBytes "text/plain"
$r3       = Invoke-Api POST "$BASE/$COURSE/contents/" -body $mp3 -token $facultyToken -multipart $true

Check "Upload .txt → 400" $r3.StatusCode 400
if ($r3.Data.file) { Yellow "    Error: $($r3.Data.file)" }

# ── STEP 4: POST – Faculty uploads fake PDF (text renamed .pdf) → 400 ────────
Cyan "`n[ STEP 4 ]  POST /$COURSE/contents/  as Faculty (fake PDF – wrong MIME) → expect 400"

$fakeBytes = [System.Text.Encoding]::UTF8.GetBytes("I am pretending to be a PDF. %PDF-fake")
$mp4       = New-Multipart "Fake PDF" "fake.pdf" $fakeBytes "application/pdf"
$r4        = Invoke-Api POST "$BASE/$COURSE/contents/" -body $mp4 -token $facultyToken -multipart $true

Check "Upload fake PDF (MIME check) → 400" $r4.StatusCode 400
if ($r4.Data.file) { Yellow "    Error: $($r4.Data.file)" }

# ── STEP 5: POST – Student tries to upload → 403 ─────────────────────────────
Cyan "`n[ STEP 5 ]  POST /$COURSE/contents/  as Student → expect 403"

$mp5 = New-Multipart "Student Upload" "lecture.pdf" $pdfBytes
$r5  = Invoke-Api POST "$BASE/$COURSE/contents/" -body $mp5 -token $studentToken -multipart $true

Check "Student upload → 403" $r5.StatusCode 403

# ── STEP 6: POST – Unauthenticated → 401 ─────────────────────────────────────
Cyan "`n[ STEP 6 ]  POST /$COURSE/contents/  unauthenticated → expect 401"

$mp6 = New-Multipart "No Auth" "lecture.pdf" $pdfBytes
$r6  = Invoke-Api POST "$BASE/$COURSE/contents/" -body $mp6 -multipart $true

Check "Unauthenticated upload → 401" $r6.StatusCode 401

# ── STEP 7: GET list – Faculty → 403 ─────────────────────────────────────────
Cyan "`n[ STEP 7 ]  GET /$COURSE/contents/  as Faculty → expect 403"

$r7 = Invoke-Api GET "$BASE/$COURSE/contents/" -token $facultyToken
Check "Faculty list → 403" $r7.StatusCode 403

# ── STEP 8: GET list – Student (enrolled) → 200 ──────────────────────────────
Cyan "`n[ STEP 8 ]  GET /$COURSE/contents/  as Student (enrolled) → expect 200"

$r8 = Invoke-Api GET "$BASE/$COURSE/contents/" -token $studentToken
Check "Student list → 200" $r8.StatusCode 200
if ($r8.StatusCode -eq 200) {
    $items = if ($r8.Data -is [array]) { $r8.Data } elseif ($r8.Data.results) { $r8.Data.results } else { @() }
    Yellow "    Items returned: $($items.Count)"
    Check  "At least 1 material returned" ($items.Count -ge 1) $true
}

# ── STEP 9: GET list – Unauthenticated → 401 ─────────────────────────────────
Cyan "`n[ STEP 9 ]  GET /$COURSE/contents/  unauthenticated → expect 401"

$r9 = Invoke-Api GET "$BASE/$COURSE/contents/"
Check "Unauthenticated list → 401" $r9.StatusCode 401

# ── STEP 10: GET retrieve – Student → 200 (only if we have an id) ─────────────
Cyan "`n[ STEP 10 ]  GET /$COURSE/contents/$materialId/  as Student → expect 200"

if ($materialId) {
    $r10 = Invoke-Api GET "$BASE/$COURSE/contents/$materialId/" -token $studentToken
    Check "Student retrieve → 200"          $r10.StatusCode 200
    if ($r10.StatusCode -eq 200) {
        Check "id matches"    $r10.Data.id     $materialId
        Check "type is 'pdf'" $r10.Data.type   "pdf"
        Yellow "    title: $($r10.Data.title)"
    }
} else { Yellow "    SKIP (no material id from step 2)" }

# ── STEP 11: GET retrieve – Faculty → 403 ────────────────────────────────────
Cyan "`n[ STEP 11 ]  GET /$COURSE/contents/$materialId/  as Faculty → expect 403"

if ($materialId) {
    $r11 = Invoke-Api GET "$BASE/$COURSE/contents/$materialId/" -token $facultyToken
    Check "Faculty retrieve → 403" $r11.StatusCode 403
} else { Yellow "    SKIP" }

# ── STEP 12: PATCH – Faculty updates title → 200 ─────────────────────────────
Cyan "`n[ STEP 12 ]  PATCH /$COURSE/contents/$materialId/  as Faculty → expect 200"

if ($materialId) {
    $patchBody = '{"title":"Updated Week 1 Lecture"}'
    try {
        $headers12 = @{
            "Authorization" = "Bearer $facultyToken"
            "Content-Type"  = "application/json"
            "Accept"        = "application/json"
        }
        $r12raw = Invoke-WebRequest -Uri "$BASE/$COURSE/contents/$materialId/" `
                    -Method PATCH -Headers $headers12 -Body $patchBody -ErrorAction Stop
        $r12data = $r12raw.Content | ConvertFrom-Json
        Check "Faculty PATCH title → 200"      $r12raw.StatusCode 200
        Check "title updated"  $r12data.title  "Updated Week 1 Lecture"
        Yellow "    New title: $($r12data.title)"
    } catch {
        $code12 = $_.Exception.Response.StatusCode.value__
        Check "Faculty PATCH title → 200" $code12 200
    }
} else { Yellow "    SKIP" }

# ── STEP 13: PATCH – Student tries → 403 ─────────────────────────────────────
Cyan "`n[ STEP 13 ]  PATCH /$COURSE/contents/$materialId/  as Student → expect 403"

if ($materialId) {
    try {
        $headers13 = @{
            "Authorization" = "Bearer $studentToken"
            "Content-Type"  = "application/json"
        }
        $r13raw = Invoke-WebRequest -Uri "$BASE/$COURSE/contents/$materialId/" `
                    -Method PATCH -Headers $headers13 -Body '{"title":"Hacked"}' -ErrorAction Stop
        Check "Student PATCH → 403" $r13raw.StatusCode 403
    } catch {
        $code13 = $_.Exception.Response.StatusCode.value__
        Check "Student PATCH → 403" $code13 403
    }
} else { Yellow "    SKIP" }

# ── STEP 14: DELETE – Student tries → 403 ────────────────────────────────────
Cyan "`n[ STEP 14 ]  DELETE /$COURSE/contents/$materialId/  as Student → expect 403"

if ($materialId) {
    $r14 = Invoke-Api DELETE "$BASE/$COURSE/contents/$materialId/" -token $studentToken
    Check "Student DELETE → 403" $r14.StatusCode 403
} else { Yellow "    SKIP" }

# ── STEP 15: DELETE – Faculty deletes → 204 ──────────────────────────────────
Cyan "`n[ STEP 15 ]  DELETE /$COURSE/contents/$materialId/  as Faculty → expect 204"

if ($materialId) {
    $r15 = Invoke-Api DELETE "$BASE/$COURSE/contents/$materialId/" -token $facultyToken
    Check "Faculty DELETE → 204" $r15.StatusCode 204
} else { Yellow "    SKIP" }

# ── STEP 16: GET retrieve after delete → 404 ─────────────────────────────────
Cyan "`n[ STEP 16 ]  GET /$COURSE/contents/$materialId/  after DELETE → expect 404"

if ($materialId) {
    $r16 = Invoke-Api GET "$BASE/$COURSE/contents/$materialId/" -token $studentToken
    Check "Retrieve after delete → 404" $r16.StatusCode 404
} else { Yellow "    SKIP" }

# ── STEP 17: GET list after delete – count should be 0 ────────────────────────
Cyan "`n[ STEP 17 ]  GET /$COURSE/contents/  after DELETE → expect empty list"

$r17 = Invoke-Api GET "$BASE/$COURSE/contents/" -token $studentToken
if ($r17.StatusCode -eq 200) {
    $items17 = if ($r17.Data -is [array]) { $r17.Data } elseif ($r17.Data.results) { $r17.Data.results } else { @() }
    Check "List after delete → 0 items" $items17.Count 0
} else {
    Check "List after delete → 200" $r17.StatusCode 200
}

################################################################################
Cyan "`n══════════════════════════════════════════════════════"
Cyan "  RESULTS"
Cyan "══════════════════════════════════════════════════════"
$total = $PASS + $FAIL
Green "  Passed : $PASS / $total"
if ($FAIL -gt 0) { Red "  Failed : $FAIL / $total" } else { Green "  Failed : 0 / $total" }
Cyan "══════════════════════════════════════════════════════`n"

if ($FAIL -gt 0) { exit 1 } else { exit 0 }
