import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Label
import os
import json
import shutil
from tkinter.ttk import Progressbar
import threading
from pydub import AudioSegment

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = y = 0
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = Label(self.tooltip, text=self.text, background="white", relief="solid", borderwidth=1, padx=5, pady=3)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
        self.tooltip = None

# Initialize Tkinter root window
root = tk.Tk()
root.title("Minecraft OGG Extractor")

# Set application icon
icon = tk.PhotoImage(file="icon.png")
root.iconphoto(False, icon)

# Function to browse .minecraft folder
def browse_minecraft_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        minecraft_folder_entry.delete(0, tk.END)
        minecraft_folder_entry.insert(0, folder_path)


# Function to browse output folder
def browse_output_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_folder_entry.delete(0, tk.END)
        output_folder_entry.insert(0, folder_path)


# Function to locate latest #.json file in .minecraft/assets/indexes
def find_latest_json(minecraft_folder):
    indexes_folder = os.path.join(minecraft_folder, "assets", "indexes")
    json_files = [f for f in os.listdir(indexes_folder) if f.endswith(".json")]

    if not json_files:
        return None

    # Get the highest numbered .json file
    latest_json = max(json_files, key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else -1)
    return os.path.join(indexes_folder, latest_json)


# Function to parse JSON file and extract .ogg entries
def parse_json(json_file):
    ogg_entries = {}
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            objects = data.get('objects', {})
            for key, info in objects.items():
                if key.endswith('.ogg'):
                    filename = key.split('/')[-1]
                    hash_value = info['hash']
                    ogg_entries[hash_value] = filename
    except Exception as e:
        print(f"Error parsing JSON file: {str(e)}")
    return ogg_entries


# Function to update console output with automatic scrolling
def update_console(msg):
    console_text.config(state=tk.NORMAL)
    console_text.insert(tk.END, msg + "\n")
    console_text.see(tk.END)
    console_text.config(state=tk.DISABLED)  # Disable editing of console text


def extract_ogg_files():
    minecraft_folder = minecraft_folder_entry.get()
    output_folder = output_folder_entry.get()

    if not minecraft_folder or not output_folder:
        messagebox.showwarning("Missing Information", "Please specify .minecraft folder and output directory.")
        return

    # Ensure that the output folder has an 'ogg' subdirectory
    output_ogg_folder = os.path.join(output_folder, 'ogg')
    os.makedirs(output_ogg_folder, exist_ok=True)

    # Find latest #.json file
    json_file = find_latest_json(minecraft_folder)
    if not json_file:
        messagebox.showerror("Error", "No JSON file found in .minecraft/assets/indexes.")
        return

    # Parse JSON to extract .ogg entries
    ogg_entries = parse_json(json_file)
    if not ogg_entries:
        messagebox.showwarning("No .ogg Entries", "No .ogg entries found in the JSON file.")
        return

    # Define the objects folder path
    objects_folder = os.path.join(minecraft_folder, "assets", "objects")

    # Start the extraction process in a separate thread
    threading.Thread(target=copy_ogg_files,
                     args=(ogg_entries, objects_folder, output_folder, output_ogg_folder)).start()


def copy_ogg_files(ogg_entries, objects_folder, output_folder, output_ogg_folder):
    total_files = len(ogg_entries)
    files_copied = 0

    # Always copy ogg files to the temporary ogg folder
    for root_dir, _, files in os.walk(objects_folder):
        for file in files:
            hash_value = os.path.splitext(file)[0]
            if hash_value in ogg_entries:
                ogg_filename = ogg_entries[hash_value]
                src_file = os.path.join(root_dir, file)
                dst_file = os.path.join(output_ogg_folder, ogg_filename)
                shutil.copy(src_file, dst_file)
                update_console(f"Copied: {src_file} -> {dst_file}")
                files_copied += 1
                progress_value = int((files_copied / total_files) * 100)
                progress_bar['value'] = progress_value
                root.update()  # Update the GUI to reflect progress

    # Check if user wants to convert and organize additional formats
    convert_mp3 = mp3_var.get()
    convert_flac = flac_var.get()
    convert_wav = wav_var.get()

    # Convert ogg files if requested
    if convert_mp3 or convert_flac or convert_wav:
        formats_to_convert = []
        if convert_mp3:
            formats_to_convert.append("mp3")
        if convert_flac:
            formats_to_convert.append("flac")
        if convert_wav:
            formats_to_convert.append("wav")

        # Create directories for each format
        for format_name in formats_to_convert:
            format_folder = os.path.join(output_folder, format_name)
            os.makedirs(format_folder, exist_ok=True)

        progress_value = 0
        for format_name in formats_to_convert:
            progress_value = 0
            # Convert ogg files
            for file in os.listdir(output_ogg_folder):
                if file.endswith(".ogg"):
                    ogg_filepath = os.path.join(output_ogg_folder, file)
                    audio = AudioSegment.from_file(ogg_filepath, format="ogg")

                    format_folder = os.path.join(output_folder, format_name)
                    converted_file = os.path.splitext(file)[0] + "." + format_name
                    dst_file = os.path.join(format_folder, converted_file)

                    # Perform conversion
                    if format_name == "mp3":
                        audio.export(dst_file, format="mp3", bitrate="192k")
                    elif format_name == "flac":
                        audio.export(dst_file, format="flac")
                    elif format_name == "wav":
                        audio.export(dst_file, format="wav")

                    update_console(f"Converted: {ogg_filepath} -> {dst_file}")

                    # Update progress bar during conversion
                    progress_value += (1 / total_files) * 100
                    progress_bar["value"] = progress_value
                    root.update()

    # Optionally delete the original ogg files and its folder after conversion
    if not keep_ogg_var.get():
        for file in os.listdir(output_ogg_folder):
            file_path = os.path.join(output_ogg_folder, file)
            os.remove(file_path)  # Delete the original .ogg files

        # Remove the 'ogg' folder after conversion if it's empty
        try:
            os.rmdir(output_ogg_folder)
            update_console(f"Deleted: {output_ogg_folder}")
        except OSError:
            pass  # Directory not empty or does not exist

    messagebox.showinfo("Extraction Complete", "Files extracted and converted successfully!")


# Function to set minimum size based on content
def set_minimum_size(event=None):
    root.update_idletasks()
    min_width = root.winfo_reqwidth()
    min_height = root.winfo_reqheight()
    root.minsize(min_width, min_height)


# Call set_minimum_size when the window is resized
root.bind('<Configure>', set_minimum_size)

# Title and Subtitle Labels
title_label = tk.Label(root, text="Minecraft Ogg Extractor", font=('Arial', 14, 'bold'))
title_label.grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 0), sticky="nsew")

subtitle_label = tk.Label(root, text="Extracts .ogg files from Minecraft assets with functionality to convert to other formats.")
subtitle_label.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="nsew")

# Label and Entry for Minecraft Folder
minecraft_label = tk.Label(root, text="Select .minecraft Folder:")
minecraft_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

minecraft_folder_entry = tk.Entry(root, width=50)
minecraft_folder_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="we")

# Browse button for .minecraft folder
browse_minecraft_button = tk.Button(root, text="Browse", command=browse_minecraft_folder)
browse_minecraft_button.grid(row=2, column=3, padx=10, pady=10)

# Include tooltip for user for .minecraft directory
ToolTip(browse_minecraft_button, "Select the .minecraft folder located in %APPDATA%/Roaming")

# Label and Entry for Output Directory
output_label = tk.Label(root, text="Select Output Directory:")
output_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")

output_folder_entry = tk.Entry(root, width=50)
output_folder_entry.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="we")

# Browse button for output directory
browse_output_button = tk.Button(root, text="Browse", command=browse_output_folder)
browse_output_button.grid(row=3, column=3, padx=10, pady=10)

# Include tooltip for user for output directory
ToolTip(browse_output_button, "Select the desired output directory")

# Checkboxes for additional formats
mp3_var = tk.BooleanVar()
mp3_checkbox = tk.Checkbutton(root, text="MP3", variable=mp3_var)
mp3_checkbox.grid(row=4, column=0, padx=10, pady=10, sticky="w")

# Include tooltip for conversion clarification.
ToolTip(mp3_checkbox, "Convert .ogg files to the .mp3 format.")

flac_var = tk.BooleanVar()
flac_checkbox = tk.Checkbutton(root, text="FLAC", variable=flac_var)
flac_checkbox.grid(row=4, column=1, padx=10, pady=10, sticky="w")

# Include tooltip for conversion clarification.
ToolTip(flac_checkbox, "Convert .ogg files to the .flac format.")

wav_var = tk.BooleanVar()
wav_checkbox = tk.Checkbutton(root, text="WAV", variable=wav_var)
wav_checkbox.grid(row=4, column=2, padx=10, pady=10, sticky="w")

# Include tooltip for conversion clarification.
ToolTip(wav_checkbox, "Convert .ogg files to the .wav format.")

# Checkbox to keep ogg files
keep_ogg_var = tk.BooleanVar(value=True)
keep_ogg_checkbox = tk.Checkbutton(root, text="Keep OGG Files", variable=keep_ogg_var)
keep_ogg_checkbox.grid(row=4, column=3, padx=10, pady=10, sticky="w")

# Include tooltip for conversion clarification.
ToolTip(keep_ogg_checkbox, "If checked, keeps .ogg files. Otherwise, removes .ogg files after conversion if other formats selected.")

# Console Output Label and Text widget with automatic scrolling
console_label = tk.Label(root, text="Console Output:")
console_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")

console_text = tk.Text(root, width=80, height=10)
console_text.grid(row=6, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="nsew")
console_text.config(state=tk.DISABLED)  # Start with disabled state for read-only

# Progress Bar
progress_bar = Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progress_bar.grid(row=7, column=0, columnspan=4, padx=10, pady=10)

# Button to start extraction process
extract_button = tk.Button(root, text="Extract Files", command=extract_ogg_files)
extract_button.grid(row=8, column=0, columnspan=4, padx=10, pady=(20, 20), sticky="n")

ToolTip(extract_button, "Click to start extraction. Extraction and conversion times may vary, please be patient!")

# Disable button resizing based on its content
extract_button.pack_propagate(False)

# Function to set minimum size based on content
def set_minimum_size(event=None):
    root.update_idletasks()
    min_width = root.winfo_reqwidth()
    min_height = root.winfo_reqheight()
    root.minsize(min_width, min_height)


# Call set_minimum_size when the window is resized
root.bind('<Configure>', set_minimum_size)

# Start the GUI main loop
root.mainloop()
