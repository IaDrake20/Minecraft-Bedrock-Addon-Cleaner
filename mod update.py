#Original program by Ian Drake.
#Feel free to change this to whatever you need!
#-------------------------------------------------

import os
import shutil
import tkinter as tk
from datetime import datetime, timezone
from typing import List, Dict, Any
from pathlib import Path
import threading
import tkinter.filedialog as filedialog

NEW_PACKS_DIR = None
OLD_PACKS_DIR = None
BACKUP_ARCHIVE_DIR = None

PackItem = Dict[str, Any]

def get_folder_data(directory: Path) -> List[PackItem]:
    """
    Collects metadata from a directory and returns the list.
    Uses UTC standardized formatting for all timestamps.
    """
    print(f"\n--- Scanning directory: {directory} ---")
    packs_array = []

    if not directory.is_dir():
        return packs_array

    try:
        for item_path in directory.iterdir():
            item_name = item_path.name
            
            if item_path.is_dir():
                try:
                    stat_result = item_path.stat()
                    mod_timestamp = stat_result.st_mtime
                    
                    mod_date_dt = datetime.fromtimestamp(mod_timestamp, tz=timezone.utc)
                    mod_date_formatted = mod_date_dt.strftime('%Y-%m-%d %H:%M:%S UTC')

                    packs_array.append({
                        'name': item_name,
                        'path': item_path,  
                        'date': mod_date_formatted,
                        'is_processed': False
                    })
                except PermissionError:
                    print(f"Warning: Permission denied accessing directory {item_name}. Skipping.")
                except Exception as e:
                    print(f"Error processing {item_name}: {e}")
    except Exception as e:
        print(f"Failed to scan directory {directory}: {e}")

    return packs_array


def find_minecraft_resource_packs() -> Path:
    """Search for Minecraft resource packs directory in AppData."""
    #look for the standard path
    search_path = Path("C:/Users")
    
    if not search_path.exists():
        return None
        
    try:
        for user_dir in search_path.iterdir():
            if user_dir.is_dir():
                potential_path = user_dir / "AppData" / "Roaming" / "Minecraft Bedrock" / "Users" / "Shared" / "games" / "com.mojang" / "resource_packs"
                if potential_path.exists() and potential_path.is_dir():
                    return potential_path
    except Exception:
        pass
        
    #Possible alt paths
    possible_paths = [
        Path("C:/Users") / os.environ.get('USERNAME', 'default') / "AppData" / "Roaming" / "Minecraft Bedrock" / "Users" / "Shared" / "games" / "com.mojang" / "resource_packs",
        Path("C:/Program Files/Minecraft/Bedrock Edition") / "resource_packs"
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            return path
            
    return None


def find_or_create_backup_directory() -> Path:
    """Find existing PACKS_BACKUP folder or create it."""
    #look for the standard path
    search_path = Path("C:/Users")
    
    if not search_path.exists():
        return None
        
    try:
        for user_dir in search_path.iterdir():
            if user_dir.is_dir():
                base_minecraft_path = user_dir / "AppData" / "Roaming" / "Minecraft Bedrock" / "Users" / "Shared" / "games" / "com.mojang"
                
                # Check if PACKS_BACKUP exists
                backup_path = base_minecraft_path / "PACKS_BACKUP"
                if backup_path.exists() and backup_path.is_dir():
                    return backup_path
                    
                potential_backup_path = base_minecraft_path / "PACKS_BACKUP"
                potential_backup_path.mkdir(parents=True, exist_ok=True)
                return potential_backup_path
                
    except Exception:
        pass
        
    try:
        username = os.environ.get('USERNAME', 'default')
        fallback_path = Path(f"C:/Users/{username}/AppData/Roaming/Minecraft Bedrock/Users/Shared/games/com.mojang/PACKS_BACKUP")
        fallback_path.mkdir(parents=True, exist_ok=True)
        return fallback_path
    except Exception:
        pass
        
    #default backup location
    try:
        default_path = Path("C:/Users") / os.environ.get('USERNAME', 'default') / "PACKS_BACKUP"
        default_path.mkdir(parents=True, exist_ok=True)
        return default_path
    except Exception:
        pass
        
    return None


def compare_and_clean_packs(new_packs: List[PackItem], old_packs: List[PackItem]) -> str:
    """
    Compares lists, backs up, and deletes. Returns a summary string for logging.
    This function modifies the file system directly.
    """
    summary = ["\n=============================================",
               "Starting Pack Comparison & Cleanup Process",
               "============================================="]

    old_pack_map = {item['name']: item for item in old_packs}

    newly_updated_count = 0
    deleted_count = 0

    #standardized timestamp generation
    backup_timestamp_suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    for new_item in new_packs:
        pack_name = new_item['name']
        summary.append(f"\n[Checking New Pack]: {pack_name}...")

        if pack_name in old_pack_map:
            old_item = old_pack_map[pack_name]
            summary.append(f"   Match found! Old version detected: {old_item['date']}")
            
            try:
                backup_source = old_item['path']
                backup_destination = BACKUP_ARCHIVE_DIR / f"{pack_name}_{backup_timestamp_suffix}"

                if not backup_destination.parent.exists():
                    backup_destination.parent.mkdir(parents=True, exist_ok=True)

                summary.append("   Backing up '...' to unique archive path...")
                shutil.copytree(backup_source, backup_destination)
                summary.append("   Backup complete.")

                #delete the old folder ONLY after successful copy
                summary.append(f"   Deleting old version of '{pack_name}' from {OLD_PACKS_DIR}...")
                shutil.rmtree(old_item['path'])
                deleted_count += 1

                new_item['is_processed'] = True
                newly_updated_count += 1
                summary.append("   Cleanup complete and update registered successfully.")

            except FileNotFoundError as e:
                #old_item['path'] is probably incorrect or missing
                summary.append(f"!!! WARNING: Filesystem error for {pack_name}. Source file not found at expected location ({old_item['path']}). Skipping cleanup. Error: {e}")
            except Exception as e:
                #catch all other I/O errors 
                summary.append(f"!!! CRITICAL ERROR processing {pack_name}: Failed to perform cleanup or backup. Reason: {type(e).__name__} - {e}")
                new_item['is_processed'] = False

        else:
            #no match, treat as new
            new_item['is_processed'] = False
            summary.append("   No matching old version found. Treating as a brand new pack.")

    summary.append("\n=============================================")
    if newly_updated_count > 0:
        summary.append(f"Process Summary: Successfully updated/cleaned up {newly_updated_count} packs.")
    else:
        summary.append("Process Summary: No existing old versions were found to update or clean up.")
    summary.append(f"Total folders deleted from '{OLD_PACKS_DIR}': {deleted_count}")

    return "\n".join(summary)

class PackManagerGUI:
    """Main GUI Class."""
    def __init__(self, master):
        self.master = master
        master.title("Pack Management System")

        #gui logging area
        self.log_frame = tk.LabelFrame(master, text="System Log", padx=10, pady=10)
        self.log_frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, width=80, height=20, font=('Courier', 10))
        self.log_scrollbar = tk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill="both", expand=True)
        self.log_scrollbar.pack(side=tk.RIGHT, fill="y")

        button_frame = tk.Frame(master)
        button_frame.pack(padx=10, pady=10, fill="x")

        tk.Button(button_frame, text="Run Comparison & Cleanup", command=self.start_cleanup_thread, height=2).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Exit", command=master.quit, height=2).pack(side=tk.RIGHT, padx=10)

    def log_message(self, message):
        """Appends a timestamped message to the console log."""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.insert(tk.END, f"{timestamp} {message}\n")
        #auto scroll down
        self.log_text.see(tk.END)

    def start_cleanup_thread(self):
        """Initiates the file operation in a separate thread."""
        self.log_message("--- Initiating Scan ---")
        #disable button to prevent re-entry while running
        for widget in self.master.winfo_children():
            if isinstance(widget, tk.Frame):
                for btn in widget.winfo_children():
                    btn.config(state=tk.DISABLED)

        self.log_message("Scanning directories... This may take time.")
        
        # Start the heavy lifting in a non-blocking thread
        threading.Thread(target=self._run_workflow).start()

    def _run_workflow(self):
        """The actual blocking logic executed in the separate thread."""
        try:
            new_packs_array = get_folder_data(NEW_PACKS_DIR)
            old_packs_array = get_folder_data(OLD_PACKS_DIR)

            self.log_message("\n" + "="*20 + " STATUS OF NEW PACKS " + "="*20)
            for pack in new_packs_array:
                status = "Processed" if pack['is_processed'] else "Pending"
                self.log_message(f" - {pack['name']:<15} | Date: {pack['date']} | Status: {status}")

            self.log_message("\n" + "="*20 + " STATUS OF OLD PACKS " + "="*20)
            for pack in old_packs_array:
                self.log_message(f" - {pack['name']:<15} | Date: {pack['date']}")

            summary = compare_and_clean_packs(new_packs_array, old_packs_array)
            self.log_message(summary)

        except Exception as e:
            final_error_msg = f"FATAL WORKFLOW ERROR: An unrecoverable error occurred during execution.\nDetails: {e}"
            self.log_message(final_error_msg)
        finally:
            for widget in self.master.winfo_children():
                if isinstance(widget, tk.Frame):
                    for btn in widget.winfo_children():
                        btn.config(state=tk.NORMAL)

def main():
    global NEW_PACKS_DIR, OLD_PACKS_DIR, BACKUP_ARCHIVE_DIR
    
    root = tk.Tk()
    root.withdraw()
    
    #user picks new packs dir
    new_packs_dir = filedialog.askdirectory(
        title="Select Minecraft Mods Directory",
        initialdir="C:/Users"
    )
    
    if not new_packs_dir:
        print("No directory selected. Exiting.")
        return
        
    NEW_PACKS_DIR = Path(new_packs_dir)
    
    OLD_PACKS_DIR = find_minecraft_resource_packs()
    
    if not OLD_PACKS_DIR or not OLD_PACKS_DIR.exists():
        print("Could not locate Minecraft resource packs directory. Exiting.")
        return
    
    #find or create backup directory
    BACKUP_ARCHIVE_DIR = find_or_create_backup_directory()
    
    if not BACKUP_ARCHIVE_DIR:
        print("Could not find or create backup directory. Exiting.")
        return
    
    root.deiconify()
    app = PackManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
