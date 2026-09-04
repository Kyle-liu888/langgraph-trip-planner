param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Start', 'StopTrip', 'EndAll', 'Status')]
    [string]$Action,
    [string]$Distro = 'Ubuntu',
    [string]$LinuxProject = ''
)
$ErrorActionPreference = 'Stop'
$docker = Join-Path $env:ProgramFiles 'Docker/Docker/resources/bin/docker.exe'
if (-not (Test-Path -LiteralPath $docker)) { throw '请先安装 Docker Desktop；本脚本不会安装全局运行依赖。' }
if (-not $LinuxProject) {
    $devUserHome = (& wsl.exe -d $Distro -- printenv HOME).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $devUserHome.StartsWith('/home/')) { throw '无法确认 Linux 用户目录。' }
    $LinuxProject = "$devUserHome/dev/projects/langgraph-trip-planner"
}
function Invoke-Dev([string]$Operation) {
    & wsl.exe -d $Distro -- python3 "$LinuxProject/scripts/dev.py" $Operation
    if ($LASTEXITCODE -ne 0) { throw "操作失败：$Operation。未执行后续关闭步骤。" }
}
switch ($Action) {
    'Start' {
        & $docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Start-Process -FilePath (Join-Path $env:ProgramFiles 'Docker/Docker/Docker Desktop.exe') -WindowStyle Hidden
            $devDeadline = (Get-Date).AddSeconds(90)
            do {
                Start-Sleep -Seconds 3
                & $docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
                $devReady = $LASTEXITCODE -eq 0
            } until ($devReady -or (Get-Date) -gt $devDeadline)
            if (-not $devReady) { throw 'Docker 尚未就绪，请打开 Docker Desktop 检查。' }
        }
        Invoke-Dev 'start'
        & code --remote "wsl+$Distro" $LinuxProject
        Write-Host 'VS Code 打开后选择 Reopen in Container，再分别运行迁移、后端和前端任务。'
    }
    'StopTrip' { Invoke-Dev 'stop-trip' }
    'Status' { Invoke-Dev 'status' }
    'EndAll' {
        & wsl.exe --list --verbose
        Invoke-Dev 'status'
        $devConfirmation = Read-Host '将备份数据库、停止全部容器、退出 Docker 并关闭所有 WSL（包括 Ollama）。输入 END ALL 确认'
        if ($devConfirmation -cne 'END ALL') { Write-Host '已取消，未关闭环境。'; return }
        Invoke-Dev 'stop-containers'
        & $docker desktop stop
        if ($LASTEXITCODE -ne 0) { throw 'Docker 未正常退出，暂停 WSL 关闭。' }
        & wsl.exe --shutdown
        if ($LASTEXITCODE -ne 0) { throw 'WSL 关闭失败。' }
        foreach ($devPort in 5173,8000,15432) {
            if (Get-NetTCPConnection -State Listen -LocalPort $devPort -ErrorAction SilentlyContinue) {
                Write-Warning "端口 $devPort 仍有监听者，请检查其他服务；本脚本不会强杀。"
            }
        }
        Write-Host '开发环境已关闭，未删除数据卷或项目文件。'
    }
}
