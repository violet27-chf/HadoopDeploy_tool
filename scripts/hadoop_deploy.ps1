# Hadoop自动部署脚本 (PowerShell版本)
# 适用于Windows系统

param(
    [string]$HadoopVersion = "3.3.6",
    [string]$InstallDir = "C:\hadoop",
    [string]$DownloadDir = "C:\temp\hadoop_download",
    [string]$UploadDir = "C:\temp\hadoop_uploads"  # 用户上传文件目录
)

# 颜色定义
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$White = "White"

# 日志函数
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    switch ($Level) {
        "INFO" { 
            Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor $Blue 
        }
        "SUCCESS" { 
            Write-Host "[$timestamp] [SUCCESS] $Message" -ForegroundColor $Green 
        }
        "WARNING" { 
            Write-Host "[$timestamp] [WARNING] $Message" -ForegroundColor $Yellow 
        }
        "ERROR" { 
            Write-Host "[$timestamp] [ERROR] $Message" -ForegroundColor $Red 
        }
        default { 
            Write-Host "[$timestamp] [INFO] $Message" -ForegroundColor $White 
        }
    }
}

# 检查用户上传的文件
function Check-UploadedFiles {
    Write-Log "检查用户上传的文件..."
    
    # 创建上传目录
    if (!(Test-Path $UploadDir)) {
        New-Item -ItemType Directory -Path $UploadDir -Force | Out-Null
    }
    
    # 检查是否有用户上传的Hadoop包
    $hadoopUploadedFile = Join-Path $UploadDir "hadoop-uploaded.tar.gz"
    if (Test-Path $hadoopUploadedFile) {
        Write-Log "发现用户上传的Hadoop包"
        $script:HadoopUploadedFile = $hadoopUploadedFile
    } else {
        $script:HadoopUploadedFile = $null
    }
    
    # 检查是否有用户上传的Java包
    $javaFiles = @(
        (Join-Path $UploadDir "java-uploaded.tar.gz"),
        (Join-Path $UploadDir "java-uploaded.tgz"),
        (Join-Path $UploadDir "java-uploaded.zip")
    )
    
    foreach ($file in $javaFiles) {
        if (Test-Path $file) {
            Write-Log "发现用户上传的Java包: $file"
            $script:JavaUploadedFile = $file
            break
        }
    }
    
    if (-not $script:JavaUploadedFile) {
        $script:JavaUploadedFile = $null
    }
}

# 检查系统环境
function Check-Environment {
    Write-Log "检查系统环境..."
    
    # 检查操作系统
    if ($env:OS -ne "Windows_NT") {
        Write-Log "此脚本仅支持Windows系统" -Level "ERROR"
        exit 1
    }
    
    # 检查PowerShell版本
    $psVersion = $PSVersionTable.PSVersion.Major
    if ($psVersion -lt 5) {
        Write-Log "需要PowerShell 5.0或更高版本" -Level "ERROR"
        exit 1
    }
    
    # 检查内存
    $memory = Get-WmiObject -Class Win32_ComputerSystem | Select-Object -ExpandProperty TotalPhysicalMemory
    $memoryGB = [math]::Round($memory / 1GB, 2)
    Write-Log "系统内存: ${memoryGB}GB"
    
    if ($memoryGB -lt 4) {
        Write-Log "系统内存不足4GB，可能影响Hadoop性能" -Level "WARNING"
    }
    
    # 检查磁盘空间
    $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
    $freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB, 2)
    Write-Log "可用磁盘空间: ${freeSpaceGB}GB"
    
    if ($freeSpaceGB -lt 10) {
        Write-Log "磁盘空间不足10GB，无法继续安装" -Level "ERROR"
        exit 1
    }
    
    Write-Log "系统环境检查完成" -Level "SUCCESS"
}

# 安装Java环境
function Install-Java {
    Write-Log "安装Java环境..."
    
    # 如果有用户上传的Java包，优先使用
    if ($script:JavaUploadedFile) {
        Write-Log "使用用户上传的Java包: $($script:JavaUploadedFile)"
        Install-CustomJava
    } else {
        # 检查是否已安装Java
        $javaPath = Get-Command java -ErrorAction SilentlyContinue
        if ($javaPath) {
            Write-Log "Java已安装，跳过安装"
            java -version
            return
        }
        
        # 下载并安装OpenJDK
        Write-Log "下载OpenJDK..."
        $javaUrl = "https://download.java.net/java/GA/jdk11.0.2/9ae5e3450b34be4a91629b33406a7b4d/9/GPL/openjdk-11.0.2_windows-x64_bin.zip"
        $javaZip = Join-Path $DownloadDir "openjdk-11.zip"
        
        try {
            Invoke-WebRequest -Uri $javaUrl -OutFile $javaZip -UseBasicParsing
            Expand-Archive -Path $javaZip -DestinationPath "C:\Program Files\Java" -Force
            Remove-Item $javaZip -Force
            
            # 设置环境变量
            $javaDir = Get-ChildItem "C:\Program Files\Java" -Directory | Where-Object { $_.Name -like "*jdk*" } | Select-Object -First 1
            if ($javaDir) {
                $env:JAVA_HOME = $javaDir.FullName
                $env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
                
                # 永久设置环境变量
                [Environment]::SetEnvironmentVariable("JAVA_HOME", $javaDir.FullName, "Machine")
                [Environment]::SetEnvironmentVariable("PATH", "$env:JAVA_HOME\bin;$env:PATH", "Machine")
                
                Write-Log "Java安装完成" -Level "SUCCESS"
                java -version
            }
        }
        catch {
            Write-Log "Java安装失败: $($_.Exception.Message)" -Level "ERROR"
            exit 1
        }
    }
}

# 安装自定义Java包
function Install-CustomJava {
    Write-Log "安装自定义Java包..."
    
    $javaInstallDir = "C:\Program Files\Java"
    if (!(Test-Path $javaInstallDir)) {
        New-Item -ItemType Directory -Path $javaInstallDir -Force | Out-Null
    }
    
    # 解压Java包
    if ($script:JavaUploadedFile.EndsWith(".zip")) {
        Expand-Archive -Path $script:JavaUploadedFile -DestinationPath $javaInstallDir -Force
    } else {
        # 使用7-Zip解压tar.gz/tgz文件
        $sevenZipPath = "C:\Program Files\7-Zip\7z.exe"
        if (Test-Path $sevenZipPath) {
            & $sevenZipPath x $script:JavaUploadedFile -o"$javaInstallDir" -y
        } else {
            Write-Log "需要7-Zip来解压tar.gz文件，请先安装7-Zip" -Level "ERROR"
            exit 1
        }
    }
    
    # 查找解压后的Java目录
    $javaDir = Get-ChildItem $javaInstallDir -Directory | Where-Object { $_.Name -like "*jdk*" -or $_.Name -like "*java*" } | Select-Object -First 1
    
    if (-not $javaDir) {
        Write-Log "无法找到Java安装目录" -Level "ERROR"
        exit 1
    }
    
    # 设置环境变量
    $env:JAVA_HOME = $javaDir.FullName
    $env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
    
    # 永久设置环境变量
    [Environment]::SetEnvironmentVariable("JAVA_HOME", $javaDir.FullName, "Machine")
    [Environment]::SetEnvironmentVariable("PATH", "$env:JAVA_HOME\bin;$env:PATH", "Machine")
    
    # 验证Java安装
    if (Get-Command java -ErrorAction SilentlyContinue) {
        Write-Log "自定义Java安装成功" -Level "SUCCESS"
        java -version
    } else {
        Write-Log "自定义Java安装失败" -Level "ERROR"
        exit 1
    }
}

# 下载Hadoop
function Download-Hadoop {
    Write-Log "下载Hadoop $HadoopVersion..."
    
    # 创建下载目录
    if (!(Test-Path $DownloadDir)) {
        New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
    }
    
    $hadoopFile = Join-Path $DownloadDir "hadoop-$HadoopVersion.tar.gz"
    
    # 如果有用户上传的Hadoop包，优先使用
    if ($script:HadoopUploadedFile) {
        Write-Log "使用用户上传的Hadoop包: $($script:HadoopUploadedFile)"
        Copy-Item $script:HadoopUploadedFile $hadoopFile -Force
        Write-Log "使用用户上传的Hadoop包" -Level "SUCCESS"
        return $hadoopFile
    }
    
    # 检查是否已下载
    if (Test-Path $hadoopFile) {
        Write-Log "Hadoop安装包已存在，跳过下载" -Level "WARNING"
        return $hadoopFile
    }
    
    # 定义下载源列表（按优先级排序）
    $downloadSources = @(
        "https://archive.apache.org/dist/hadoop/common/hadoop-$HadoopVersion/hadoop-$HadoopVersion.tar.gz",
        "https://mirrors.tuna.tsinghua.edu.cn/apache/hadoop/common/hadoop-$HadoopVersion/hadoop-$HadoopVersion.tar.gz",
        "https://mirrors.aliyun.com/apache/hadoop/common/hadoop-$HadoopVersion/hadoop-$HadoopVersion.tar.gz",
        "https://mirrors.huaweicloud.com/apache/hadoop/common/hadoop-$HadoopVersion/hadoop-$HadoopVersion.tar.gz",
        "https://mirror.bit.edu.cn/apache/hadoop/common/hadoop-$HadoopVersion/hadoop-$HadoopVersion.tar.gz"
    )
    
    # 尝试从不同源下载
    foreach ($sourceUrl in $downloadSources) {
        Write-Log "尝试从源下载: $sourceUrl"
        
        try {
            # 检查网络连接
            $response = Invoke-WebRequest -Uri $sourceUrl -Method Head -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Log "源可用，开始下载..."
                
                # 下载文件
                Invoke-WebRequest -Uri $sourceUrl -OutFile $hadoopFile -UseBasicParsing -TimeoutSec 300
                
                if (Test-Path $hadoopFile) {
                    $fileSize = (Get-Item $hadoopFile).Length
                    if ($fileSize -gt 100MB) {  # 检查文件大小是否合理
                        Write-Log "Hadoop下载成功 (源: $sourceUrl)" -Level "SUCCESS"
                        return $hadoopFile
                    } else {
                        Write-Log "下载的文件大小异常，可能下载失败" -Level "WARNING"
                        Remove-Item $hadoopFile -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
        catch {
            Write-Log "从 $sourceUrl 下载失败: $($_.Exception.Message)" -Level "WARNING"
            if (Test-Path $hadoopFile) {
                Remove-Item $hadoopFile -Force -ErrorAction SilentlyContinue
            }
        }
    }
    
    Write-Log "所有下载源都失败，无法下载Hadoop" -Level "ERROR"
    return $null
}

# 安装Hadoop
function Install-Hadoop {
    param([string]$HadoopFile)
    
    Write-Log "安装Hadoop..."
    
    # 创建安装目录
    if (!(Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    
    # 解压Hadoop
    $sevenZipPath = "C:\Program Files\7-Zip\7z.exe"
    if (Test-Path $sevenZipPath) {
        & $sevenZipPath x $HadoopFile -o"$InstallDir" -y
    } else {
        Write-Log "需要7-Zip来解压Hadoop文件，请先安装7-Zip" -Level "ERROR"
        exit 1
    }
    
    # 查找解压后的Hadoop目录
    $hadoopDir = Get-ChildItem $InstallDir -Directory | Where-Object { $_.Name -like "*hadoop*" } | Select-Object -First 1
    
    if (-not $hadoopDir) {
        Write-Log "无法找到Hadoop安装目录" -Level "ERROR"
        exit 1
    }
    
    # 设置环境变量
    $env:HADOOP_HOME = $hadoopDir.FullName
    $env:PATH = "$env:HADOOP_HOME\bin;$env:PATH"
    
    # 永久设置环境变量
    [Environment]::SetEnvironmentVariable("HADOOP_HOME", $hadoopDir.FullName, "Machine")
    [Environment]::SetEnvironmentVariable("PATH", "$env:HADOOP_HOME\bin;$env:PATH", "Machine")
    
    Write-Log "Hadoop安装完成" -Level "SUCCESS"
}

# 配置Hadoop
function Configure-Hadoop {
    Write-Log "配置Hadoop..."
    
    $hadoopConfDir = Join-Path $env:HADOOP_HOME "etc\hadoop"
    
    # 配置core-site.xml
    $coreSiteContent = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>C:\tmp\hadoop-${env:USERNAME}</value>
    </property>
</configuration>
"@
    
    Set-Content -Path (Join-Path $hadoopConfDir "core-site.xml") -Value $coreSiteContent -Encoding UTF8
    
    # 配置hdfs-site.xml
    $hdfsSiteContent = @"
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="configuration.xsl"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>1</value>
    </property>
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>C:\data\hadoop\hdfs\namenode</value>
    </property>
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>C:\data\hadoop\hdfs\datanode</value>
    </property>
</configuration>
"@
    
    Set-Content -Path (Join-Path $hadoopConfDir "hdfs-site.xml") -Value $hdfsSiteContent -Encoding UTF8
    
    # 创建数据目录
    $dataDirs = @(
        "C:\data\hadoop\hdfs\namenode",
        "C:\data\hadoop\hdfs\datanode"
    )
    
    foreach ($dir in $dataDirs) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Log "Hadoop配置完成" -Level "SUCCESS"
}

# 主函数
function Main {
    Write-Log "开始Hadoop自动部署..."
    
    Check-Environment
    Check-UploadedFiles
    Install-Java
    
    $hadoopFile = Download-Hadoop
    if (-not $hadoopFile) {
        Write-Log "Hadoop下载失败" -Level "ERROR"
        exit 1
    }
    
    Install-Hadoop -HadoopFile $hadoopFile
    Configure-Hadoop
    
    Write-Log "Hadoop部署完成！" -Level "SUCCESS"
    Write-Log "Hadoop Web界面:"
    Write-Log "  - NameNode: http://localhost:9870"
    Write-Log "  - ResourceManager: http://localhost:8088"
    Write-Log "  - NodeManager: http://localhost:8042"
}

# 执行主函数
Main 