import os
import shutil
import zipfile
from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps


class Command(BaseCommand):
    help = ('Copies static files from STATIC_ROOT directory to REQUIRED_STATIC_FILES directory, '
            'excluding node_modules and only including files from installed apps, js18, webpack, and webpack_b3')

    def handle(self, *args, **options):
        static_root = settings.STATIC_ROOT

        if not static_root:
            self.stderr.write("STATIC_ROOT is not configured")
            return

        REQUIRED_STATIC_FILES_DIR = 'REQUIRED_STATIC_FILES'
        # Create STATIC_FILTERED directory in project root
        static_filtered = os.path.join(settings.BASE_DIR, REQUIRED_STATIC_FILES_DIR)

        # Create directory if it doesn't exist, or clean it if it does
        if os.path.exists(static_filtered):
            shutil.rmtree(static_filtered)
        os.makedirs(static_filtered)

        def get_app_name(app_path):
            """Extract the final app name from a Python path."""
            # Handle both string paths and config objects
            if hasattr(app_path, 'name'):
                app_path = app_path.name
            # Split on dots and get the last part
            parts = app_path.split('.')

            # Handle special cases like 'django.contrib.admin' -> 'admin'
            if 'contrib' in parts:
                return parts[-1]

            # Handle cases like 'corehq.apps.users' -> 'users'
            if 'apps' in parts:
                return parts[-1]

            # Default to last part of path
            return parts[-1]

        # Get list of installed app paths
        installed_apps = {get_app_name(app.name): app.path for app in apps.get_app_configs()}
        print(installed_apps)
        # Additional directories to copy
        additional_dirs = ['jsi18n', 'webpack', 'webpack_b3', 'CACHE']

        files_to_copy = ['build.b3.js', 'build.b3.txt', 'build.b5.js', 'build.b5.txt', 'build.js', 'build.txt']

        def should_copy_directory(dir_name):
            # Skip node_modules
            if 'node_modules' in dir_name:
                return False

            # Check if directory is an installed app
            if dir_name in installed_apps:
                return True

            # Check if directory is in additional_dirs
            if dir_name in additional_dirs:
                return True

            return False

        def copy_directory(src, dst):
            if not os.path.exists(dst):
                os.makedirs(dst)

            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)

                if os.path.isdir(s):
                    if 'node_modules' not in s:
                        copy_directory(s, d)
                else:
                    if not os.path.exists(os.path.dirname(d)):
                        os.makedirs(os.path.dirname(d))
                    shutil.copy2(s, d)

        # Copy files
        copied_count = 0
        for item in os.listdir(static_root):
            src_path = os.path.join(static_root, item)
            dst_path = os.path.join(static_filtered, item)

            if os.path.isdir(src_path) and should_copy_directory(item):
                self.stdout.write(f"Copying {item}...")
                copy_directory(src_path, dst_path)
                copied_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully copied {copied_count} directories to {static_filtered}'
        ))

        # copy files to copy
        for file in files_to_copy:
            src_path = os.path.join(static_root, file)
            dst_path = os.path.join(static_filtered, file)
            shutil.copy2(src_path, dst_path)

        # Print total size of copied files
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(static_filtered):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        # Create zip file of static_filtered directory
        zip_path = f"{static_filtered}.zip"
        self.stdout.write(f"Creating zip file at {zip_path}...")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(static_filtered):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, static_filtered)
                    zipf.write(file_path, arcname)

        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(
            f'Successfully created zip file ({zip_size:.2f} MB)'
        ))

        self.stdout.write(self.style.SUCCESS(
            f'Total size of copied files: {total_size / (1024*1024):.2f} MB'
        ))
