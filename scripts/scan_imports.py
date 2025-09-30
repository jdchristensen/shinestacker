import ast
from pathlib import Path

def scan_imports():
    project_root = Path("../src/shinestacker")
    imports = {
        'PySide6': set(),
        'scipy': set(),
        'matplotlib': set(),
        'cv2': set(),
        'numpy': set(),
        'PIL': set()
    }
    
    for py_file in project_root.rglob("*.py"):
        with open(py_file, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
            except:
                continue
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for lib in imports.keys():
                        if lib in alias.name:
                            imports[lib].add(alias.name)            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for lib in imports.keys():
                        if lib in node.module:
                            imports[lib].add(node.module)
                            if node.names:
                                for alias in node.names:
                                    imports[lib].add(f"{node.module}.{alias.name}")
    return imports

def print_imports(imports):
    for lib, modules in imports.items():
        if modules:
            print(f"\n=== {lib.upper()} IMPORTS ===")
            for imp in sorted(modules):
                print(f"  {imp}")

if __name__ == "__main__":
    found_imports = scan_imports()
    print_imports(found_imports)
