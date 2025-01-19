from pathlib import Path
import json
import sqlite3
import os
import shutil
from datetime import datetime
import time

class BookmarkImporter:
    def __init__(self, unified_bookmarks_path):
        with open(unified_bookmarks_path, 'r', encoding='utf-8') as f:
            self.unified_data = json.load(f)

    def backup_file(self, file_path):
        """Create a backup of a file with timestamp."""
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{int(time.time())}"
            shutil.copy2(file_path, backup_path)
            print(f"Created backup at: {backup_path}")
            return backup_path
        return None

    def import_to_brave(self):
        """Import unified bookmarks to Brave."""
        # Get Brave bookmarks path
        brave_path = os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/Bookmarks')
        snap_path = os.path.expanduser('~/snap/brave/current/.config/BraveSoftware/Brave-Browser/Default/Bookmarks')

        brave_bookmarks_path = snap_path if os.path.exists(snap_path) else brave_path

        if not os.path.exists(brave_bookmarks_path):
            raise FileNotFoundError("Brave bookmarks file not found")

        # Create backup
        self.backup_file(brave_bookmarks_path)

        # Read current Brave bookmarks structure
        with open(brave_bookmarks_path, 'r', encoding='utf-8') as f:
            brave_data = json.load(f)

        # Create new bookmark structure
        bookmark_bar = {
            "children": [],
            "date_added": str(int(time.time() * 1000000)),
            "date_modified": str(int(time.time() * 1000000)),
            "guid": "bookmark_bar",
            "id": "1",
            "name": "Bookmarks bar",
            "type": "folder"
        }

        # Convert unified bookmarks to Brave format
        for path, details in self.unified_data['bookmarks'].items():
            folders = path.split('/')
            current_folder = bookmark_bar['children']

            # Navigate through folders
            for i, folder_name in enumerate(folders[:-1]):
                # Find or create folder
                folder = next((f for f in current_folder if f['type'] == 'folder' and f['name'] == folder_name), None)
                if not folder:
                    folder = {
                        "children": [],
                        "date_added": str(int(time.time() * 1000000)),
                        "date_modified": str(int(time.time() * 1000000)),
                        "guid": f"folder_{time.time()}_{i}",
                        "id": str(int(time.time()) + i),
                        "name": folder_name,
                        "type": "folder"
                    }
                    current_folder.append(folder)
                current_folder = folder['children']

            # Add bookmark
            current_folder.append({
                "date_added": str(details.get('added', int(time.time() * 1000000))),
                "guid": f"bookmark_{time.time()}",
                "id": str(int(time.time())),
                "name": folders[-1],
                "type": "url",
                "url": details['url']
            })

        # Update Brave bookmarks structure
        brave_data['roots']['bookmark_bar'] = bookmark_bar

        # Write back to file
        with open(brave_bookmarks_path, 'w', encoding='utf-8') as f:
            json.dump(brave_data, f, indent=2)

        print("Brave bookmarks updated successfully")

    def import_to_firefox(self):
        """Import unified bookmarks to Firefox."""
        # Get Firefox profile path
        standard_path = os.path.expanduser('~/.mozilla/firefox')
        snap_path = os.path.expanduser('~/snap/firefox/common/.mozilla/firefox')

        profile_paths = [p for p in [standard_path, snap_path] if os.path.exists(p)]

        if not profile_paths:
            raise FileNotFoundError("Firefox profile directory not found")

        for base_path in profile_paths:
            try:
                profile = next(p for p in Path(base_path).glob('*.default*'))
                break
            except StopIteration:
                continue

        db_path = os.path.join(profile, 'places.sqlite')

        # Create backup
        self.backup_file(db_path)

        # Create temporary copy of database
        temp_db = f'/tmp/places_temp_{int(time.time())}.sqlite'
        shutil.copy2(db_path, temp_db)

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Clear existing bookmarks (keeping essential folders)
            cursor.execute("DELETE FROM moz_bookmarks WHERE type = 1 AND parent > 2")

            # Get the bookmark toolbar folder id
            cursor.execute("SELECT id FROM moz_bookmarks WHERE guid = 'toolbar_____'")
            toolbar_id = cursor.fetchone()[0]

            # Function to ensure folder exists
            def ensure_folder(name, parent_id):
                cursor.execute("""
                    SELECT id FROM moz_bookmarks
                    WHERE type = 2 AND parent = ? AND title = ?
                """, (parent_id, name))
                result = cursor.fetchone()
                if result:
                    return result[0]

                cursor.execute("""
                    INSERT INTO moz_bookmarks (type, parent, title, dateAdded, lastModified)
                    VALUES (2, ?, ?, ?, ?)
                """, (parent_id, name, int(time.time() * 1000000), int(time.time() * 1000000)))
                return cursor.lastrowid

            # Import bookmarks
            for path, details in self.unified_data['bookmarks'].items():
                folders = path.split('/')
                current_parent = toolbar_id

                # Create folder structure
                for folder_name in folders[:-1]:
                    current_parent = ensure_folder(folder_name, current_parent)

                # Add URL to moz_places if it doesn't exist
                cursor.execute("""
                    INSERT OR IGNORE INTO moz_places (url, title)
                    VALUES (?, ?)
                """, (details['url'], folders[-1]))

                # Get place_id
                cursor.execute("SELECT id FROM moz_places WHERE url = ?", (details['url'],))
                place_id = cursor.fetchone()[0]

                # Add bookmark
                cursor.execute("""
                    INSERT INTO moz_bookmarks (type, fk, parent, title, dateAdded, lastModified)
                    VALUES (1, ?, ?, ?, ?, ?)
                """, (place_id, current_parent, folders[-1],
                      details.get('added', int(time.time() * 1000000)),
                      details.get('last_modified', int(time.time() * 1000000))))

            conn.commit()
            conn.close()

            # Replace original database
            shutil.copy2(temp_db, db_path)
            print("Firefox bookmarks updated successfully")

        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

def main():
    try:
        # Default path for unified bookmarks
        unified_bookmarks_path = os.path.expanduser('bookmarks.json')

        if not os.path.exists(unified_bookmarks_path):
            print(f"Error: Unified bookmarks file not found at {unified_bookmarks_path}")
            return

        print(f"Importing bookmarks from {unified_bookmarks_path}\n")

        print("Creating backups before importing...")
        importer = BookmarkImporter(unified_bookmarks_path)

        print("\nImporting to Brave...")
        importer.import_to_brave()

        print("\nImporting to Firefox...")
        importer.import_to_firefox()

        print("\nBookmark import completed successfully!")
        print("Please restart your browsers to see the changes.")

    except Exception as e:
        print(f"Error during import: {str(e)}")

if __name__ == "__main__":
    main()
