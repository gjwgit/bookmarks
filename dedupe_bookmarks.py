import json
import os
from datetime import datetime
from collections import defaultdict

def get_timestamp(details):
    """Safely get timestamp from bookmark details."""
    try:
        # Try last_modified first
        if details.get('last_modified'):
            timestamp = int(details['last_modified'])
            if timestamp > 0:
                return timestamp

        # Try added timestamp
        if details.get('added'):
            timestamp = int(details['added'])
            if timestamp > 0:
                return timestamp

        # Return default timestamp if none found
        return 0
    except (ValueError, TypeError):
        # Return default timestamp if conversion fails
        return 0

def remove_duplicates(input_file='./bookmarks_unified.json', output_file=None):
    """
    Remove duplicate bookmarks from unified JSON file based on URLs.
    Keeps the most recently modified entry when duplicates are found.
    """
    input_path = os.path.expanduser(input_file)
    if output_file is None:
        output_file = input_path.replace('.json', '_deduped.json')
    output_path = os.path.expanduser(output_file)

    # Read the unified bookmarks file
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Group bookmarks by URL
    url_groups = defaultdict(list)
    for path, details in data['bookmarks'].items():
        # Skip entries without URLs
        if not details.get('url'):
            continue
        url_groups[details['url']].append((path, details))

    # Process duplicates and create new bookmarks dictionary
    new_bookmarks = {}
    duplicates_removed = []

    for url, entries in url_groups.items():
        if len(entries) > 1:
            # Sort by timestamp, using our safe timestamp getter
            sorted_entries = sorted(
                entries,
                key=lambda x: get_timestamp(x[1]),
                reverse=True
            )

            # Keep the most recent entry
            kept_path, kept_details = sorted_entries[0]
            new_bookmarks[kept_path] = kept_details

            # Record removed duplicates
            for removed_path, _ in sorted_entries[1:]:
                duplicates_removed.append({
                    'url': url,
                    'kept_path': kept_path,
                    'removed_path': removed_path
                })
        else:
            # No duplicates for this URL
            path, details = entries[0]
            new_bookmarks[path] = details

    # Create new output data
    output_data = {
        'bookmarks': new_bookmarks,
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'original_count': len(data['bookmarks']),
            'deduped_count': len(new_bookmarks),
            'duplicates_removed': len(duplicates_removed),
            'deduplication_date': datetime.now().isoformat()
        },
        'removed_duplicates': duplicates_removed
    }

    # Save the deduplicated bookmarks
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    return output_path, len(duplicates_removed)

def main():
    try:
        print("Starting bookmark deduplication...")

        output_path, duplicates_count = remove_duplicates()

        print(f"\nDuplication removal complete:")
        print(f"- Removed {duplicates_count} duplicate bookmarks")
        print(f"- Saved deduplicated bookmarks to: {output_path}")
        print("\nYou can review the removed duplicates in the 'removed_duplicates' section of the output file")

        # Provide a command to view the results
        print("\nTo view the results, you can use:")
        print(f"jq '.metadata' {output_path}")
        print("or")
        print(f"jq '.removed_duplicates[]' {output_path}")

    except Exception as e:
        print(f"Error: {str(e)}")
        # Print more detailed error information
        import traceback
        print("\nDetailed error information:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
