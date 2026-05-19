import os


def before_apk_build(tc):
    """Fix project.properties before build.py reads it.
    Runs inside the dist directory (CWD = dist_dir).
    """
    prop_file = 'project.properties'

    android_api = getattr(tc.ctx, 'android_api', 34)
    if not android_api:
        android_api = 34

    if not os.path.exists(prop_file):
        with open(prop_file, 'w') as f:
            f.write(f'target=android-{android_api}\n')
        print(f"Hook: Created project.properties (target=android-{android_api})")
        return

    with open(prop_file, 'r') as f:
        lines = f.readlines()

    target_lines = [l for l in lines if l.startswith('target=')]
    if target_lines:
        with open(prop_file, 'w') as f:
            f.write(target_lines[0].strip() + '\n')
        print(f"Hook: Fixed project.properties -> {target_lines[0].strip()}")
    else:
        with open(prop_file, 'w') as f:
            f.write(f'target=android-{android_api}\n')
        print(f"Hook: Rewrote project.properties (target=android-{android_api})")
