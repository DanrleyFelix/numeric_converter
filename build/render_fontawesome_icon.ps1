param(
    [Parameter(Mandatory = $true)][string]$FontPath,
    [Parameter(Mandatory = $true)][string]$Glyph,
    [Parameter(Mandatory = $true)][int]$CanvasSize,
    [Parameter(Mandatory = $true)][string]$HexColor,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

Add-Type -AssemblyName System.Drawing

$privateFonts = New-Object System.Drawing.Text.PrivateFontCollection
$privateFonts.AddFontFile($FontPath)
$fontFamily = $privateFonts.Families[0]

$bitmap = New-Object System.Drawing.Bitmap $CanvasSize, $CanvasSize
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.Clear([System.Drawing.Color]::Transparent)

$red = [Convert]::ToInt32($HexColor.Substring(1, 2), 16)
$green = [Convert]::ToInt32($HexColor.Substring(3, 2), 16)
$blue = [Convert]::ToInt32($HexColor.Substring(5, 2), 16)
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, $red, $green, $blue))

$fontSize = [single]($CanvasSize * 0.68)
$font = New-Object System.Drawing.Font($fontFamily, $fontSize, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
$format = New-Object System.Drawing.StringFormat
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center
$layoutRect = New-Object System.Drawing.RectangleF 0, 0, $CanvasSize, $CanvasSize

$graphics.DrawString($Glyph, $font, $brush, $layoutRect, $format)

[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($OutputPath)) | Out-Null
$bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)

$format.Dispose()
$font.Dispose()
$brush.Dispose()
$graphics.Dispose()
$bitmap.Dispose()
