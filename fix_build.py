import os
import sys

def fix_build_py(path):
    """Fix project.properties parsing in build.py to handle multi-line files."""
    with open(path, 'r') as f:
        content = f.read()

    old = (
        "        target = fileh.read().strip()\n"
        "    android_api = target.split('-')[1]"
    )

    # Debug: check if the exact string is found
    if old not in content:
        # Try finding the lines
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'fileh.read().strip()' in line:
                print(f"DEBUG: Found 'fileh.read().strip()' at line {i+1}: repr={repr(line)}")
                if i + 1 < len(lines):
                    print(f"DEBUG: Next line {i+2}: repr={repr(lines[i+1])}")
    new = (
        "        for _l in fileh:\n"
        "            if _l.startswith('target='):\n"
        "                target = _l.strip().split('=')[1].split('-')[1]\n"
        "                break\n"
        "    android_api = target"
    )

    if old in content:
        content = content.replace(old, new)
        with open(path, 'w') as f:
            f.write(content)
        print(f"Fixed: {path}")
        return True
    else:
        # Try with different indentation
        for indent in ['    ', '\t']:
            old2 = (
                f"{indent}    target = fileh.read().strip()\n"
                f"{indent}android_api = target.split('-')[1]"
            )
            if old2 in content:
                new2 = (
                    f"{indent}    for _l in fileh:\n"
                    f"{indent}        if _l.startswith('target='):\n"
                    f"{indent}            target = _l.strip().split('=')[1].split('-')[1]\n"
                    f"{indent}            break\n"
                    f"{indent}android_api = target"
                )
                content = content.replace(old2, new2)
                with open(path, 'w') as f:
                    f.write(content)
                print(f"Fixed: {path}")
                return True
        print(f"ERROR: Could not find target code in {path}")
        return False


def fix_project_properties(path):
    """Remove extra lines from project.properties, keep only target line."""
    if not os.path.exists(path):
        print(f"project.properties not found at {path}")
        return False

    with open(path, 'r') as f:
        lines = f.readlines()

    # Keep only the target line
    target_lines = [l for l in lines if l.startswith('target=')]
    if not target_lines:
        print(f"ERROR: No target= line found in {path}")
        return False

    with open(path, 'w') as f:
        f.write(target_lines[0].strip() + '\n')
    print(f"Fixed project.properties: {path}")
    return True


def clear_pycache(dir_path):
    """Remove __pycache__ directories and .pyc files to invalidate bytecode cache."""
    for root, dirs, files in os.walk(dir_path):
        for d in dirs:
            if d == '__pycache__':
                cache_dir = os.path.join(root, d)
                for f in os.listdir(cache_dir):
                    os.remove(os.path.join(cache_dir, f))
                os.rmdir(cache_dir)
                print(f"Removed __pycache__: {cache_dir}")
        for f in files:
            if f.endswith('.pyc'):
                os.remove(os.path.join(root, f))
                print(f"Removed .pyc: {os.path.join(root, f)}")


if __name__ == '__main__':
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())

    # Clear any Python bytecode cache in p4a directory first
    p4a_dir = os.path.join(
        workspace, '.buildozer', 'android', 'platform',
        'python-for-android'
    )
    if os.path.exists(p4a_dir):
        clear_pycache(p4a_dir)

    # Fix template
    template = os.path.join(
        p4a_dir, 'pythonforandroid', 'bootstraps',
        'common', 'build', 'build.py'
    )
    if os.path.exists(template):
        fix_build_py(template)
        # Also clear cache in the build directory
        build_dir = os.path.dirname(template)
        clear_pycache(build_dir)

    # Fix dist files
    dist_dir = os.path.join(
        workspace, '.buildozer', 'android', 'platform',
        'build-arm64-v8a', 'dists', 'snakegame'
    )
    dist_build_py = os.path.join(dist_dir, 'build.py')
    dist_props = os.path.join(dist_dir, 'project.properties')

    if os.path.exists(dist_build_py):
        fix_build_py(dist_build_py)
    if os.path.exists(dist_props):
        fix_project_properties(dist_props)
