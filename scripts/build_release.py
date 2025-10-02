import os
import shutil
import tarfile
import subprocess
from pathlib import Path
import platform


def setup_environment():
    os.chdir("../")
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist"
    project_name = "shinestacker"
    app_name = "shinestacker"
    hooks_dir = "scripts/hooks"
    hook_files = list(Path(hooks_dir).glob("hook-*.py"))
    for hook in hook_files:
        print(f"  - {hook.name}")
    return project_root, dist_dir, project_name, app_name


def build_pyinstaller_command(sys_name, dist_dir, project_name, app_name, hooks_dir):
    if sys_name == 'darwin':
        return [
            "pyinstaller", "--windowed",
            f"--name={app_name}",
            f"--distpath={dist_dir}",
            "--paths=src",
            "--icon=src/shinestacker/gui/ico/shinestacker.icns",
            f"--additional-hooks-dir={hooks_dir}",
            f"--collect-all={project_name}",
            "--collect-data=imagecodecs",
            "--collect-submodules=imagecodecs",
            "--copy-metadata=imagecodecs",
            "src/shinestacker/app/main.py"
        ]
    elif sys_name == 'windows':
        return [
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
        return [
            "pyinstaller", "--onedir",
            f"--name={app_name}",
            f"--distpath={dist_dir}",
            "--paths=src",
            f"--collect-all={project_name}",
            "--collect-data=imagecodecs", "--collect-submodules=imagecodecs",
            "--copy-metadata=imagecodecs", f"--additional-hooks-dir={hooks_dir}",
            "src/shinestacker/app/main.py"
        ]


def package_windows(dist_dir, app_name):
    shutil.make_archive(
        base_name=str(dist_dir / "shinestacker-release"),
        format="zip",
        root_dir=dist_dir,
        base_dir=app_name
    )


def package_macos(dist_dir, app_name, project_root):
    app_bundle = dist_dir / f"{app_name}.app"
    if not app_bundle.exists():
        print(f"ERROR: .app bundle not found at {app_bundle}")
        return
    dmg_temp_dir = dist_dir / "dmg_temp"
    if dmg_temp_dir.exists():
        shutil.rmtree(dmg_temp_dir)
    shutil.copytree(app_bundle, dmg_temp_dir / app_bundle.name, symlinks=True)
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
    subprocess.run(dmg_cmd, check=True)
    print(f"Created DMG: {dmg_path.name}")
    shutil.rmtree(dmg_temp_dir)
    archive_path = dist_dir / "shinestacker-release.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(app_bundle, arcname=app_bundle.name, recursive=True)
    print(f"Created tar.gz: {archive_path.name}")


def package_linux(dist_dir, app_name):
    archive_path = dist_dir / "shinestacker-release.tar.gz"
    linux_app_dir = dist_dir / app_name
    if linux_app_dir.exists():
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(linux_app_dir, arcname=app_name, recursive=True)
        print(f"Packaged Linux application: {app_name}")
    else:
        print(f"ERROR: Linux app directory not found at {linux_app_dir}")


def create_windows_installer(project_root, dist_dir):
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
            break
    if not iscc_exe:
        try:
            subprocess.run(["choco", "--version"], check=True, capture_output=True)
            subprocess.run(["choco", "install", "innosetup", "-y",
                            "--no-progress", "--accept-license"], check=True)
            for path in inno_paths:
                if os.path.exists(path):
                    iscc_exe = path
                    break
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    if iscc_exe:
        iss_script_source = project_root / "scripts" / "shinestacker-inno-setup.iss"
        iss_script_temp = project_root / "shinestacker-inno-setup.iss"
        if iss_script_source.exists():
            version_file = project_root / "src" / "shinestacker" / "_version.py"
            version = "0.0.0"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    content = f.read()
                    import re
                    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
                    if match:
                        version = match.group(1)
            with open(iss_script_source, 'r') as f:
                iss_content = f.read()
            old_version_line = f'#define MyAppVersion "{"x.x.x"}"'
            new_version_line = f'#define MyAppVersion "{version}"'
            iss_content = iss_content.replace(old_version_line, new_version_line)
            with open(iss_script_temp, 'w') as f:
                f.write(iss_content)
            subprocess.run([iscc_exe, str(iss_script_temp)], check=True)
            iss_script_temp.unlink()
            if dist_dir.exists():
                installer_files = list(dist_dir.glob("*.exe"))
                if installer_files:
                    print(f"Installer created: {installer_files[0].name}")


def main():
    project_root, dist_dir, project_name, app_name = setup_environment()
    sys_name = platform.system().lower()
    hooks_dir = "scripts/hooks"
    pyinstaller_cmd = build_pyinstaller_command(
        sys_name, dist_dir, project_name, app_name, hooks_dir)
    print(" ".join(pyinstaller_cmd))
    subprocess.run(pyinstaller_cmd, check=True)
    if sys_name == 'windows':
        package_windows(dist_dir, app_name)
    elif sys_name == 'darwin':
        package_macos(dist_dir, app_name, project_root)
    else:
        package_linux(dist_dir, app_name)
    if sys_name == 'windows':
        print("=== CREATING WINDOWS INSTALLER ===")
        create_windows_installer(project_root, dist_dir)


if __name__ == "__main__":
    main()
