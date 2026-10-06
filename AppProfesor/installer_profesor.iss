; =============================================
; Inno Setup Script - Panel Docente UPC
; Python 3.12.10 va incrustado en el instalador.
; Crea venv e instala dependencias en silencio.
; =============================================
#define MyAppName "Panel Docente UPC"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Universidad Popular del Cesar"
#define MyAppExeName "PanelDocente_UPC.exe"
#define SourceDir "."
#define DistDir "dist"

[Setup]
AppId={{E7A3F1C2-4B5D-4A8E-B9C0-1234567890AB}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SupervisionUPC\PanelDocente
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=Instalar_PanelDocente_UPC
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=recursos\installer_icon.ico
WizardSmallImageFile=recursos\wizard_small.bmp
WizardImageFile=recursos\wizard_image.bmp
ExtraDiskSpaceRequired=1073741824

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "startmenuicon"; Description: "Agregar al Menu de Inicio"; GroupDescription: "Accesos directos:"

[Files]
; Ejecutable lanzador compilado
Source: "{#DistDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Archivos del proyecto
Source: "{#SourceDir}\main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\requerimientos.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\api\*"; DestDir: "{app}\api"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\utils\*"; DestDir: "{app}\utils"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\vista\*"; DestDir: "{app}\vista"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\recursos\*"; DestDir: "{app}\recursos"; Flags: ignoreversion recursesubdirs createallsubdirs
; Instalador de Python 3.12.10 incrustado - se borra despues de instalar
Source: "..\python-3.12.10-amd64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\SupervisionUPC\Profesor_env"
Type: filesandordirs; Name: "{localappdata}\SupervisionUPC\logs"
Type: files; Name: "{localappdata}\SupervisionUPC\*.log"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
var
  ProgressPage: TOutputProgressWizardPage;

// Busca python.exe 3.12 de manera robusta:
// 1. En AppData per-user estándar
// 2. En el Registro de Windows de usuario (HKCU)
// 3. En el Registro de Windows de máquina (HKLM)
// 4. En Program Files y raíz del sistema
function BuscarPython312: String;
var
  TestPath, RegPath: String;
begin
  Result := '';

  // 1. Ruta default per-user en AppData
  TestPath := ExpandConstant('{localappdata}') + '\Programs\Python\Python312\python.exe';
  if FileExists(TestPath) then begin
    Result := TestPath;
    Exit;
  end;

  // 2. Ruta alternativa con punto
  TestPath := ExpandConstant('{localappdata}') + '\Programs\Python\Python3.12\python.exe';
  if FileExists(TestPath) then begin
    Result := TestPath;
    Exit;
  end;

  // 3. Consultar Registro de Windows del Usuario Actual (HKCU)
  if RegQueryStringValue(HKEY_CURRENT_USER, 'Software\Python\PythonCore\3.12\InstallPath', 'ExecutablePath', RegPath) then begin
    if FileExists(RegPath) then begin
      Result := RegPath;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKEY_CURRENT_USER, 'Software\Python\PythonCore\3.12\InstallPath', '', RegPath) then begin
    TestPath := RegPath;
    if (Length(TestPath) > 0) and (TestPath[Length(TestPath)] <> '\') then
      TestPath := TestPath + '\';
    TestPath := TestPath + 'python.exe';
    if FileExists(TestPath) then begin
      Result := TestPath;
      Exit;
    end;
  end;

  // 4. Consultar Registro de Windows de Máquina (HKLM)
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'Software\Python\PythonCore\3.12\InstallPath', 'ExecutablePath', RegPath) then begin
    if FileExists(RegPath) then begin
      Result := RegPath;
      Exit;
    end;
  end;
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'Software\Python\PythonCore\3.12\InstallPath', '', RegPath) then begin
    TestPath := RegPath;
    if (Length(TestPath) > 0) and (TestPath[Length(TestPath)] <> '\') then
      TestPath := TestPath + '\';
    TestPath := TestPath + 'python.exe';
    if FileExists(TestPath) then begin
      Result := TestPath;
      Exit;
    end;
  end;

  // 5. Verificar Program Files (64 y 32 bits)
  TestPath := ExpandConstant('{commonpf64}') + '\Python312\python.exe';
  if FileExists(TestPath) then begin
    Result := TestPath;
    Exit;
  end;

  TestPath := ExpandConstant('{commonpf32}') + '\Python312\python.exe';
  if FileExists(TestPath) then begin
    Result := TestPath;
    Exit;
  end;

  TestPath := 'C:\Python312\python.exe';
  if FileExists(TestPath) then begin
    Result := TestPath;
    Exit;
  end;
end;

procedure InitializeWizard;
begin
  ProgressPage := CreateOutputProgressPage(
    'Configurando entorno',
    'Por favor espere. Este proceso puede tardar varios minutos...'
  );
end;

procedure InstalarDependencias;
var
  VenvDir, AppDir, PipExe, PythonExe, ReqFile, LogFile, PythonInstaller, PythonArgs, TargetPythonDir, PyLogFile: String;
  ResultCode: Integer;
begin
  AppDir          := ExpandConstant('{app}');
  VenvDir         := ExpandConstant('{localappdata}') + '\SupervisionUPC\Profesor_env';
  LogFile         := AppDir + '\pip_error.log';
  ReqFile         := AppDir + '\requerimientos.txt';
  PythonInstaller := ExpandConstant('{tmp}') + '\python-3.12.10-amd64.exe';
  TargetPythonDir := ExpandConstant('{localappdata}') + '\Programs\Python\Python312';
  PyLogFile       := ExpandConstant('{tmp}') + '\python_install.log';

  ProgressPage.Show;

  // === PASO 1: Verificar si Python 3.12 ya esta disponible ===
  ProgressPage.SetText('Paso 1/4: Verificando Python 3.12.10...', '');
  ProgressPage.SetProgress(1, 4);

  PythonExe := BuscarPython312;

  // Si no esta instalado en el sistema, instalar silenciosamente en espacio de usuario
  if PythonExe = '' then begin
    ProgressPage.SetText('Paso 1/4: Instalando Python 3.12.10 (sin privilegios de admin)...', '');
    
    // Parámetros blindados para espacio de usuario:
    // - Include_launcher=0 e InstallLauncherAllUsers=0 evitan escribir en C:\Windows (CERO permisos de Administrador requeridos)
    // - PrependPath=0, Shortcuts=0 y AssociateFiles=0 garantizan que NO se contamine el sistema del usuario
    // - TargetDir define la ruta exacta sin ambigüedades
    PythonArgs := '/quiet' +
                  ' InstallAllUsers=0' +
                  ' Include_launcher=0' +
                  ' InstallLauncherAllUsers=0' +
                  ' PrependPath=0' +
                  ' Shortcuts=0' +
                  ' AssociateFiles=0' +
                  ' Include_doc=0' +
                  ' Include_test=0' +
                  ' Include_dev=1' +
                  ' Include_exe=1' +
                  ' Include_lib=1' +
                  ' Include_pip=1' +
                  ' TargetDir="' + TargetPythonDir + '"' +
                  ' /log "' + PyLogFile + '"';

    Exec(PythonInstaller, PythonArgs, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // Buscar de nuevo despues de instalar
    PythonExe := BuscarPython312;
  end;

  if PythonExe = '' then begin
    ProgressPage.Hide;
    MsgBox(
      'Error: No se pudo instalar Python 3.12.10.' + #13#10 + #13#10 +
      'El registro del error se encuentra en:' + #13#10 +
      PyLogFile + #13#10 + #13#10 +
      'Por favor verifique que su antivirus permita la instalacion o consulte con el soporte.',
      mbError, MB_OK);
    Exit;
  end;

  // === PASO 2: Crear entorno virtual ===
  ProgressPage.SetText('Paso 2/4: Creando contenedor virtual (venv)...', '');
  ProgressPage.SetProgress(2, 4);

  Exec(PythonExe, '-m venv "' + VenvDir + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  PythonExe := VenvDir + '\Scripts\python.exe';
  PipExe    := VenvDir + '\Scripts\pip.exe';

  if not FileExists(PipExe) then begin
    ProgressPage.Hide;
    MsgBox(
      'Error: No se pudo crear el entorno virtual.' + #13#10 +
      'Ruta esperada de pip: ' + PipExe,
      mbError, MB_OK);
    Exit;
  end;

  // === PASO 3: Actualizar pip ===
  ProgressPage.SetText('Paso 3/4: Actualizando gestor de paquetes...', '');
  ProgressPage.SetProgress(3, 4);

  Exec('cmd.exe',
    '/c ""' + PipExe + '" install --upgrade pip setuptools wheel --quiet >> "' + LogFile + '" 2>&1"',
    AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // === PASO 4: Instalar dependencias ===
  // --prefer-binary: usa .whl precompilados, nunca intenta compilar en la maquina del usuario
  ProgressPage.SetText('Paso 4/4: Instalando librerias (puede tardar varios minutos)...', '');
  ProgressPage.SetProgress(4, 4);

  Exec('cmd.exe',
    '/c ""' + PipExe + '" install --prefer-binary -r "' + ReqFile + '" >> "' + LogFile + '" 2>&1"',
    AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if ResultCode <> 0 then begin
    ProgressPage.Hide;
    MsgBox(
      'Advertencia: Algunas librerias no se instalaron correctamente.' + #13#10 +
      'El detalle del error esta en:' + #13#10 +
      LogFile,
      mbError, MB_OK);
    Exit;
  end;

  ProgressPage.Hide;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    InstalarDependencias();
end;
