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

pyinstaller_cmd = [
    "pyinstaller", "--onedir", f"--name={app_name}", "--paths=src",
    f"--distpath=dist/{package_dir}", f"--collect-all={project_name}",
    "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
    "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}"
]
if sys_name == 'darwin':
    pyinstaller_cmd += ["--windowed", "--icon=src/shinestacker/gui/ico/shinestacker.icns"]
elif sys_name == 'windows':
    pyinstaller_cmd += ["--windowed", "--icon=src/shinestacker/gui/ico/shinestacker.ico"]
pyinstaller_cmd += ["src/shinestacker/app/main.py"]

print(" ".join(pyinstaller_cmd))
subprocess.run(pyinstaller_cmd, check=True)

# examples_dir = project_root / "examples"
# target_examples = dist_dir / package_dir / "examples"
# target_examples.mkdir(exist_ok=True)
# for project_file in ["complete-project.fsp", "stack-from-frames.fsp"]:
#     shutil.copy(examples_dir / project_file, target_examples)
#    shutil.copytree(examples_dir / 'input', target_examples / 'input', dirs_exist_ok=True)

if sys_name == 'windows':
    shutil.make_archive(
        base_name=str(dist_dir / "shinestacker-release"),
        format="zip",
        root_dir=dist_dir,
        base_dir=package_dir
    )
else:
    archive_path = dist_dir / "shinestacker-release.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(
            dist_dir / package_dir,
            arcname=package_dir,
            recursive=True,
            filter=lambda info: info
        )

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
            subprocess.run(["choco", "install", "innosetup", "-y", "--no-progress", "--accept-license"], check=True)
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
            print(f"Copying ISS script to project root: {iss_script_temp}")
            shutil.copy2(iss_script_source, iss_script_temp)
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
