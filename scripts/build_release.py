import os
import shutil
import tarfile
import subprocess
from pathlib import Path
import platform

#
# assume the scripts runs under its directory, "scripts", as defined in release.yml
#
os.chdir("../")
project_root = Path(__file__).resolve().parent.parent
dist_dir = project_root / "dist"
project_name = "shinestacker"
app_name = "shinestacker"
package_dir = "shinestacker"

sys_name = platform.system().lower()

hooks_dir = "scripts/hooks"

print("=== USING HOOKS ===")
hook_files = list(Path(hooks_dir).glob("hook-*.py"))
for hook in hook_files:
    print(f"  - {hook.name}")

if sys_name == 'darwin':
    # macOS: Use --windowed to create ONLY the .app bundle
    pyinstaller_cmd = [
        "pyinstaller", "--windowed",
        f"--name={app_name}",
        f"--distpath={dist_dir}",
        "--paths=src",
        "--icon=src/shinestacker/gui/ico/shinestacker.icns",
        f"--additional-hooks-dir={hooks_dir}",
        # Collect specific modules instead of using --collect-all
        f"--collect-all={project_name}",
        "--collect-data=imagecodecs",
        "--collect-submodules=imagecodecs",
        "--copy-metadata=imagecodecs",
        "src/shinestacker/app/main.py"
    ]
elif sys_name == 'windows':
    # Windows: Use --onedir to create folder structure
    pyinstaller_cmd = [
        "pyinstaller", "--onedir", "--windowed",
        f"--name={app_name}",
        f"--distpath={dist_dir}",
        "--paths=src",
        "--icon=src/shinestacker/gui/ico/shinestacker.ico",
        f"--collect-all={project_name}",
        "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
        "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}",
        "src/shinestacker/app/main.py"
    ]
else:
    # Linux: Use --onedir to create folder structure
    pyinstaller_cmd = [
        "pyinstaller", "--onedir",
        f"--name={app_name}",
        f"--distpath={dist_dir}",
        "--paths=src",
        f"--collect-all={project_name}",
        "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
        "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}",
        "src/shinestacker/app/main.py"
    ]

print(" ".join(pyinstaller_cmd))
subprocess.run(pyinstaller_cmd, check=True)

if sys_name == 'windows':
    # For Windows, package the folder created by --onedir
    shutil.make_archive(
        base_name=str(dist_dir / "shinestacker-release"),
        format="zip",
        root_dir=dist_dir,
        base_dir=app_name
    )
elif sys_name == 'darwin':
    app_bundle = dist_dir / f"{app_name}.app"
    if app_bundle.exists():
        dmg_temp_dir = dist_dir / "dmg_temp"
        if dmg_temp_dir.exists():
            shutil.rmtree(dmg_temp_dir)
        dmg_temp_dir.mkdir(exist_ok=True)
        shutil.copytree(app_bundle, dmg_temp_dir / app_bundle.name, dirs_exist_ok=True)
        os.symlink("/Applications", dmg_temp_dir / "Applications")
        dmg_path = dist_dir / f"{app_name}-release.dmg"
        dmg_cmd = [
            "hdiutil", "create",
            "-volname", app_name,
            "-srcfolder", str(dmg_temp_dir),
            "-ov", str(dmg_path),
            "-format", "UDBZ",
            "-fs", "HFS+"
        ]
        print("Creating DMG...")
        subprocess.run(dmg_cmd, check=True)
        print(f"Created DMG: {dmg_path.name}")
        shutil.rmtree(dmg_temp_dir)
        archive_path = dist_dir / "shinestacker-release.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(app_bundle, arcname=app_bundle.name, recursive=True)
        print(f"Also created tar.gz: {archive_path.name}")
    else:
        print(f"ERROR: .app bundle not found at {app_bundle}")
else:
    # For Linux, package the folder created by --onedir
    archive_path = dist_dir / "shinestacker-release.tar.gz"
    linux_app_dir = dist_dir / app_name
    if linux_app_dir.exists():
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(
                linux_app_dir,
                arcname=app_name,
                recursive=True
            )
        print(f"Packaged Linux application: {app_name}")
    else:
        print(f"ERROR: Linux app directory not found at {linux_app_dir}")

if sys_name == 'windows':
    print("=== CREATING WINDOWS INSTALLER ===")
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    iscc_exe = None
    for path in inno_paths:
        if os.path.exists(path):
            iscc_exe = path
            print(f"Found Inno Setup at: {path}")
            break
    if not iscc_exe:
        print("Inno Setup not found in standard locations. Checking for Chocolatey...")
        try:
            subprocess.run(["choco", "--version"], check=True, capture_output=True)
            print("Installing Inno Setup via Chocolatey...")
            subprocess.run(["choco", "install", "innosetup", "-y",
                            "--no-progress", "--accept-license"], check=True)
            for path in inno_paths:
                if os.path.exists(path):
                    iscc_exe = path
                    print(f"Found Inno Setup at: {path}")
                    break
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Chocolatey not available or installation failed.")
    if iscc_exe:
        iss_script_source = project_root / "scripts" / "shinestacker-inno-setup.iss"
        iss_script_temp = project_root / "shinestacker-inno-setup.iss"
        if iss_script_source.exists():
            version_file = project_root / "src" / "shinestacker" / "_version.py"
            version = "0.0.0"  # fallback
            if version_file.exists():
                with open(version_file, 'r') as f:
                    content = f.read()
                    import re
                    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
                    if match:
                        version = match.group(1)
                        print(f"Found version: {version}")
                    else:
                        print("WARNING: Could not extract version from _version.py, using fallback")
            with open(iss_script_source, 'r') as f:
                iss_content = f.read()
            old_version_line = f'#define MyAppVersion "{"x.x.x"}"'
            new_version_line = f'#define MyAppVersion "{version}"'
            iss_content = iss_content.replace(old_version_line, new_version_line)
            with open(iss_script_temp, 'w') as f:
                f.write(iss_content)
            print(f"Updated ISS script with version: {version}")
            print(f"Compiling installer with: {iscc_exe}")
            subprocess.run([iscc_exe, str(iss_script_temp)], check=True)
            print("Removing temporary ISS script")
            iss_script_temp.unlink()
            if dist_dir.exists():
                installer_files = list(dist_dir.glob("*.exe"))
                if installer_files:
                    print(f"Installer created: {installer_files[0].name}")
        else:
            print(f"ISS script not found at: {iss_script_source}")
    else:
        print("WARNING: Could not find or install Inno Setup. Skipping installer creation.")
        print("You can manually install Inno Setup from: https://jrsoftware.org/isdl.php")
        print("Or install Chocolatey and run: choco install innosetup -y")
