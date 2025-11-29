# File: fix_timestamp_references.ps1
# PowerShell script to automatically fix all timestamp references

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "FIXING STRESSLEVEL TIMESTAMP REFERENCES" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------
# File 1: analytics/calculators.py
# ---------------------------------------------------------
Write-Host "[1/3] Fixing analytics/calculators.py..." -ForegroundColor Green
$file1 = "analytics\calculators.py"

if (Test-Path $file1) {
    $content = Get-Content $file1 -Raw
    $content = $content -replace '\.latest\(''timestamp''\)', ".latest('calculated_at')"
    Set-Content $file1 -Value $content
    Write-Host "  [OK] Fixed .latest('timestamp')" -ForegroundColor Green
}
else {
    Write-Host "  [ERR] File not found!" -ForegroundColor Red
}

# ---------------------------------------------------------
# File 2: analytics/views.py
# ---------------------------------------------------------
Write-Host "[2/3] Fixing analytics/views.py..." -ForegroundColor Green
$file2 = "analytics\views.py"

if (Test-Path $file2) {
    $content = Get-Content $file2 -Raw
    $content = $content -replace '\.order_by\(''-timestamp''\)', ".order_by('-calculated_at')"
    Set-Content $file2 -Value $content
    Write-Host "  [OK] Fixed .order_by('-timestamp')" -ForegroundColor Green
}
else {
    Write-Host "  [ERR] File not found!" -ForegroundColor Red
}

# ---------------------------------------------------------
# File 3: dashboard/views.py
# ---------------------------------------------------------
Write-Host "[3/3] Fixing dashboard/views.py..." -ForegroundColor Green
$file3 = "dashboard\views.py"

if (Test-Path $file3) {
    $content = Get-Content $file3 -Raw
    $content = $content -replace '\.order_by\(''-timestamp''\)', ".order_by('-calculated_at')"
    Set-Content $file3 -Value $content
    Write-Host "  [OK] Fixed .order_by('-timestamp')" -ForegroundColor Green
}
else {
    Write-Host "  [ERR] File not found!" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "ALL FIXES APPLIED!" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify changes: git diff (if using git)" -ForegroundColor White
Write-Host "  2. Run server: python manage.py runserver" -ForegroundColor White
Write-Host "  3. Test: Visit /dashboard/student/" -ForegroundColor White
Write-Host ""
