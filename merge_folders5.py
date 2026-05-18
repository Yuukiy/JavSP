import os
import shutil
import argparse
import time
from tkinter import Tk
from tkinter.filedialog import askdirectory


def read_merge_conf(filename):
    synonyms = {}
    added_words = set()

    for enc in ('utf-8', 'gb18030'):
        try:
            with open(filename, 'r', encoding=enc) as file:
                file.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        enc = 'utf-8'

    with open(filename, 'r', encoding=enc) as file:
        for line_number, line in enumerate(file, start=1):
            words = line.strip().split('\t')
            if len(words) > 1:
                primary_word = words[0]
                for word in words:
                    if word in added_words:
                        raise ValueError(f"Duplicate word found: {word} on line {line_number}")
                    if word not in synonyms:
                        synonyms[word] = primary_word
                        added_words.add(word)
            elif len(words) == 1 and words[0]:
                print(f"Warning: Line '{line.strip()}' has no synonyms.")

    return synonyms


def fast_get_dir_size(path):
    try:
        total = 0
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False):
                for root, dirs, files in os.walk(entry.path):
                    for f in files:
                        try:
                            total += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass
        return total
    except OSError:
        return 0


def rename_and_merge(directory, synonyms):
    renamed = 0
    merged = 0

    entries = os.listdir(directory)
    dir_names = [e for e in entries if os.path.isdir(os.path.join(directory, e))]

    rename_plan = []
    for d in dir_names:
        if d in synonyms:
            target_name = synonyms[d]
            if target_name != d:
                rename_plan.append((d, target_name))

    for old_name, new_name in rename_plan:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)

        if not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"Renamed: '{old_name}' -> '{new_name}'")
            renamed += 1
        else:
            print(f"Merging: '{old_name}' -> '{new_name}'")
            for item in os.listdir(old_path):
                s = os.path.join(old_path, item)
                d = os.path.join(new_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    if os.path.exists(d):
                        s_size = os.path.getsize(s)
                        d_size = os.path.getsize(d)
                        if s_size > d_size:
                            shutil.move(s, d)
                    else:
                        shutil.move(s, d)
            shutil.rmtree(old_path)
            merged += 1

    print(f"\nRename: {renamed}, Merge: {merged}")
    return renamed + merged


def remove_small_folders(directory, limit_mb):
    limit_bytes = limit_mb * 1024 * 1024
    deleted = 0
    freed = 0

    all_dirs = []
    for root, dirs, _ in os.walk(directory, topdown=False):
        for d in dirs:
            all_dirs.append(os.path.join(root, d))

    for folder in all_dirs:
        if not os.path.exists(folder):
            continue
        size = fast_get_dir_size(folder)
        if size < limit_bytes:
            size_mb = size / (1024 * 1024)
            shutil.rmtree(folder)
            print(f"Deleted ({size_mb:.1f}MB): {folder}")
            freed += size
            deleted += 1

    print(f"\nDeleted {deleted} small folders, freed {freed / (1024*1024):.1f}MB")
    return deleted


def select_directory():
    root = Tk()
    root.withdraw()
    directory = askdirectory(title="Select Directory")
    if directory:
        return directory
    else:
        print("No directory selected.")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename/merge actress folders and remove small folders.")
    parser.add_argument('-i', '--input', help="Directory to process.")
    parser.add_argument('-s', '--size', type=int, default=200, help="Remove folders smaller than this size in MB (default: 200).")
    args = parser.parse_args()

    directory_to_process = args.input or select_directory()
    conf_file = "merge.conf"
    start = time.time()

    print(f"Processing: {directory_to_process}")
    print("=" * 60)

    try:
        synonyms = read_merge_conf(conf_file)
        rename_and_merge(directory_to_process, synonyms)
    except Exception as e:
        print(f"An error occurred during rename/merge: {e}")

    print("=" * 60)
    print("Removing small folders...")

    try:
        remove_small_folders(directory_to_process, args.size)
    except Exception as e:
        print(f"An error occurred while removing small folders: {e}")

    elapsed = time.time() - start
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
