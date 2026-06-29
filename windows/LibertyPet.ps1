Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$framesRoot = Join-Path $root "assets\frames"
$transparentColor = [System.Drawing.Color]::FromArgb(0, 255, 0)
$random = [System.Random]::new()

function Load-Frames {
    param([string]$Name)

    $folder = Join-Path $framesRoot $Name
    $paths = Get-ChildItem -LiteralPath $folder -Filter "*.png" | Sort-Object Name
    if ($paths.Count -eq 0) {
        throw "No frames found for $Name under $folder"
    }

    $images = New-Object System.Collections.Generic.List[System.Drawing.Image]
    foreach ($path in $paths) {
        $stream = [System.IO.File]::OpenRead($path.FullName)
        try {
            $loaded = [System.Drawing.Image]::FromStream($stream)
            $images.Add([System.Drawing.Image]$loaded.Clone())
            $loaded.Dispose()
        }
        finally {
            $stream.Dispose()
        }
    }
    return $images
}

$frames = @{}
foreach ($state in @(
    "idle",
    "idle_left",
    "run",
    "run_left",
    "eat",
    "eat_left",
    "pet",
    "pet_left",
    "sleep",
    "sleep_left"
)) {
    $frames[$state] = Load-Frames $state
}

$script:state = "idle"
$script:direction = 1
$script:frameIndex = 0
$script:stateTicks = 0
$script:dragStart = $null
$script:didDrag = $false

function Get-StateName {
    switch ($script:state) {
        "run" { if ($script:direction -lt 0) { "run_left" } else { "run" }; break }
        "eat" { if ($script:direction -lt 0) { "eat_left" } else { "eat" }; break }
        "pet" { if ($script:direction -lt 0) { "pet_left" } else { "pet" }; break }
        "sleep" { if ($script:direction -lt 0) { "sleep_left" } else { "sleep" }; break }
        default { if ($script:direction -lt 0) { "idle_left" } else { "idle" } }
    }
}

function Set-State {
    param(
        [string]$Next,
        [Nullable[int]]$Ticks = $null
    )

    $script:state = $Next
    $script:frameIndex = 0
    if ($Ticks.HasValue) {
        $script:stateTicks = $Ticks.Value
        return
    }

    switch ($Next) {
        "run" { $script:stateTicks = $random.Next(55, 121); break }
        "eat" { $script:stateTicks = $random.Next(30, 47); break }
        "pet" { $script:stateTicks = $random.Next(20, 33); break }
        "sleep" { $script:stateTicks = $random.Next(45, 81); break }
        default { $script:stateTicks = $random.Next(15, 36) }
    }
}

function Choose-NextState {
    $roll = $random.NextDouble()
    if ($roll -lt 0.58) {
        Set-State "run"
    }
    elseif ($roll -lt 0.82) {
        Set-State "idle"
    }
    elseif ($roll -lt 0.95) {
        Set-State "eat"
    }
    else {
        Set-State "sleep"
    }
}

$first = $frames["idle"][0]
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea

$form = [System.Windows.Forms.Form]::new()
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.ShowInTaskbar = $false
$form.TopMost = $true
$form.KeyPreview = $true
$form.BackColor = $transparentColor
$form.TransparencyKey = $transparentColor
$form.ClientSize = [System.Drawing.Size]::new($first.Width, $first.Height)
$form.Location = [System.Drawing.Point]::new(
    [int]($screen.Left + ($screen.Width - $first.Width) / 2),
    [int]($screen.Bottom - $first.Height - 24)
)

$picture = [System.Windows.Forms.PictureBox]::new()
$picture.Dock = [System.Windows.Forms.DockStyle]::Fill
$picture.BackColor = $transparentColor
$picture.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Normal
$picture.Image = $first
$picture.Cursor = [System.Windows.Forms.Cursors]::Hand
$form.Controls.Add($picture)

$closeAction = {
    $form.Close()
}

$mouseDown = {
    param($sender, [System.Windows.Forms.MouseEventArgs]$event)

    $form.Activate()
    if ($event.Button -eq [System.Windows.Forms.MouseButtons]::Right) {
        $form.Close()
        return
    }
    if ($event.Button -ne [System.Windows.Forms.MouseButtons]::Left) {
        return
    }
    if ($event.Clicks -ge 2) {
        Set-State "eat" 34
        $script:dragStart = $null
        $script:didDrag = $false
        return
    }
    $script:dragStart = [System.Drawing.Point]::new($event.X, $event.Y)
    $script:didDrag = $false
}

$mouseMove = {
    param($sender, [System.Windows.Forms.MouseEventArgs]$event)

    if ($null -eq $script:dragStart) {
        return
    }
    if (($event.Button -band [System.Windows.Forms.MouseButtons]::Left) -eq 0) {
        return
    }
    $script:didDrag = $true
    $mouse = [System.Windows.Forms.Cursor]::Position
    $form.Location = [System.Drawing.Point]::new(
        $mouse.X - $script:dragStart.X,
        $mouse.Y - $script:dragStart.Y
    )
}

$mouseUp = {
    param($sender, [System.Windows.Forms.MouseEventArgs]$event)

    if ($event.Button -eq [System.Windows.Forms.MouseButtons]::Left -and -not $script:didDrag) {
        Set-State "pet" 26
    }
    $script:dragStart = $null
    $script:didDrag = $false
}

$picture.Add_MouseDown($mouseDown)
$picture.Add_MouseMove($mouseMove)
$picture.Add_MouseUp($mouseUp)
$form.Add_MouseDown($mouseDown)
$form.Add_MouseMove($mouseMove)
$form.Add_MouseUp($mouseUp)
$form.Add_KeyDown({
    param($sender, [System.Windows.Forms.KeyEventArgs]$event)

    if ($event.KeyCode -eq [System.Windows.Forms.Keys]::Escape -or $event.KeyCode -eq [System.Windows.Forms.Keys]::Q) {
        $form.Close()
    }
})

$timer = [System.Windows.Forms.Timer]::new()
$timer.Interval = 95
$timer.Add_Tick({
    $key = Get-StateName
    $images = $frames[$key]
    $picture.Image = $images[$script:frameIndex % $images.Count]
    $script:frameIndex += 1

    if ($script:state -eq "run") {
        $nextX = $form.Left + ($script:direction * 7)
        $nextY = $form.Top + @(-1, 0, 0, 1)[$random.Next(0, 4)]
        $nextY = [Math]::Min([Math]::Max($screen.Top + 6, $nextY), $screen.Bottom - $form.Height - 6)

        $leftEdge = $screen.Left - [int]($form.Width / 3)
        $rightEdge = $screen.Right - $form.Width + [int]($form.Width / 3)
        if ($nextX -le $leftEdge) {
            $nextX = $leftEdge
            $script:direction = 1
        }
        elseif ($nextX -ge $rightEdge) {
            $nextX = $rightEdge
            $script:direction = -1
        }

        $form.Location = [System.Drawing.Point]::new($nextX, $nextY)
    }

    $script:stateTicks -= 1
    if ($script:stateTicks -le 0) {
        Choose-NextState
    }
})

$form.Add_FormClosed({
    $timer.Stop()
    $timer.Dispose()
    foreach ($list in $frames.Values) {
        foreach ($image in $list) {
            $image.Dispose()
        }
    }
})

Choose-NextState
$timer.Start()
[System.Windows.Forms.Application]::EnableVisualStyles()
if ($env:LIBERTY_PET_TEST_MS) {
    $testTimer = [System.Windows.Forms.Timer]::new()
    $testTimer.Interval = [int]$env:LIBERTY_PET_TEST_MS
    $testTimer.Add_Tick({
        $testTimer.Stop()
        $testTimer.Dispose()
        $form.Close()
    })
    $testTimer.Start()
}
[System.Windows.Forms.Application]::Run($form)
