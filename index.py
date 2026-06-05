from pathlib import Path
import shutil
import time
import logging
import threading
import customtkinter as ctk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =====================================================
# CONFIGURATION
# =====================================================

HOME = Path.home()

# Default tracked folder (User can change this live in the GUI)
TRACKED_FOLDER = HOME / "Downloads"

DEST_DIR_IMAGES = HOME / "Pictures" / "Organized_Images"
DEST_DIR_DOCS = HOME / "Documents" / "Organized_Docs"
DEST_DIR_AUDIO = HOME / "Music" / "Organized_Audio"
DEST_DIR_ARCHIVES = HOME / "Documents" / "Organized_Archives"
# Safely isolated outside of Downloads to prevent infinite execution loops
DEST_DIR_OTHER = HOME / "Documents" / "Organized_Other"

EXTENSION_MAP = {
    # Images
    ".jpg": DEST_DIR_IMAGES, ".jpeg": DEST_DIR_IMAGES, ".png": DEST_DIR_IMAGES,
    ".gif": DEST_DIR_IMAGES, ".bmp": DEST_DIR_IMAGES, ".webp": DEST_DIR_IMAGES,

    # Documents
    ".pdf": DEST_DIR_DOCS, ".docx": DEST_DIR_DOCS, ".txt": DEST_DIR_DOCS,
    ".xlsx": DEST_DIR_DOCS, ".pptx": DEST_DIR_DOCS, ".csv": DEST_DIR_DOCS,

    # Audio
    ".mp3": DEST_DIR_AUDIO, ".wav": DEST_DIR_AUDIO, ".flac": DEST_DIR_AUDIO, ".aac": DEST_DIR_AUDIO,

    # Archives
    ".zip": DEST_DIR_ARCHIVES, ".rar": DEST_DIR_ARCHIVES, ".7z": DEST_DIR_ARCHIVES,
    ".tar": DEST_DIR_ARCHIVES, ".gz": DEST_DIR_ARCHIVES,
}

# Active temporary extensions to skip until download finishes
IGNORED_EXTENSIONS = {".crdownload", ".tmp", ".part", ".download"}

# =====================================================
# LOGGING SETUP
# =====================================================

logging.basicConfig(
    filename="file_organizer.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =====================================================
# CORE ENGINE LOGIC
# =====================================================

class OrganizerEngine:
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.observer = None
        self.tracked_path = TRACKED_FOLDER

    def log(self, message):
        """Streams system events live to both the app GUI window and text log file"""
        self.log_callback(message)
        logging.info(message)

    def wait_for_file_complete(self, file_path, timeout=60):
        """Ensures files have completely finished copying or writing before moving"""
        previous_size = -1
        while timeout > 0:
            try:
                if not file_path.exists():
                    return False
                current_size = file_path.stat().st_size
                
                if current_size == previous_size and current_size > 0:
                    return True
                previous_size = current_size
            except FileNotFoundError:
                pass
            time.sleep(1)
            timeout -= 1
        return False

    def get_destination(self, file_path):
        extension = file_path.suffix.lower()
        return EXTENSION_MAP.get(extension, DEST_DIR_OTHER)

    def generate_unique_path(self, destination):
        if not destination.exists():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def move_file(self, file_path):
        if not file_path.exists() or not file_path.is_file():
            return
        if file_path.suffix.lower() in IGNORED_EXTENSIONS:
            return

        # Double check to prevent processing files that are currently inside our destinations
        if DEST_DIR_OTHER in file_path.parents:
            return

        try:
            # FIX: If file is 0 bytes, skip it immediately to avoid freezing the startup scan.
            # It will get picked up later by the on_modified listener when written to.
            if file_path.stat().st_size == 0:
                return
        except FileNotFoundError:
            return

        destination_folder = self.get_destination(file_path)
        destination_folder.mkdir(parents=True, exist_ok=True)
        destination_file = self.generate_unique_path(destination_folder / file_path.name)

        if not self.wait_for_file_complete(file_path):
            return

        try:
            shutil.move(str(file_path), str(destination_file))
            self.log(f"Moved: {file_path.name} ➔ {destination_folder.name}")
        except Exception as e:
            logging.error(f"Failed to move {file_path.name}: {e}")

    def organize_existing_files(self):
        self.log("🧹 Scanning for existing completed files...")
        for item in self.tracked_path.iterdir():
            if item.is_file():
                self.move_file(item)
        self.log("✨ Startup cleanup sequence complete.")

    def start_monitoring(self, path_to_watch):
        self.tracked_path = Path(path_to_watch)
        self.organize_existing_files()

        class FileMoverHandler(FileSystemEventHandler):
            def __init__(self, engine):
                self.engine = engine
                
            def on_created(self, event):
                if event.is_directory:
                    return
                self.engine.move_file(Path(event.src_path))

            def on_modified(self, event):
                if event.is_directory:
                    return
                # Catches right-click empty files once they are written to/saved
                self.engine.move_file(Path(event.src_path))

        event_handler = FileMoverHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.tracked_path), recursive=False)
        self.observer.start()
        self.log("👀 Background listener actively running...")

    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.log("🛑 Background engine successfully halted.")

# =====================================================
# GUI
# =====================================================

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue") 

class OrganizerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart File Organizer Pro")
        self.geometry("640x480")
        self.resizable(False, False)

        self.selected_folder = ctk.StringVar(value=str(TRACKED_FOLDER))
        self.is_running = False
        
        # Link UI instance handler to the automation core engine
        self.engine = OrganizerEngine(log_callback=self.log_message)

        # --- DRAWING LAYOUT UI ---
        self.title_label = ctk.CTkLabel(self, text="⚡ Smart File Organizer", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(padx=20, pady=(25, 5))

        self.desc_label = ctk.CTkLabel(self, text="Automated background engine to keep clean directories.", font=ctk.CTkFont(size=13))
        self.desc_label.pack(padx=20, pady=(0, 25))

        # Folder Selector Component
        self.folder_frame = ctk.CTkFrame(self)
        self.folder_frame.pack(padx=20, pady=5, fill="x")

        self.folder_entry = ctk.CTkEntry(self.folder_frame, textvariable=self.selected_folder, width=410)
        self.folder_entry.pack(side="left", padx=(10, 10), pady=12)

        self.browse_btn = ctk.CTkButton(self.folder_frame, text="Browse", width=100, command=self.browse_folder)
        self.browse_btn.pack(side="right", padx=(0, 10), pady=12)

        # Action Core Switch Engine Controller
        self.action_btn = ctk.CTkButton(self, text="Start Monitoring", fg_color="green", hover_color="#005c11", 
                                         font=ctk.CTkFont(size=16, weight="bold"), height=44, command=self.toggle_monitoring)
        self.action_btn.pack(padx=20, pady=15, fill="x")

        # System Console Output Log View
        self.log_label = ctk.CTkLabel(self, text="Live Engine Activity Log:", font=ctk.CTkFont(size=12, weight="bold"))
        self.log_label.pack(anchor="w", padx=25, pady=(10, 0))

        self.log_textbox = ctk.CTkTextbox(self, height=160, font=ctk.CTkFont(family="Consolas", size=11), state="disabled")
        self.log_textbox.pack(padx=20, pady=(5, 20), fill="both", expand=True)

        self.log_message("System Idle. Select target drive directory path and start the monitor engine.")

    # --- UI BACKEND CONTROLS ---

    def browse_folder(self):
        chosen_dir = filedialog.askdirectory(initialdir=self.selected_folder.get())
        if chosen_dir:
            self.selected_folder.set(chosen_dir)
            self.log_message(f"Tracked directory path updated to: {chosen_dir}")

    def toggle_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.action_btn.configure(text="Stop Monitoring", fg_color="#b80000", hover_color="#7a0000")
            self.folder_entry.configure(state="disabled")
            self.browse_btn.configure(state="disabled")
            
            # Offload file system handling loop onto a separate background thread
            target_folder = self.selected_folder.get()
            self.monitor_thread = threading.Thread(target=self.engine.start_monitoring, args=(target_folder,), daemon=True)
            self.monitor_thread.start()
        else:
            self.is_running = False
            self.action_btn.configure(text="Start Monitoring", fg_color="green", hover_color="#005c11")
            self.folder_entry.configure(state="normal")
            self.browse_btn.configure(state="normal")
            
            # Clean exit for watchdog pipeline observers
            self.engine.stop_monitoring()

    def log_message(self, message):
        """Thread-safe injector mechanism to feed events onto window viewport"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_textbox.see("end")  # Follow scrolling frame drop anchor automatically
        self.log_textbox.configure(state="disabled")

# =====================================================
# INITIALIZER SYSTEM RUNNER
# =====================================================

if __name__ == "__main__":
    app = OrganizerGUI()
    
    # Intercept system close handler window button to destroy active running sub-threads cleanly
    def on_closing():
        if app.is_running:
            app.engine.stop_monitoring()
        app.destroy()
        
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()