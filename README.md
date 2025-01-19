## Manage Bookmarks

Claude 20250119

Use case - I swap between Firefox (preferred but problematic with
Teams meetings) and Brave (great in general but recently getting some
delayed responses, but works with Teams meetings). Maintaining the
same bookmarks is problematic.

I now use my own *bookmarks.json* as the definitive file obtained by
extracting as JSON bookmarks from Firefox and Brave, unifying them,
de-duplicating and then moving that into *bookmarks.json*. I now
maintain *bookmarks.json* manually.

## unify_bookmarks.py

Read and save as JSON firefox and brave bookmarks, then unify them
into **bookmarks_unified.json** while also saving
**bookmarks_brave.json** and **bookmarks_firefox.json**

## dedupe_bookmarks.py

Remove duplicates from *bookmarks_unified.json* saving to
**bookmarks_unified_deduped.py**

## manage bookmarks

Copy *bookmarks_unified_deduped.py* to **bookmarks.py** and cleanup
manually and retain this as the master bookmarks file.

## clear_firefox.py

Removes all bookmarks from Firefox.

## update_bookmarks.py

Replaces current bookmarks in Brave and Firefox with those from
*bookmarks.json*
