$ErrorActionPreference = 'Continue'

# Get token from git credential manager at runtime
$TOKEN = ""
$cred = "protocol=https`nhost=github.com`n" | git credential fill 2>$null
if ($cred) {
    $matched = $cred | Select-String "password=(.+)"
    if ($matched) { $TOKEN = $matched.Matches.Groups[1].Value }
}
if (-not $TOKEN) { Write-Host "ERROR: No GitHub token found. Run 'git push' first to authenticate."; exit 1 }

$REPO = "rambochai7750973-hash/snakegame"
$HEADERS = @{ Authorization = "Bearer $TOKEN"; Accept = "application/vnd.github.v3+json" }
$API_BASE = "https://api.github.com"

function Invoke-GHAPI {
    param($Uri)
    try { return Invoke-RestMethod -Uri $Uri -Headers $HEADERS -ErrorAction Stop } catch { return $null }
}

function Wait-ForWorkflowRun {
    param($RunId)
    $maxWait = 600  # 10 min max
    $waited = 0
    while ($waited -lt $maxWait) {
        $run = Invoke-GHAPI "$API_BASE/repos/$REPO/actions/runs/$RunId"
        if (-not $run) { return $null }
        if ($run.status -eq "completed") { return $run }
        Write-Host "   Status: $($run.status)... waiting 15s"
        Start-Sleep -Seconds 15
        $waited += 15
    }
    return $null
}

function Get-LatestRun {
    $runs = Invoke-GHAPI "$API_BASE/repos/$REPO/actions/runs?branch=master&per_page=5"
    if (-not $runs -or -not $runs.workflow_runs) { return $null }
    return $runs.workflow_runs[0]
}

function Download-Logs {
    param($RunId)
    $dir = Join-Path $PSScriptRoot "build_logs"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $logPath = Join-Path $dir "build_$RunId.log"

    # Get the log download URL
    $logs = Invoke-GHAPI "$API_BASE/repos/$REPO/actions/runs/$RunId/logs"
    if (-not $logs) { return $null }

    $zipPath = Join-Path $dir "logs_$RunId.zip"
    $url = "$API_BASE/repos/$REPO/actions/runs/$RunId/logs"
    try {
        Invoke-RestMethod -Uri $url -Headers $HEADERS -OutFile $zipPath -ErrorAction Stop
        Expand-Archive -Path $zipPath -DestinationPath (Join-Path $dir "extracted_$RunId") -Force
        # Find the main build log
        $extracted = Join-Path $dir "extracted_$RunId"
        $logs = Get-ChildItem -Path $extracted -Recurse -File | Where-Object { $_.Name -match 'build' -or $_.Extension -eq '.txt' }
        if ($logs) {
            Get-Content -Path $logs[0].FullName | Out-File -FilePath $logPath -Encoding utf8
            return $logPath
        }
        # Also try artifact download
        $artifacts = Invoke-GHAPI "$API_BASE/repos/$REPO/actions/runs/$RunId/artifacts"
        if ($artifacts -and $artifacts.artifacts) {
            foreach ($art in $artifacts.artifacts) {
                if ($art.name -match 'build-log') {
                    $dlUrl = "$API_BASE/repos/$REPO/actions/artifacts/$($art.id)/zip"
                    $artZip = Join-Path $dir "artifact_$($art.id).zip"
                    Invoke-RestMethod -Uri $dlUrl -Headers $HEADERS -OutFile $artZip -ErrorAction Stop
                    Expand-Archive -Path $artZip -DestinationPath (Join-Path $dir "artifact_$($art.id)") -Force
                    $artLogs = Get-ChildItem -Path (Join-Path $dir "artifact_$($art.id)") -Recurse -File
                    if ($artLogs) {
                        Get-Content -Path $artLogs[0].FullName | Out-File -FilePath $logPath -Encoding utf8
                        return $logPath
                    }
                }
            }
        }
        return $null
    } catch {
        Write-Host "   Error downloading logs: $_"
        return $null
    }
}

function Analyze-Error($logPath) {
    if (-not (Test-Path $logPath)) { return $null }
    $log = Get-Content -Path $logPath -Raw

    # Check for success - APK artifact size > 0 means .apk was uploaded
    if ($log -match "BUILD SUCCESSFUL" -or $log -match "APK built successfully" -or $log -match "Artifact snakegame-apk.zip successfully finalized") {
        return @{ type = "success" }
    }

    # Check for pipefail/SIGPIPE issue (build succeeded but step failed due to yes + pipefail)
    if ($log -match "# Android packaging done!" -and $log -match "Artifact snakegame-apk") {
        # Build actually succeeded, just exit code issue
        return @{ type = "success" }
    }

    # Check for empty gradle dependency
    if ($log -match "Supplied String module notation '' is invalid") {
        return @{
            type = "empty_gradle_dep"
            desc = "Empty gradle dependency string"
            fix  = "buildozer.spec"
        }
    }

    # Check for project.properties missing target
    if ($log -match "Project target: android-\d+ not found" -or $log -match "Unable to resolve target") {
        return @{
            type = "project_properties"
            desc = "Missing or wrong target in project.properties"
            fix  = "hook.py"
        }
    }

    # Check for permission denied
    if ($log -match "Permission denied") {
        return @{ type = "permission"; desc = "Permission issue"; fix = "unknown" }
    }

    # Check for aapt errors
    if ($log -match "aapt" -and $log -match "error") {
        return @{ type = "aapt"; desc = "AAPT error"; fix = "unknown" }
    }

    # Generic error detection
    if ($log -match "(?i)error|FAILED|Exception|failed") {
        return @{ type = "generic"; desc = "Unknown error in log"; fix = "unknown" }
    }

    return $null
}

function Apply-Fix($errorInfo) {
    $specPath = Join-Path $PSScriptRoot "buildozer.spec"

    if ($errorInfo.type -eq "empty_gradle_dep") {
        Write-Host "   FIX: Removing android.gradle_dependencies line..."
        $content = Get-Content -Path $specPath -Raw
        $content = $content -replace '(?m)^android\.gradle_dependencies\s*=.*\n?', ''
        # Add commented version
        $content = $content -replace '(?m)^(# )?android\.allow_backup', '# android.gradle_dependencies = androidx.legacy:legacy-support-v4:1.0.0`nandroid.allow_backup'
        Set-Content -Path $specPath -Value $content -Encoding utf8 -NoNewline
        return $true
    }

    return $false
}

# Main loop
$maxAttempts = 10
$attempt = 1

while ($attempt -le $maxAttempts) {
    Write-Host "`n=== AUTO BUILD ATTEMPT $attempt/$maxAttempts ==="

    # 1. Push current code
    Write-Host "[1/4] Pushing to GitHub..."
    $pushResult = git push origin master 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Push failed: $pushResult"
        Write-Host "   Checking if code is already up to date..."
        git pull origin master 2>&1 | Out-Null
    } else {
        Write-Host "   Push OK"
    }

    # 2. Wait for workflow to start + complete
    Write-Host "[2/4] Waiting for workflow to trigger..."
    Start-Sleep -Seconds 20  # Give GitHub a moment

    $run = Get-LatestRun
    if (-not $run) {
        Write-Host "   No runs found, retrying..."
        Start-Sleep -Seconds 15
        $run = Get-LatestRun
        if (-not $run) {
            Write-Host "   Still no runs. Aborting."
            break
        }
    }

    Write-Host "   Run #$($run.id) - status: $($run.status)"
    if ($run.status -ne "completed") {
        Write-Host "   Waiting for run to complete..."
        $run = Wait-ForWorkflowRun -RunId $run.id
        if (-not $run) {
            Write-Host "   Timed out waiting for run."
            break
        }
    }
    Write-Host "   Conclusion: $($run.conclusion)"

    # 3. Download logs
    Write-Host "[3/4] Downloading build logs..."
    $logPath = Download-Logs -RunId $run.id
    if (-not $logPath) {
        Write-Host "   Could not download logs. Trying to get run logs directly via zip..."
        # Try alternative approach: download logs zip
        $logDir = Join-Path $PSScriptRoot "build_logs"
        $zipPath = Join-Path $logDir "raw_logs_$($run.id).zip"
        try {
            Invoke-WebRequest -Uri "$API_BASE/repos/$REPO/actions/runs/$($run.id)/logs" -Headers $HEADERS -OutFile $zipPath -ErrorAction Stop
            Expand-Archive -Path $zipPath -DestinationPath (Join-Path $logDir "raw_$($run.id)") -Force
            $found = Get-ChildItem -Path (Join-Path $logDir "raw_$($run.id)") -Recurse | Where-Object { $_.Length -gt 100 } | Sort-Object Length -Descending
            if ($found) {
                $logPath = Join-Path $logDir "build_$($run.id).log"
                Get-Content -Path $found[0].FullName | Out-File -FilePath $logPath -Encoding utf8
                Write-Host "   Downloaded log: $($found[0].Name) ($($found[0].Length) bytes)"
            }
        } catch {
            Write-Host "   Failed to download: $_"
        }
        if (-not $logPath) {
            Write-Host "   Cannot proceed without logs."
            break
        }
    }
    Write-Host "   Log saved to $logPath"

    # 4. Analyze
    Write-Host "[4/4] Analyzing build output..."
    $errorInfo = Analyze-Error -logPath $logPath

    if (-not $errorInfo) {
        Write-Host "   Could not parse build output (no clear error/success marker found)."
        # Show last 30 lines of log
        Write-Host "   Last 30 lines of log:"
        Get-Content -Path $logPath -Tail 30 | ForEach-Object { Write-Host "     $_" }
        Write-Host "   Manual intervention needed. Aborting."
        break
    }

    if ($errorInfo.type -eq "success") {
        Write-Host "`n=========================================="
        Write-Host "  BUILD SUCCESSFUL! APK is ready!"
        Write-Host "=========================================="
        Write-Host "   Run #$($run.id)"
        Write-Host "   Conclusion: $($run.conclusion)"
        break
    }

    Write-Host "   Error detected: $($errorInfo.desc)"
    Write-Host "   Applying fix..."

    $fixed = Apply-Fix -errorInfo $errorInfo
    if (-not $fixed) {
        Write-Host "   Cannot auto-fix: $($errorInfo.desc)"
        Write-Host "   Log path: $logPath"
        Write-Host "   Needs manual intervention."
        break
    }

    Write-Host "   Fix applied. Will retry..."
    $attempt++
    Start-Sleep -Seconds 5
}
