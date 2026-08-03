import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# --- Configuration ---
NEW_PACKS_DIR = input("Enter the directory to the download folder please: ")
OLD_PACKS_DIR = input("Enter the directory to the addons folder please: ")
BACKUP_ARCHIVE_DIR = input("Enter the directory to the backuparchive please: ")


# Type alias for clarity
PackItem = Dict[str, Any]

def get_folder_data(directory: str) -> List[PackItem]:
    """
    Build + fill arrays to hold the data for the directories
    """
    print(f"\n--- Scanning directory: {directory} ---")
    packs_array = []
    if not os.path.isdir(directory):
        print(f"Warning: Directory '{directory}' does not exist.")
        return packs_array

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        
        if os.path.isdir(item_path):
            try:
                mod_time_sec = os.path.getmtime(item_path)
                mod_date = datetime.fromtimestamp(mod_time_sec, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

                packs_array.append({
                    'name': item,
                    'path': item_path,
                    'date': mod_date,
                    'is_processed': False
                })
            except Exception as e:
                print(f"Error processing {item}: {e}")

    return packs_array


def compare_and_clean_packs(new_packs: List[PackItem], old_packs: List[PackItem]) -> None:
    """
    Part 2 Logic: Compares new and old lists, backs up, deletes, and updates status.
    """
    print("Starting Pack Comparison & Cleanup Process")

    old_pack_map = {item['name']: item for item in old_packs}

    newly_updated_count = 0
    deleted_count = 0

    for new_item in new_packs:
        pack_name = new_item['name']
        print(f"\n[Checking New Pack]: {pack_name}...")

        if pack_name in old_pack_map:
            old_item = old_pack_map[pack_name]

            print(f"   Match found! Old version detected: {old_item['date']}")
            
            #backup and delete old
            try:
                backup_source = old_item['path']
                
                timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_destination = os.path.join(BACKUP_ARCHIVE_DIR, f"{pack_name}_{timestamp_suffix}")

                print(f"   Backing up '{pack_name}' from {OLD_PACKS_DIR} to unique archive path...")
                
                shutil.copytree(backup_source, backup_destination)
                print("   Backup complete.")

                print(f"   Deleting old version of '{pack_name}' from {OLD_PACKS_DIR}...")
                shutil.rmtree(old_item['path'])
                deleted_count += 1

                new_item['is_processed'] = True
                newly_updated_count += 1
                print("   Cleanup complete and update registered successfully.")


            except FileNotFoundError as e:
                print(f"!!! WARNING: Filesystem error encountered for {pack_name}. Source file not found. Skipping backup/delete. Error: {e}")
            except Exception as e:
                print(f"!!! CRITICAL ERROR processing {pack_name}: Failed to perform cleanup or backup. Reason: {e}")
                new_item['is_processed'] = False


        else:
            new_item['is_processed'] = False
            print("   No matching old version found. Treating as a brand new pack.")


    print("Process Summary:")
    if newly_updated_count > 0:
        print(f"Successfully updated/cleaned up {newly_updated_count} packs.")
    else:
        print("No existing old versions were found to update or clean up.")
    print(f"Total folders deleted from '{OLD_PACKS_DIR}': {deleted_count}")


def main():
    """Main function to run the entire workflow. Added top-level safety net."""
    try:
        new_packs_array = get_folder_data(NEW_PACKS_DIR)
        old_packs_array = get_folder_data(OLD_PACKS_DIR)

    except Exception as e:
        print("\n[FATAL ERROR] Failed during initial data collection. Check directory paths and permissions.")
        print(f"Details: {e}")
        return 

    print("STATUS OF NEW PACKS")
    for pack in new_packs_array:
        status = "Processed" if pack.get('is_processed', False) else "Pending" 
        print(f" - {pack['name']:<15} | Date: {pack['date']} | Status: {status}")

    print("STATUS OF OLD PACKS")
    for pack in old_packs_array:
        print(f" - {pack['name']:<15} | Date: {pack['date']}")


    if new_packs_array and old_packs_array:
        compare_and_clean_packs(new_packs_array, old_packs_array)

    print("\n\n*** Workflow completed successfully. ***")


if __name__ == "__main__":
    main()
