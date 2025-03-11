import PyInstaller.__main__
import sys
import os
import subprocess

def build():
    # Get the absolute path to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    main_file = os.path.join(project_root, 'main.py')
    resources_dir = os.path.join(project_root, 'resources')
    icon_file = os.path.join(project_root, 'icon.ico')
    
    # Force Intel architecture for Python
    if sys.platform == 'darwin':
        os.environ['ARCHFLAGS'] = '-arch x86_64'
        # Check if running on Apple Silicon
        arch = subprocess.check_output(['uname', '-m']).decode('utf-8').strip()
        if arch == 'arm64':
            print("Warning: Building on Apple Silicon. Using x86_64 architecture for compatibility.")
            # Use x86_64 Python if available
            intel_python = '/usr/local/bin/python3'
            if os.path.exists(intel_python):
                print(f"Using Intel Python at {intel_python}")
                args = [intel_python, '-m', 'PyInstaller']
            else:
                print("Intel Python not found. Please install Python for Intel Mac.")
                print("You can install it using: arch -x86_64 brew install python@3.11")
                return
        
    # Base arguments
    args = [
        main_file,
        '--onefile',
        '--name=KB_Logistik',
        '--clean',
        '--noconsole',
        '--target-arch=x86_64'  # Force Intel architecture
    ]

    # Add resources if the directory exists
    if os.path.exists(resources_dir):
        if sys.platform == 'darwin':  # macOS
            args.append(f'--add-data={resources_dir}:resources')
        else:  # Windows
            args.append(f'--add-data={resources_dir};resources')
    else:
        print(f"Warning: Resources directory not found at {resources_dir}")
        print("Creating resources directory...")
        os.makedirs(resources_dir)

    # Add icon if exists
    if os.path.exists(icon_file):
        args.append(f'--icon={icon_file}')
    
    print("Building with arguments:", args)
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build()