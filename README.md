# ⚡ Smart File Organizer Pro

A modern, dark-mode desktop application built in Python that automatically keeps your directories spotless. It runs quietly in the background using multi-threading and sorts incoming downloads, images, and archives seamlessly based on file extensions.

## ✨ Features
- **Real-Time Monitoring:** Uses the `watchdog` library to listen for system filesystem triggers instantly.
- **Modern Dark Interface:** Sleek UX built with `CustomTkinter`.
- **Thread-Isolated Engine:** The background sorting worker runs on a separate thread, keeping the GUI incredibly smooth and responsive.
- **Smart Duplicate Prevention:** Appends custom unique counters to file name patterns so older files never get accidentally overwritten.
- **Defensive Edge Case Checks:** Automatically waits for heavy downloads to complete and gracefully handles right-click empty file creation scenarios.

## 🛠️ Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/smart-file-organizer.git](https://github.com/MH7Q/smart-file-organizer.git)
   cd smart-file-organizer