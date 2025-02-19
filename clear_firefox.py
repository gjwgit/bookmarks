import sqlite3
import os
from pathlib import Path
import shutil
from datetime import datetime
import subprocess

# def is_firefox_running():
#     try:
#         # Using pgrep to search for firefox process
#         subprocess.check_output(["pgrep", "firefox"])
#         return True
#     except subprocess.CalledProcessError:
#         # Process not found
#         return False

def is_firefox_running():
    try:
        # Get PIDs of Firefox processes
        pids = subprocess.check_output(["pgrep", "firefox"]).decode().strip().split('\n')

        for pid in pids:
            # Check state of each process
            state = subprocess.check_output(["ps", "-o", "stat=", "-p", pid]).decode().strip()
            if 'Z' not in state:
                return True  # Found at least one non-zombie Firefox
        return False
    except subprocess.CalledProcessError:
        return False  # No Firefox processes found

def clear_firefox_bookmarks():
    """Clear all Firefox bookmarks but preserve the essential structure."""

    # Find Firefox profile directory
    standard_path = os.path.expanduser('~/.mozilla/firefox')
    snap_path = os.path.expanduser('~/snap/firefox/common/.mozilla/firefox')

    profile_paths = [p for p in [standard_path, snap_path] if os.path.exists(p)]

    if not profile_paths:
        raise FileNotFoundError("Firefox profile directory not found")

    profile = None
    for base_path in profile_paths:
        try:
            # First try to find default-release profile
            profile = next(Path(base_path).glob('*.default-release'), None)
            if profile is None:
                # If not found, try default profile
                profile = next(Path(base_path).glob('*.default'), None)
            if profile is None:
                # If still not found, try any .profile directory
                profile = next(Path(base_path).glob('*.profile'))
            if profile:
                break
        except StopIteration:
            continue

    if not profile:
        raise FileNotFoundError("Firefox profile not found")

    db_path = os.path.join(profile, 'places.sqlite')

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"Created backup at: {backup_path}")

    # Create temporary copy to work with
    temp_db = f'/tmp/places_temp_{timestamp}.sqlite'
    shutil.copy2(db_path, temp_db)

    try:
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")

        try:
            # Delete all bookmarks except essential folders
            # This preserves the root folders but removes all user bookmarks
            cursor.execute("""
                DELETE FROM moz_bookmarks
                WHERE id NOT IN (
                    SELECT id FROM moz_bookmarks
                    WHERE guid IN (
                        'root________',  -- root folder
                        'toolbar_____',  -- bookmarks toolbar
                        'menu________',  -- bookmarks menu
                        'mobile______',  -- mobile bookmarks
                        'unfiled_____'   -- other bookmarks
                    )
                )
            """)

            # Clean up orphaned URLs
            cursor.execute("""
                DELETE FROM moz_places
                WHERE id NOT IN (
                    SELECT fk
                    FROM moz_bookmarks
                    WHERE fk IS NOT NULL
                )
            """)

            # Commit the changes
            cursor.execute("COMMIT")

        except Exception as e:
            # If anything goes wrong, roll back
            cursor.execute("ROLLBACK")
            raise e

        finally:
            conn.close()

        # If everything succeeded, copy the modified database back
        shutil.copy2(temp_db, db_path)
        print("Successfully cleared all bookmarks")
        print(f"Backup saved at: {backup_path}")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_db):
            os.remove(temp_db)

def main():
    confirmation = 'yes'

    if is_firefox_running():
        print("WARNING: This will delete all Firefox bookmarks!")
        print("A backup will be created, but please make sure Firefox is closed.")
        confirmation = input("Are you sure you want to proceed? (type 'yes' to confirm): ")

    if confirmation.lower() == 'yes':
        try:
            clear_firefox_bookmarks()
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("Firefox bookmarks removal cancelled.")
        exit(1)

if __name__ == "__main__":
    main()
