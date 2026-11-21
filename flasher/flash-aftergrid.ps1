# Aftergrid: join the ISO parts, verify them, and write Aftergrid to a USB stick (Windows 10/11).
param([switch]$ListOnly, [switch]$VerifyOnly, [int]$Disk = -1, [int64]$ExpectSize = 0)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ListOnly) {
  Get-Disk | Where-Object { $_.BusType -eq 'USB' } | ForEach-Object { "Disk {0} | {1} | {2} bytes | boot={3} system={4}" -f $_.Number, $_.FriendlyName, $_.Size, $_.IsBoot, $_.IsSystem } |
    Out-File -Encoding utf8 (Join-Path $Here 'aftergrid-usb-list.txt')
  exit 0
}
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  $a = "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$PSCommandPath`""
  if ($Disk -ge 0) { $a += " -Disk $Disk -ExpectSize $ExpectSize" }
  if ($VerifyOnly) { $a += " -VerifyOnly" }
  Start-Process powershell -Verb RunAs -ArgumentList $a
  exit
}
try { Start-Transcript -Path (Join-Path $Here ("aftergrid-flash-{0:HHmmss}.log" -f (Get-Date))) -Force | Out-Null } catch {}
$Iso      = Join-Path $Here '@ISONAME@'
$WantHash = '@HASH@'
$Sizes    = [ordered]@{ @SIZES@ }
function Say($t, $c='White') { Write-Host $t -ForegroundColor $c }
Say "`n=== @ISONAME@ USB maker ===`n" Cyan

# ---------- 1. Build the ISO from parts ----------
if ((Test-Path $Iso) -and ((Get-FileHash $Iso -Algorithm SHA256).Hash -eq $WantHash)) {
  Say "ISO already built and verified." Green
} else {
  $Search = @($Here, (Join-Path $env:USERPROFILE 'Downloads'), (Join-Path $env:USERPROFILE 'Downloads\Aftergrid'))
  $Parts = @()
  foreach ($n in $Sizes.Keys) {
    $hit = Get-ChildItem -Path $Search -Filter "@ISONAME@.$n*.part" -File -ErrorAction SilentlyContinue |
           Where-Object { $_.Length -eq $Sizes[$n] } | Select-Object -First 1
    if (-not $hit) { Say "Missing part $n (@ISONAME@.$n.part, $([math]::Round($Sizes[$n]/1MB)) MB). Download it from the Claude chat into Downloads, then run this again." Red; Read-Host 'Press Enter to close'; exit 1 }
    $Parts += $hit.FullName
  }
  Say "Joining $($Parts.Count) parts..."
  $out = [IO.File]::Create($Iso)
  foreach ($p in $Parts) { $in = [IO.File]::OpenRead($p); $in.CopyTo($out, 8MB); $in.Close() }
  $out.Close()
  Say "Verifying checksum..."
  if ((Get-FileHash $Iso -Algorithm SHA256).Hash -ne $WantHash) { Remove-Item $Iso; Say "Checksum FAILED. A part is corrupt; re-download it." Red; Read-Host 'Press Enter to close'; exit 1 }
  Say "ISO OK." Green
}

# ---------- 2. Pick the USB stick ----------
$sys = (Get-Partition -DriveLetter $env:SystemDrive[0]).DiskNumber
$usb = @(Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.Number -ne $sys -and -not $_.IsBoot -and -not $_.IsSystem })
if ($usb.Count -eq 0) { Say "No USB drive found. Plug in the stick and run again." Red; Read-Host 'Press Enter to close'; exit 1 }
Say "`nUSB drives found:" Cyan
$usb | ForEach-Object { "  Disk {0}:  {1}  {2:N1} GB" -f $_.Number, $_.FriendlyName, ($_.Size/1GB) } | ForEach-Object { Say $_ Yellow }
if ($Disk -ge 0) { $num = $Disk } else { $num = Read-Host "`nType the Disk number of your Aftergrid stick" }
$target = $usb | Where-Object { $_.Number -eq [int]$num }
if (-not $target) { Say "Not one of the USB drives listed. Stopping." Red; Read-Host 'Press Enter to close'; exit 1 }
if ($target.Size -lt (Get-Item $Iso).Length) { Say "That drive is too small." Red; Read-Host 'Press Enter to close'; exit 1 }
Say ("`nEVERYTHING on Disk {0} ({1}, {2:N1} GB) will be ERASED." -f $target.Number, $target.FriendlyName, ($target.Size/1GB)) Red
if ($Disk -ge 0) {
  if ($target.Size -ne $ExpectSize) { Say "Disk $Disk is not the stick that was confirmed (size changed). Stopping." Red; Read-Host 'Press Enter to close'; exit 1 }
  if (-not $VerifyOnly) { Say "Pre-confirmed in chat. Starting in 10 seconds; close this window to cancel." Yellow; Start-Sleep 10 }
} elseif ((Read-Host "Type ERASE to continue") -cne 'ERASE') { Say "Cancelled. Nothing was changed." Yellow; Read-Host 'Press Enter to close'; exit 0 }

# ---------- 3. Wipe and write ----------
if (-not $VerifyOnly) {
Say "Wiping partition table..."
"select disk $($target.Number)`r`nclean`r`nrescan" | Out-File -Encoding ascii "$env:TEMP\aftergrid-dp.txt"
diskpart /s "$env:TEMP\aftergrid-dp.txt" | Out-Null
Start-Sleep 3
}

Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using Microsoft.Win32.SafeHandles;
public static class ArkRaw {
  [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  public static extern SafeFileHandle CreateFile(string n, uint a, uint s, IntPtr sec, uint c, uint f, IntPtr t);
}
'@
$h = [ArkRaw]::CreateFile("\\.\PhysicalDrive$($target.Number)", [uint32]3221225472, [uint32]3, [IntPtr]::Zero, [uint32]3, [uint32]2147483648, [IntPtr]::Zero)
if ($h.IsInvalid) { Say "Could not open the drive (error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())). Close Explorer windows on it and retry." Red; Read-Host 'Press Enter to close'; exit 1 }
$dst = New-Object IO.FileStream($h, [IO.FileAccess]::ReadWrite, 4096, $false)
$src = [IO.File]::OpenRead($Iso)
$buf = New-Object byte[] (4MB); $total = $src.Length; $done = 0
if (-not $VerifyOnly) {
while (($r = $src.Read($buf, 0, $buf.Length)) -gt 0) {
  if ($r % 512 -ne 0) { [Array]::Clear($buf, $r, 512 - ($r % 512)); $r += 512 - ($r % 512) }
  $dst.Write($buf, 0, $r); $done += $r
  Write-Progress -Activity "Writing Aftergrid to Disk $($target.Number)" -PercentComplete ([int]($done*100/$total)) -Status ("{0:N0} / {1:N0} MB" -f ($done/1MB), ($total/1MB))
}
$dst.Flush()
}
$src.Close()

# ---------- 4. Verify ----------
Say "Verifying what was written..."
$dst.Seek(0, 'Begin') | Out-Null
$sha = [Security.Cryptography.SHA256]::Create(); $left = $total
while ($left -gt 0) {
  $want = [int][math]::Min([int64]$buf.Length, [int64]([math]::Ceiling($left/512)*512))
  $r = $dst.Read($buf, 0, $want); $use = [int][math]::Min([int64]$r, [int64]$left)
  $sha.TransformBlock($buf, 0, $use, $null, 0) | Out-Null; $left -= $use
  Write-Progress -Activity "Verifying" -PercentComplete (($total-$left)*100/$total)
}
$sha.TransformFinalBlock($buf, 0, 0) | Out-Null; $dst.Close()
$got = -join ($sha.Hash | ForEach-Object { $_.ToString('X2') })
if ($got -ne $WantHash) { Say "Verify FAILED. Try another USB port or stick." Red; Read-Host 'Press Enter to close'; exit 1 }
Say "`nDONE. Aftergrid is on the stick and verified." Green
Say "If Windows pops up 'You need to format the disk', click CANCEL. That's normal."
Say "Next: restart, tap the boot key (F12 / F9 / F8 / F11 / Esc), pick the USB stick, choose 'Aftergrid - Fresh session',"
Say "then run Aftergrid Control -> '1. Set up this stick'."
Read-Host "`nPress Enter to close"
