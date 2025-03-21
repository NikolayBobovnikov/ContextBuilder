import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import logging

from logging_config import setup_logging
from file_handler import FileHandler
from markdown_generator import MarkdownGenerator
from file_monitor import FileMonitor
from ui_builder import UIBuilder
from constants import DEFAULT_WINDOW_TITLE, DEFAULT_WINDOW_SIZE, OUTPUT_FILENAME

class MarkdownGeneratorApp:
    def __init__(self, root):
        setup_logging()
        logging.info("Initializing Markdown Generator App.")
        
        self.root = root
        self.root.title(DEFAULT_WINDOW_TITLE)
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        
        self.directory = ""
        self.file_handler = None
        self.file_monitor = FileMonitor(self.update_markdown_for_file)
        self.ui = UIBuilder(root)
        self.refresh_timer = None
        self.markdown_lock = threading.Lock()
        
        self._setup_ui_callbacks()

    def _setup_ui_callbacks(self):
        self.ui.tree.bind("<Button-1>", self.on_tree_click)
        self.ui.start_button.config(command=self.start_monitoring)
        self.ui.stop_button.config(command=self.stop_monitoring)
        
        # Set the open directory command for the button in UI
        self.ui.root.children['!frame'].children['!button'].config(command=self.open_directory)
        
        self.root.report_callback_exception = self._handle_exception
        
    def _handle_exception(self, exc, val, tb):
        logging.error("Uncaught exception", exc_info=(exc, val, tb))

    def open_directory(self):
        self.directory = filedialog.askdirectory()
        if not self.directory:
            return

        try:
            self.file_handler = FileHandler(self.directory)
            self.ui.set_directory_label(self.directory)
            structure = self.file_handler.get_directory_structure()
            self.ui.populate_tree(structure)
            self._update_button_state()
            logging.info(f"Directory loaded: {self.directory}")
        except Exception as e:
            logging.error(f"Error loading directory: {str(e)}")
            messagebox.showerror("Error", str(e))

    def on_tree_click(self, event):
        try:
            item = self.ui.tree.identify_row(event.y)
            if not item:
                return
            
            # Check if click is on the expander button area
            level = 0
            parent = self.ui.tree.parent(item)
            while parent:
                level += 1
                parent = self.ui.tree.parent(parent)
            
            # If click is on the expander area, let default handling occur
            indent = 20
            if event.x < (level * indent + 20):  # 20 is OPEN_BUTTON_WIDTH
                return  # Return without "break" to allow default handling
            
            # Handle checkbox click
            self.ui._handle_tree_click(event, self._update_button_state)
            
            # Handle auto-refresh if monitoring is active
            if self.file_monitor.observer and self.file_monitor.observer.is_alive():
                if self.refresh_timer:
                    self.root.after_cancel(self.refresh_timer)
                self.refresh_timer = self.root.after(500, self.refresh_selection)
            
            return "break"  # Prevent default behavior only for checkbox clicks
        except Exception:
            logging.exception("Error in on_tree_click callback")
            raise

    def refresh_selection(self):
        logging.info("Selection changed; refreshing markdown file.")
        self.generate_markdown(show_message=False)
        self.refresh_timer = None

    def start_monitoring(self):
        selected_files = self.ui.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No files selected", "Please select at least one file.")
            return

        # Generate the markdown file initially
        self.generate_markdown()

        # Start file monitoring
        self.file_monitor.start(selected_files)
        
        # Update button states
        self.ui.set_button_states(False, True)
        logging.info("Monitoring started.")

    def stop_monitoring(self):
        self.file_monitor.stop()
        messagebox.showinfo("Stopped", "File monitoring has been stopped.")
        
        # Update button states
        self.ui.set_button_states(True, False)

    def _update_button_state(self):
        has_selection = bool(self.ui.get_selected_files())
        monitoring = self.file_monitor.observer and self.file_monitor.observer.is_alive()
        
        self.ui.set_button_states(has_selection and not monitoring, monitoring)

    def generate_markdown(self, show_message=True):
        selected_files = self.ui.get_selected_files()
        if not selected_files:
            if show_message:
                messagebox.showwarning("No files selected", "Please select at least one file.")
            return

        logging.info(f"Generating markdown for {len(selected_files)} selected files.")
        try:
            markdown_generator = MarkdownGenerator(self.directory, selected_files)
            markdown_content = markdown_generator.generate()
            
            output_path = os.path.join(self.directory, OUTPUT_FILENAME)
            
            with self.markdown_lock:
                with open(output_path, "w", encoding="utf-8") as md_file:
                    md_file.write(markdown_content)

            logging.info(f"Markdown file written at {output_path}")
            if show_message:
                messagebox.showinfo("Markdown Generated", f"Markdown file updated at {output_path}")
        except Exception as e:
            logging.error(f"Error generating markdown: {str(e)}")
            if show_message:
                messagebox.showerror("Error", f"Error generating markdown: {str(e)}")

    def update_markdown_for_file(self, file_path):
        logging.info(f"Updating markdown for modified file: {file_path}")
        threading.Thread(target=self._update_markdown_for_file, args=(file_path,)).start()

    def _update_markdown_for_file(self, file_path):
        output_path = os.path.join(self.directory, OUTPUT_FILENAME)
        if not os.path.exists(output_path):
            logging.warning("Output markdown file does not exist.")
            return

        try:
            with self.markdown_lock:
                with open(output_path, "r", encoding="utf-8") as md_file:
                    content = md_file.read()

                relative_file = os.path.relpath(file_path, self.directory)
                file_header = f"### {relative_file}"
                
                start_index = content.find(file_header)
                if start_index != -1:
                    end_index = content.find("###", start_index + 1)
                    if end_index == -1:
                        end_index = len(content)

                    # Generate new section for this file
                    file_section = MarkdownGenerator(self.directory, [file_path])._generate_file_section(file_path)
                    
                    # Replace the file content section
                    updated_content = content[:start_index] + file_section + content[end_index:]
                    
                    with open(output_path, "w", encoding="utf-8") as md_file:
                        md_file.write(updated_content)

                    logging.info(f"Markdown updated for file: {relative_file}")
                else:
                    logging.warning(f"Header for {relative_file} not found in markdown.")
        except Exception as e:
            logging.error(f"Error updating markdown for file {file_path}: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MarkdownGeneratorApp(root)
    root.mainloop()
