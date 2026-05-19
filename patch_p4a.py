import sys
import os

p4a_dir = sys.argv[1] if len(sys.argv) > 1 else 'p4a_local'
template = os.path.join(
    p4a_dir, 'pythonforandroid', 'bootstraps',
    'common', 'build', 'build.py'
)

with open(template) as fh:
    content = fh.read()

old = (
    "    with open('project.properties', 'r') as fileh:\n"
    "        target = fileh.read().strip()\n"
    "    android_api = target.split('-')[1]"
)

new = (
    "    with open('project.properties', 'r') as fileh:\n"
    "        for _l in fileh:\n"
    "            if _l.startswith('target='):\n"
    "                target = _l.strip().split('=')[1].split('-')[1]\n"
    "                break\n"
    "        else:\n"
    "            raise ValueError('No target= line in project.properties')\n"
    "    android_api = target"
)

if old in content:
    content = content.replace(old, new)
    with open(template, 'w') as fh:
        fh.write(content)
    print(f"Patched: {template}")
else:
    print(f"ERROR: old code not found in {template}")
    for i, line in enumerate(content.split('\n'), 1):
        if 'fileh.read()' in line:
            print(f"  Line {i}: {repr(line)}")
            if i > 1:
                print(f"  Prev line {i-1}: {repr(content.split(chr(10))[i-2])}")
    sys.exit(1)
