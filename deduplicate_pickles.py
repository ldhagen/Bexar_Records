#!/usr/bin/env python3
"""
Deduplicate Pickle Files
------------------------
This script scans the current directory for duplicate .pkl files by comparing 
their SHA256 hashes. It provides a terminal-based UI (whiptail) to allow 
users to select and remove redundant files.

Deduplication Strategy:
1. Group files by size (quick filter).
2. Hash files with identical sizes to confirm they are bit-for-bit matches.
3. Present a checklist suggesting the removal of older duplicates (based on name).
"""

import os
import hashlib
import subprocess
import shlex
import sys
from collections import defaultdict

def get_file_hash(filepath, block_size=65536):
    """
    Calculates the SHA256 hash of a file to uniquely identify its content.
    Reads in blocks to remain memory efficient for large pickle files.
    """
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()
    except OSError as e:
        print(f"Error reading {filepath}: {e}")
        return None

def find_duplicates(directory):
    """
    Scans for .pkl files and identifies duplicates.
    Uses a two-pass approach (size then hash) to optimize performance.
    """
    print("Scanning for .pkl files...")
    files = [f for f in os.listdir(directory) if f.endswith('.pkl')]
    files.sort()
    
    # First pass: Group by size to identify potential duplicates quickly
    size_map = defaultdict(list)
    for f in files:
        path = os.path.join(directory, f)
        if os.path.isfile(path):
            size_map[os.path.getsize(path)].append(f)
    
    duplicates = {}
    total_files = len(files)
    processed = 0
    
    print(f"Hashing {total_files} files...")
    
    for size, file_list in size_map.items():
        # Only hash files if there's more than one with the same size
        if len(file_list) < 2:
            processed += len(file_list)
            continue
            
        # Second pass: Generate SHA256 hashes for files sharing the same size
        hash_map = defaultdict(list)
        for f in file_list:
            path = os.path.join(directory, f)
            h = get_file_hash(path)
            if h:
                hash_map[h].append(f)
            processed += 1
            if processed % 10 == 0:
                print(f"Progress: {processed}/{total_files}", end='\r')
                
        for h, f_list in hash_map.items():
            if len(f_list) > 1:
                duplicates[h] = f_list

    print(f"\nFound {len(duplicates)} groups of duplicate files.")
    return duplicates

def show_whiptail_checklist(duplicates):
    """
    Displays a terminal-based checklist using 'whiptail'.
    Suggests keeping the newest file (alphabetically last) in each duplicate group.
    """
    
    checklist_args = []
    
    for group_idx, (h, files) in enumerate(duplicates.items()):
        # Sort files to determine the 'newest' based on standard naming conventions
        files.sort() 
        
        # We suggest keeping the last one (usually newest date) and removing the others
        to_keep = files[-1]
        
        for f in files:
            # Files selected "ON" will be deleted
            status = "ON" if f != to_keep else "OFF"
            
            # Labeling the items in the TUI
            desc = f"Group {group_idx+1} (Duplicate)"
            if f == to_keep:
                desc += " [KEEPING NEWEST]"
            
            checklist_args.extend([f, desc, status])

    if not checklist_args:
        print("No duplicates to handle.")
        return []

    # Configure the whiptail command
    cmd = [
        "whiptail",
        "--title", "Duplicate Pickle File Remover",
        "--checklist", "Select files to PERMANENTLY DELETE.\n(Space to toggle, Enter to confirm)",
        "25", "110", "15", # UI Dimensions: Height, Width, ListHeight
    ] + checklist_args

    try:
        # Run whiptail and capture selected files from stderr
        result = subprocess.run(cmd, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            print("Selection cancelled by user.")
            return []
            
        # whiptail returns selected tags in stderr as a string of quoted values
        output = result.stderr.decode('utf-8')
        return shlex.split(output)
        
    except FileNotFoundError:
        print("Error: 'whiptail' is not installed. Please install it to use this TUI.")
        return []

def main():
    """
    Main execution flow: Find duplicates, prompt for removal, and execute deletion.
    """
    directory = "."
    duplicates = find_duplicates(directory)
    
    if not duplicates:
        print("No duplicate .pkl files found.")
        return

    # Trigger the TUI for user selection
    to_remove = show_whiptail_checklist(duplicates)
    
    if not to_remove:
        print("No files selected for removal.")
        return
        
    # Safety confirmation before permanent deletion
    print(f"\nCRITICAL: You are about to permanently delete {len(to_remove)} files.")
    confirm = input("Type 'yes' to confirm deletion: ")
    
    if confirm.lower() == 'yes':
        count = 0
        for f in to_remove:
            try:
                os.remove(os.path.join(directory, f))
                print(f"Deleted: {f}")
                count += 1
            except OSError as e:
                print(f"Error deleting {f}: {e}")
        print(f"\nSuccess: Removed {count} files.")
    else:
        print("Deletion aborted.")

if __name__ == "__main__":
    main()

