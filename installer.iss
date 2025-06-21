[Setup]
AppName=Hadoop部署系统
AppVersion=1.0
DefaultDirName={pf}\HadoopDeploy
DefaultGroupName=HadoopDeploy
OutputDir=dist
OutputBaseFilename=HadoopDeploySetup
Compression=lzma
SolidCompression=yes
SetupIconFile=E:\hadoopDeployer.ico

[Files]
Source: "dist\app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Hadoop部署系统"; Filename: "{app}\app.exe"; IconFilename: "E:\hadoopDeployer.ico"
Name: "{group}\卸载Hadoop部署系统"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\app.exe"; Description: "启动Hadoop部署系统"; Flags: nowait postinstall skipifsilent
Filename: "http://localhost:5000"; Description: "在浏览器中打开Hadoop部署系统"; Flags: nowait postinstall skipifsilent shellexec 