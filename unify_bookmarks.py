import json
import sqlite3
import os
from pathlib import Path
import shutil
from datetime import datetime
import subprocess

class UbuntuBookmarkManager:
    def __init__(self):
        self.brave_bookmarks = {}
        self.firefox_bookmarks = {}

    def get_brave_bookmarks_path(self):
        """Get the Brave bookmarks file path for Ubuntu."""
        default_path = os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/Bookmarks')

        # Check if snap version is installed
        snap_path = os.path.expanduser('~/snap/brave/current/.config/BraveSoftware/Brave-Browser/Default/Bookmarks')

        if os.path.exists(snap_path):
            return snap_path
        elif os.path.exists(default_path):
            return default_path
        else:
            raise FileNotFoundError("Brave bookmarks file not found. Is Brave installed?")

    def get_firefox_profile_path(self):
        """Get the Firefox profile path for Ubuntu."""
        # Check both standard and snap installation paths
        standard_path = os.path.expanduser('~/.mozilla/firefox')
        snap_path = os.path.expanduser('~/snap/firefox/common/.mozilla/firefox')

        base_paths = [p for p in [standard_path, snap_path] if os.path.exists(p)]

        if not base_paths:
            raise FileNotFoundError("Firefox profile directory not found. Is Firefox installed?")

        for base_path in base_paths:
            try:
                # First try to find default-release profile
                profile = next(Path(base_path).glob('*.default-release'), None)
                if profile is None:
                    # If not found, try default profile
                    profile = next(Path(base_path).glob('*.default'), None)
                if profile is None:
                    # If still not found, try any .profile directory
                    profile = next(Path(base_path).glob('*.profile'))
                return str(profile)
            except StopIteration:
                continue

        raise Exception("Could not find Firefox profile directory")

    def ensure_browser_not_running(self):
        """Check if browsers are running and warn user if they are."""
        processes = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
        running_browsers = []

        if 'firefox' in processes:
            running_browsers.append('Firefox')
        if 'brave' in processes:
            running_browsers.append('Brave')

        if running_browsers:
            print("WARNING: The following browsers are running:", ", ".join(running_browsers))
            print("Please close them before proceeding to avoid database locks.")
            input("Press Enter to continue once browsers are closed...")

    def read_brave_bookmarks(self, file_path=None):
        """Read Brave bookmarks from the Bookmarks file."""
        if file_path is None:
            file_path = self.get_brave_bookmarks_path()

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        def process_brave_nodes(node, folder_path=""):
            if node.get('type') == 'url':
                full_path = f"{folder_path}/{node['name']}"
                self.brave_bookmarks[full_path] = {
                    'url': node['url'],
                    'added': node.get('date_added', ''),
                    'last_modified': node.get('date_modified', ''),
                    'folder': folder_path
                }
            elif node.get('type') == 'folder':
                new_path = f"{folder_path}/{node['name']}" if folder_path else node['name']
                for child in node.get('children', []):
                    process_brave_nodes(child, new_path)

        for root in ['bookmark_bar', 'other', 'synced']:
            if root in data['roots']:
                process_brave_nodes(data['roots'][root])

    def read_firefox_bookmarks(self, profile_path=None):
        """Read Firefox bookmarks from places.sqlite database."""
        if profile_path is None:
            profile_path = self.get_firefox_profile_path()

        db_path = os.path.join(profile_path, 'places.sqlite')

        # Create a copy of the database to avoid locks
        temp_dir = '/tmp'  # Use Ubuntu temp directory
        temp_db = os.path.join(temp_dir, f'places_temp_{datetime.now().strftime("%Y%m%d%H%M%S")}.sqlite')
        shutil.copy2(db_path, temp_db)

        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # First, let's check the column names in the database
            cursor.execute("PRAGMA table_info(moz_bookmarks)")
            columns = [column[1] for column in cursor.fetchall()]

            # Determine the correct column names based on what's in the database
            date_added_col = "dateAdded" if "dateAdded" in columns else "date_added"
            last_modified_col = "lastModified" if "lastModified" in columns else "last_modified"

            query = f"""
            WITH RECURSIVE
            bookmark_tree(id, title, url, parent, path, folder_path) AS (
                SELECT b.id, b.title, p.url, b.parent,
                       CAST(b.title AS TEXT) as path,
                       CAST('' AS TEXT) as folder_path
                FROM moz_bookmarks b
                LEFT JOIN moz_places p ON b.fk = p.id
                WHERE b.parent = 1

                UNION ALL

                SELECT b.id, b.title, p.url, b.parent,
                       bt.path || '/' || b.title,
                       CASE
                           WHEN p.url IS NOT NULL THEN bt.path
                           ELSE bt.path || '/' || b.title
                       END
                FROM moz_bookmarks b
                LEFT JOIN moz_places p ON b.fk = p.id
                JOIN bookmark_tree bt ON b.parent = bt.id
            ),
            final_bookmarks AS (
                SELECT
                    bt.path,
                    p.url,
                    b.{date_added_col},
                    b.{last_modified_col},
                    bt.folder_path
                FROM bookmark_tree bt
                JOIN moz_bookmarks b ON bt.id = b.id
                LEFT JOIN moz_places p ON b.fk = p.id
                WHERE p.url IS NOT NULL
            )
            SELECT * FROM final_bookmarks;
            """

            cursor.execute(query)
            for path, url, date_added, last_modified, folder_path in cursor.fetchall():
                if url:  # Only add entries that have a URL
                    self.firefox_bookmarks[path] = {
                        'url': url,
                        'added': date_added,
                        'last_modified': last_modified,
                        'folder': folder_path
                    }

            conn.close()
        except Exception as e:
            print(f"Error reading Firefox bookmarks: {str(e)}")
            print(f"Database path: {db_path}")
            raise
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)

    def compare_bookmarks(self):
        """Compare bookmarks between browsers and return differences."""
        brave_urls = {details['url'] for details in self.brave_bookmarks.values()}
        firefox_urls = {details['url'] for details in self.firefox_bookmarks.values()}

        only_in_brave = brave_urls - firefox_urls
        only_in_firefox = firefox_urls - brave_urls
        in_both = brave_urls & firefox_urls

        return {
            'only_in_brave': [
                {'path': path, 'details': details}
                for path, details in self.brave_bookmarks.items()
                if details['url'] in only_in_brave
            ],
            'only_in_firefox': [
                {'path': path, 'details': details}
                for path, details in self.firefox_bookmarks.items()
                if details['url'] in only_in_firefox
            ],
            'in_both': [
                {'path': path, 'details': details}
                for path, details in self.brave_bookmarks.items()
                if details['url'] in in_both
            ]
        }
    def export_separate_bookmarks(self, output_dir='./'):
        """Export Firefox and Brave bookmarks to separate JSON files."""
        output_dir = os.path.expanduser(output_dir)

        # Export Firefox bookmarks
        firefox_output = {
            'bookmarks': self.firefox_bookmarks,
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'bookmark_count': len(self.firefox_bookmarks)
            }
        }

        firefox_path = os.path.join(output_dir, 'bookmarks_firefox.json')
        with open(firefox_path, 'w', encoding='utf-8') as f:
            json.dump(firefox_output, f, indent=2)

        # Export Brave bookmarks
        brave_output = {
            'bookmarks': self.brave_bookmarks,
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'bookmark_count': len(self.brave_bookmarks)
            }
        }

        brave_path = os.path.join(output_dir, 'bookmarks_brave.json')
        with open(brave_path, 'w', encoding='utf-8') as f:
            json.dump(brave_output, f, indent=2)

        return firefox_path, brave_path

    def export_unified_bookmarks(self, output_file):
        """Export unified bookmarks to a JSON file."""
        unified = {
            'bookmarks': {
                **self.firefox_bookmarks,
                **self.brave_bookmarks  # Brave bookmarks will override duplicates
            },
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'brave_count': len(self.brave_bookmarks),
                'firefox_count': len(self.firefox_bookmarks)
            }
        }

        output_path = os.path.expanduser(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unified, f, indent=2)
        return output_path

def main():
    manager = UbuntuBookmarkManager()

    try:
        print("Checking if browsers are running...")
        manager.ensure_browser_not_running()

        print("\nReading Brave bookmarks...")
        manager.read_brave_bookmarks()
        print("Reading Firefox bookmarks...")
        manager.read_firefox_bookmarks()

        print("\nComparing bookmarks...")
        differences = manager.compare_bookmarks()

        print(f"\nFound {len(differences['only_in_brave'])} bookmarks only in Brave")
        print(f"Found {len(differences['only_in_firefox'])} bookmarks only in Firefox")
        print(f"Found {len(differences['in_both'])} bookmarks in both browsers")

        # Export separate bookmark files
        firefox_path, brave_path = manager.export_separate_bookmarks()
        print(f"\nFirefox bookmarks exported to: {firefox_path}")
        print(f"Brave bookmarks exported to: {brave_path}")

        # Export unified bookmarks
        output_file = './bookmarks_unified.json'
        unified_path = manager.export_unified_bookmarks(output_file)
        print(f"Unified bookmarks exported to: {unified_path}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
