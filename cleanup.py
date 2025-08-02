
import os
import shutil

# Keep track of the current directory
current_directory = os.getcwd()

# List of files and directories to keep
keep_list = [
    os.path.join(current_directory, 'src'),
    os.path.join(current_directory, 'tests'),
    os.path.join(current_directory, '.git'),
    os.path.join(current_directory, '.github'),
    os.path.join(current_directory, 'cleanup.py')
]

# Iterate over all files and directories in the current directory
for item in os.listdir(current_directory):
    item_path = os.path.join(current_directory, item)
    # If the item is not in the keep list, delete it
    if item_path not in keep_list:
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                os.system(f'rmdir /s /q "{item_path}')
        except Exception as e:
            print(f'Error deleting {item_path}: {e}')

print('Cleanup complete.')
