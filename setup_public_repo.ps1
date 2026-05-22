# Script to initialize the public Stock-Yard-Public repository

Write-Host "🚀 Setting up public repository..." -ForegroundColor Cyan

# Create temp directory
$tempDir = "temp_public_repo"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}

# Clone public repo
Write-Host "📥 Cloning Stock-Yard-Public..." -ForegroundColor Yellow
git clone https://github.com/anuragsin17-sketch/Stock-Yard-Public.git $tempDir

# Copy files
Write-Host "📋 Copying files..." -ForegroundColor Yellow
Copy-Item "index.html" "$tempDir/"
Copy-Item "data.json" "$tempDir/"
Copy-Item "PUBLIC_REPO_README.md" "$tempDir/README.md"

# Navigate to public repo
Set-Location $tempDir

# Configure git
git config user.name "GitHub Action"
git config user.email "action@github.com"

# Add files
git add .
git commit -m "Initial setup: Add dashboard and data files

- Added index.html (Stock Yard dashboard)
- Added data.json (screening results)
- Added README.md (public documentation)
- Ready for GitHub Pages deployment"

# Push
Write-Host "⬆️ Pushing to public repository..." -ForegroundColor Yellow
git push origin main

# Go back
Set-Location ..

# Clean up
Remove-Item -Recurse -Force $tempDir

Write-Host "✅ Public repository setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to: https://github.com/anuragsin17-sketch/Stock-Yard-Public/settings/pages"
Write-Host "2. Set Source to: Deploy from a branch"
Write-Host "3. Select branch: main / (root)"
Write-Host "4. Click Save"
Write-Host "5. Your site will be live at: https://anuragsin17-sketch.github.io/Stock-Yard-Public/"
