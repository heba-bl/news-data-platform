# Screenshot automatique des interfaces
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screenshotDir = "C:\Users\ayman\CascadeProjects\news-data-platform\docs\screenshots"
New-Item -ItemType Directory -Force -Path $screenshotDir | Out-Null

$browserPath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

function Take-Screenshot($filename) {
    Start-Sleep -Seconds 6
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
    $path = "$screenshotDir\$filename"
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose()
    Write-Host "  Screenshot sauvegarde : $filename" -ForegroundColor Green
}

$pages = @(
    @{ url="http://localhost:3001/d/news-complete/news-data-platform-complet"; file="grafana_dashboard.png";   name="Grafana Dashboard" },
    @{ url="http://localhost:8080/home";                                        file="airflow_home.png";        name="Airflow DAGs" },
    @{ url="http://localhost:9200/buckets";                                     file="minio_buckets.png";       name="MinIO Buckets" },
    @{ url="http://localhost:8090/ui/clusters/local/all-topics/news-articles/messages"; file="kafka_topic.png"; name="Kafka Topic" }
)

Write-Host ""
Write-Host "=== CAPTURE DES SCREENSHOTS ===" -ForegroundColor Cyan
Write-Host "Le navigateur va s'ouvrir pour chaque interface." -ForegroundColor Yellow
Write-Host ""

foreach ($page in $pages) {
    Write-Host "Ouverture : $($page.name)..." -ForegroundColor White
    Start-Process $browserPath "--start-maximized --new-window $($page.url)"
    Take-Screenshot $page.file
}

Write-Host ""
Write-Host "=== SCREENSHOTS TERMINES ===" -ForegroundColor Green
Write-Host "Dossier : $screenshotDir" -ForegroundColor Cyan
Get-ChildItem $screenshotDir | ForEach-Object { Write-Host "  $($_.Name)  ($([Math]::Round($_.Length/1KB,1)) KB)" }
