import os
import shutil
import subprocess
from pathlib import Path

def create_macos_icon():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    png_source = project_root / "src" / "shinestacker" / "gui" / "ico" / "shinestacker.png"
    icns_output = project_root / "src" / "shinestacker" / "gui" / "ico" / "shinestacker.icns"
    
    if not png_source.exists():
        print(f"ERROR: Source PNG not found at {png_source}")
        return False
        
    print(f"Creating macOS icon from {png_source}")
    
    iconset_dir = project_root / "src" / "shinestacker" / "gui" / "ico" / "shinestacker.iconset"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir()
    
    sizes = [
        ("16x16", 16),
        ("16x16@2x", 32),
        ("32x32", 32), 
        ("32x32@2x", 64),
        ("128x128", 128),
        ("128x128@2x", 256),
        ("256x256", 256),
        ("256x256@2x", 512),
        ("512x512", 512),
        ("512x512@2x", 1024)
    ]
    
    for name, size in sizes:
        output_file = iconset_dir / f"icon_{name}.png"
        print(f"  Creating {name}...")
        subprocess.run([
            "sips", "-z", str(size), str(size), 
            str(png_source), 
            "--out", str(output_file)
        ], check=True)
    
    print("Converting to .icns format...")
    subprocess.run([
        "iconutil", "-c", "icns", 
        str(iconset_dir), 
        "-o", str(icns_output)
    ], check=True)
    
    shutil.rmtree(iconset_dir)
    print(f"SUCCESS: Created {icns_output}")
    return True


if __name__ == "__main__":
    create_macos_icon()
