import os
import fnmatch
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Constants for markdown structure
MARKDOWN_HEADER_CONTEXT = "# Context"
MARKDOWN_HEADER_STRUCTURE = "## Project Structure"
MARKDOWN_HEADER_FILES = "## Files"
MARKDOWN_CODE_BLOCK = "```"

def setup_logging():
    # Ensure the logs directory exists
    logs_dir = os.path.join(".", "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Configure logging: both console and file handlers
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    
    # Console handler
    console_enabled = False
    if console_enabled:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    
    # File handler
    fh = logging.FileHandler(os.path.join(logs_dir, "app.log"), mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

setup_logging()
logging.info("Logging is configured.")

class MarkdownGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Markdown Generator")
        self.root.geometry("800x600")
        self.directory = ""
        self.ignore_patterns = []
        self.observer = None
        self.refresh_timer = None  # For debouncing selection changes

        logging.info("Initializing Markdown Generator App.")
        self.init_ui()

    

    def init_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Frame for directory selection
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text="Selected Directory:").grid(row=0, column=0, sticky="w")
        self.directory_label = tk.Label(frame, text="")
        self.directory_label.grid(row=0, column=1, sticky="ew")

        tk.Button(frame, text="Open Directory", command=self.open_directory).grid(row=0, column=2, padx=(10, 0))

        # Treeview for directory structure
        self.tree_frame = tk.Frame(self.root)
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.tree_frame, selectmode='none', show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Bind single click handler on the treeview (ignoring expand/collapse clicks)
        self.tree.bind("<Button-1>", self.on_tree_click, add="+")

        self.start_button = tk.Button(
            self.root,
            text="Start Monitoring",
            command=self.start_monitoring,
            state=tk.DISABLED # initially disabled
        )
        self.start_button.grid(row=2, column=0, pady=(10, 5))

        self.stop_button = tk.Button(
            self.root,
            text="Stop Monitoring",
            command=self.stop_monitoring,
            state=tk.DISABLED  # initially disabled
        )
        self.stop_button.grid(row=3, column=0, pady=(5, 10))

    def start_monitoring(self):
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No files selected", "Please select at least one file.")
            return

        # Generate the markdown file initially
        self.generate_markdown()

        # Set up file watchers for live updates
        self.setup_file_watchers(selected_files)

        # Update buttons
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        logging.info("Monitoring started.")

    def stop_monitoring(self):
        if self.observer:
            logging.info("Stopping file watchers.")
            self.observer.stop()
            self.observer.join()
            self.observer = None
            messagebox.showinfo("Stopped", "File monitoring has been stopped.")

        # Update buttons
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)


    def on_tree_click(self, event):
        try:
            item = self.tree.identify_row(event.y)
            if not item:
                return

            # Determine the level (depth) of the item by counting its ancestors.
            level = 0
            parent = self.tree.parent(item)
            while parent:
                level += 1
                parent = self.tree.parent(parent)

            indent = 20
            OPEN_BUTTON_WIDTH = 20

            if event.x < (level * indent + OPEN_BUTTON_WIDTH):
                return

            tags = self.tree.item(item, "tags")
            if 'checked' in tags:
                self.uncheck_item(item)
                logging.debug(f"Unchecked item: {self.tree.item(item, 'text')}")
            else:
                self.check_item(item)
                logging.debug(f"Checked item: {self.tree.item(item, 'text')}")
            
            self.check_generate_button_state()  # Now uses start_button

            # If monitoring is active, debounce and refresh the markdown
            if self.observer:
                if self.refresh_timer:
                    self.root.after_cancel(self.refresh_timer)
                self.refresh_timer = self.root.after(500, self.refresh_selection)
            return "break"
        except Exception:
            logging.exception("Error in on_tree_click callback")
            raise


    def refresh_selection(self):
        logging.info("Selection changed; refreshing markdown file.")
        self.generate_markdown(show_message=False)
        self.refresh_timer = None  # Reset the timer variable


    def open_directory(self):
        self.directory = filedialog.askdirectory()
        if not self.directory:
            return

        self.directory_label.config(text=self.directory)
        logging.info(f"Directory selected: {self.directory}")

        # Load .gitignore patterns (if available)
        self.load_gitignore()

        # Clear and populate the treeview
        self.tree.delete(*self.tree.get_children())
        self.populate_tree(self.directory, '')

        self.check_generate_button_state()

    def load_gitignore(self):
        """Load ignore patterns from .gitignore in the selected directory and add hardcoded patterns."""
        self.ignore_patterns = []
        gitignore_path = os.path.join(self.directory, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                # Use 'utf-8-sig' to handle BOM if present
                with open(gitignore_path, 'r', encoding="utf-8-sig") as f:
                    for line in f:
                        pattern = line.strip()
                        if pattern and not pattern.startswith('#'):
                            self.ignore_patterns.append(pattern)
                logging.info(f"Loaded {len(self.ignore_patterns)} .gitignore patterns from file: {self.ignore_patterns}")
            except Exception as e:
                logging.error(f"Error reading .gitignore: {str(e)}")
                messagebox.showerror("Error", f"Error reading .gitignore: {str(e)}")
        else:
            logging.info("No .gitignore file found.")

        # Add additional hardcoded patterns
        additional_patterns = [
            ".git/", 
            ".gitignore", 
            "requirements.txt", 
            "package-lock.json",
            "*.ico",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.bmp",
            "*.tiff",
            "*.svg",
            "*.bin",
            "*.exe",
            "*.dll",
            "*.lib",
            "*.exp",
            "*.obj",
            "*.def",
            "*.db",
            "*.sqlite*",
            "*.log",
            "*.tmp"
            ]
        self.ignore_patterns.extend(additional_patterns)
        logging.info(f"Total number of ignore patterns: {len(self.ignore_patterns)}")
        logging.debug(f"Ignore patterns: {self.ignore_patterns}")

    def is_ignored(self, path):
        """Determine if the given path should be ignored based on .gitignore and hardcoded patterns.
        
        The function converts the path to a relative path (using forward slashes). For directory
        patterns (ending with '/'), it checks if any segment of the path matches the wildcard pattern.
        For patterns that don't contain a slash, it checks the basename (so that a pattern like 
        'package-lock.json' will match regardless of its directory).
        """
        relative_path = os.path.relpath(path, self.directory)
        relative_path = relative_path.replace(os.sep, '/')
        if relative_path.startswith(".git/") or relative_path == ".git":
            return True

        for pattern in self.ignore_patterns:
            # Remove leading slash if present, making the pattern relative to the project root.
            if pattern.startswith('/'):
                pattern = pattern[1:]
            if pattern.endswith('/'):
                # For directory patterns, remove trailing slash and check each segment.
                dir_pattern = pattern.rstrip('/')
                for segment in relative_path.split('/'):
                    if fnmatch.fnmatch(segment, dir_pattern):
                        return True
            else:
                # If the pattern doesn't include a slash, match against the basename.
                if '/' not in pattern:
                    if fnmatch.fnmatch(os.path.basename(relative_path), pattern):
                        return True
                else:
                    # Otherwise, match the full relative path.
                    if fnmatch.fnmatch(relative_path, pattern):
                        return True
        return False

    def populate_tree(self, parent_dir, parent_node):
        """Recursively populate the treeview with files and folders, skipping ignored paths."""
        try:
            entries = sorted(os.listdir(parent_dir))
        except PermissionError as e:
            logging.warning(f"Permission denied for directory: {parent_dir} ({e})")
            return

        for entry in entries:
            full_path = os.path.join(parent_dir, entry)
            if self.is_ignored(full_path):
                logging.debug(f"Ignored: {full_path}")
                continue

            node = self.tree.insert(
                parent_node,
                'end',
                text=f"☐ {entry}",
                open=False,
                tags=('unchecked',)
            )
            logging.debug(f"Added node: {full_path}")

            if os.path.isdir(full_path):
                self.populate_tree(full_path, node)

            self.tree.update_idletasks()
            self.scrollbar.configure(command=self.tree.yview)

    def update_parent(self, item):
        parent = self.tree.parent(item)
        if parent:
            children = self.tree.get_children(parent)
            all_checked = all('checked' in self.tree.item(child, 'tags') for child in children)
            if all_checked:
                self.tree.item(
                    parent,
                    tags=('checked',),
                    text=f"☑ {self.tree.item(parent, 'text')[2:]}"
                )
            else:
                self.tree.item(
                    parent,
                    tags=('unchecked',),
                    text=f"☐ {self.tree.item(parent, 'text')[2:]}"
                )
            self.update_parent(parent)

    def check_item(self, item):
        """Mark an item and its children as checked."""
        self.tree.item(
            item,
            tags=('checked',),
            text=f"☑ {self.tree.item(item, 'text')[2:]}"
        )
        for child in self.tree.get_children(item):
            self.check_item(child)
        self.update_parent(item)

    def uncheck_item(self, item):
        """Mark an item and its children as unchecked."""
        self.tree.item(
            item,
            tags=('unchecked',),
            text=f"☐ {self.tree.item(item, 'text')[2:]}"
        )
        for child in self.tree.get_children(item):
            self.uncheck_item(child)
        self.update_parent(item)

    def check_generate_button_state(self):
        # If monitoring is active, always keep the start button disabled.
        if self.observer is not None:
            self.start_button.config(state=tk.DISABLED)
        else:
            # Otherwise, enable start button only if there are selected files.
            if self.get_selected_files():
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)


    def generate_markdown(self, show_message=True):
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No files selected", "Please select at least one file.")
            return

        logging.info(f"Generating markdown for {len(selected_files)} selected files.")
        markdown_content = self.create_markdown(selected_files)
        output_path = os.path.join(self.directory, "project_structure.md")

        try:
            # Overwrite the markdown file completely
            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_content)

            logging.info(f"Markdown file written at {output_path}")
            if show_message:
                messagebox.showinfo("Markdown Generated", f"Markdown file updated at {output_path}")

            # Restart file watchers only on a manual generation call
            if show_message:
                self.setup_file_watchers(selected_files)
        except UnicodeEncodeError as e:
            logging.error(f"Encoding Error writing markdown: {str(e)}")
            messagebox.showerror("Encoding Error", f"Error writing markdown file: {str(e)}")


    def get_selected_files(self):
        """Collect all checked files (even if nested) based on treeview state."""
        selected_files = []

        def collect_files(node, parent_path):
            item_text = self.tree.item(node, 'text')[2:]
            item_path = os.path.join(parent_path, item_text)
            if os.path.isfile(item_path) and ('checked' in self.tree.item(node, 'tags')):
                selected_files.append(item_path)
            if os.path.isdir(item_path):
                for child in self.tree.get_children(node):
                    collect_files(child, item_path)

        for child in self.tree.get_children():
            collect_files(child, self.directory)
        logging.debug(f"Selected files: {selected_files}")
        return selected_files

    def create_markdown(self, selected_files):
        structure = self.generate_project_structure(selected_files)
        file_contents = self.get_selected_file_contents(selected_files)

        markdown_text = f"""{MARKDOWN_HEADER_CONTEXT}

{MARKDOWN_HEADER_STRUCTURE}
{structure}

{MARKDOWN_HEADER_FILES}
{file_contents}
"""
        logging.debug("Markdown content created.")
        return markdown_text

    def generate_project_structure(self, selected_files):
        structure_lines = []
        selected_dirs = set(os.path.dirname(f) for f in selected_files)

        for root, dirs, files in os.walk(self.directory):
            if self.is_ignored(root):
                continue

            level = root.replace(self.directory, "").count(os.sep)
            indent = "│   " * level
            basename = os.path.basename(root) if os.path.basename(root) else self.directory

            if root == self.directory or root in selected_dirs:
                branch = f"{indent}├── {basename}/" if level > 0 else basename
                structure_lines.append(branch)

                selected_files_in_dir = [
                    f for f in files
                    if os.path.join(root, f) in selected_files and not self.is_ignored(os.path.join(root, f))
                ]
                for i, file in enumerate(selected_files_in_dir):
                    file_indent = indent + "    " if i == len(selected_files_in_dir) - 1 else indent + "│   "
                    connector = "└──" if i == len(selected_files_in_dir) - 1 else "├──"
                    structure_lines.append(f"{file_indent}{connector} {file}")

        logging.debug("Project structure generated.")
        return f"{MARKDOWN_CODE_BLOCK}\n" + "\n".join(structure_lines) + f"\n{MARKDOWN_CODE_BLOCK}"

    def get_selected_file_contents(self, selected_files):
        contents = []
        for file in selected_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    file_content = f.read().strip()
            except UnicodeDecodeError:
                with open(file, "rb") as f:
                    file_content = f.read().decode('utf-8', errors='ignore').strip()

            relative_file = os.path.relpath(file, self.directory)
            file_extension = self.get_file_extension(file)
            section = f"### {relative_file}\n\n{MARKDOWN_CODE_BLOCK}{file_extension}\n{file_content}\n{MARKDOWN_CODE_BLOCK}"
            contents.append(section)
        logging.debug("File contents extracted for markdown.")
        return "\n\n".join(contents)

    def setup_file_watchers(self, selected_files):
        """Set up file watchers for live updates to the markdown file."""
        if self.observer:
            logging.info("Stopping previous file watchers.")
            self.observer.stop()
            self.observer.join()

        self.observer = Observer()
        for file_path in selected_files:
            event_handler = FileChangeHandler(self, file_path)
            self.observer.schedule(event_handler, os.path.dirname(file_path), recursive=False)
            logging.debug(f"File watcher set for: {file_path}")

        self.observer.start()
        logging.info("File watchers started.")

    def update_markdown_for_file(self, file_path):
        logging.info(f"Updating markdown for modified file: {file_path}")
        threading.Thread(target=self._update_markdown_for_file, args=(file_path,)).start()

    def _update_markdown_for_file(self, file_path):
        output_path = os.path.join(self.directory, "project_structure.md")
        if not os.path.exists(output_path):
            logging.warning("Output markdown file does not exist.")
            return

        with open(output_path, "r", encoding="utf-8") as md_file:
            content = md_file.read()

        relative_file = os.path.relpath(file_path, self.directory)
        file_header = f"### {relative_file}"
        start_index = content.find(file_header)
        if start_index != -1:
            end_index = content.find("###", start_index + 1)
            if end_index == -1:
                end_index = len(content)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    new_content = f.read().strip()
            except UnicodeDecodeError:
                with open(file_path, "rb") as f:
                    new_content = f.read().decode('utf-8', errors='ignore').strip()

            file_extension = self.get_file_extension(file_path)
            updated_file_content = f"{file_header}\n{MARKDOWN_CODE_BLOCK}{file_extension}\n{new_content}\n{MARKDOWN_CODE_BLOCK}"
            updated_content = content[:start_index] + updated_file_content + content[end_index:]

            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write(updated_content)

            logging.info(f"Markdown updated for file: {relative_file}")
            self.update_project_structure(output_path)
        else:
            logging.warning(f"Header for {relative_file} not found in markdown.")

    def update_project_structure(self, output_path):
        """Update the project structure section if applicable (requires markers)."""
        with open(output_path, "r", encoding="utf-8") as md_file:
            content = md_file.read()

        structure_start = content.find("<PROJECT_STRUCTURE>")
        structure_end = content.find("</PROJECT_STRUCTURE>")
        if structure_start != -1 and structure_end != -1:
            selected_files = self.get_selected_files()
            new_structure = self.generate_project_structure(selected_files)
            updated_content = (
                content[:structure_start + len("<PROJECT_STRUCTURE>\n")] +
                new_structure +
                content[structure_end:]
            )

            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write(updated_content)
            logging.info("Project structure updated in markdown.")

    @staticmethod
    def get_file_extension(file):
        """Return the file extension without the leading dot."""
        _, ext = os.path.splitext(file)
        return ext[1:] if ext.startswith('.') else ext


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, file_path):
        self.app = app
        self.file_path = file_path

    def on_modified(self, event):
        if event.src_path == self.file_path:
            logging.info(f"Detected modification in {self.file_path}")
            self.app.update_markdown_for_file(self.file_path)


if __name__ == "__main__":
    root = tk.Tk()

    def tk_report_callback_exception(exc, val, tb):
        logging.error("Exception in Tkinter callback", exc_info=(exc, val, tb))
    root.report_callback_exception = tk_report_callback_exception

    app = MarkdownGeneratorApp(root)
    root.mainloop()
