import os
import fnmatch
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import difflib


# Constants for markdown structure
MARKDOWN_HEADER_CONTEXT = "## Context"
MARKDOWN_HEADER_STRUCTURE = "### Project Structure"
MARKDOWN_HEADER_FILES = "### Files"
MARKDOWN_CODE_BLOCK = "```"


class MarkdownGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Markdown Generator")
        self.root.geometry("800x600")  # Set initial window size
        self.directory = ""
        self.gitignore_patterns = []

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

        # Button to generate markdown
        self.generate_button = tk.Button(self.root, text="Generate Markdown", command=self.generate_markdown, state=tk.DISABLED)
        self.generate_button.grid(row=2, column=0, pady=10)

    def open_directory(self):
        self.directory = filedialog.askdirectory()
        if not self.directory:
            return

        self.directory_label.config(text=self.directory)

        # Load .gitignore
        self.load_gitignore()

        # Populate tree with directory structure
        self.tree.delete(*self.tree.get_children())  # Clear any previous tree content
        self.populate_tree(self.directory, '')

        # Check if the generate button should be enabled
        self.check_generate_button_state()

    def load_gitignore(self):
        self.gitignore_patterns = []
        gitignore_path = os.path.join(self.directory, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                for line in f:
                    pattern = line.strip()
                    if pattern and not pattern.startswith('#'):
                        self.gitignore_patterns.append(pattern)

    def is_ignored(self, path):
        relative_path = os.path.relpath(path, self.directory)
        if relative_path == ".git":
            return True
        for pattern in self.gitignore_patterns:
            if pattern.endswith('/'):
                if fnmatch.fnmatch(relative_path + '/', pattern) or \
                   fnmatch.fnmatch(relative_path, pattern[:-1]):
                    return True
            else:
                if fnmatch.fnmatch(relative_path, pattern):
                    return True
        return False

    def populate_tree(self, parent_dir, parent_node):
        for entry in sorted(os.listdir(parent_dir)):
            full_path = os.path.join(parent_dir, entry)
            if self.is_ignored(full_path):
                continue

            # Insert item with an unchecked checkbox
            node = self.tree.insert(parent_node, 'end', text=f"☐ {entry}", open=False, tags=('unchecked',))

            if os.path.isdir(full_path):
                self.populate_tree(full_path, node)

            # Add checkbox toggle logic
            self.tree.tag_bind('unchecked', '<Button-1>', self.toggle_item)
            self.tree.tag_bind('checked', '<Button-1>', self.toggle_item)

             # Adjust scrollbar
            self.tree.update_idletasks()
            self.scrollbar.configure(command=self.tree.yview)

    def toggle_item(self, event):
        item = self.tree.identify('item', event.x, event.y)
        tag = self.tree.item(item, "tags")[0]
        if tag == 'unchecked':
            self.check_item(item)
        else:
            self.uncheck_item(item)

        # Check if the generate button should be enabled
        self.check_generate_button_state()

    def update_parent(self, item):
        parent = self.tree.parent(item)
        if parent:
            children = self.tree.get_children(parent)
            all_checked = all(self.tree.item(child, 'tags')[0] == 'checked' for child in children)
            if all_checked:
                self.tree.item(parent, tags=('checked',), text=f"☑ {self.tree.item(parent, 'text')[2:]}")
            else:
                self.tree.item(parent, tags=('unchecked',), text=f"☐ {self.tree.item(parent, 'text')[2:]}")
            self.update_parent(parent)

    def check_item(self, item):
        self.tree.item(item, tags=('checked',), text=f"☑ {self.tree.item(item, 'text')[2:]}")
        for child in self.tree.get_children(item):
            self.check_item(child)
        self.update_parent(item)

    def uncheck_item(self, item):
        self.tree.item(item, tags=('unchecked',), text=f"☐ {self.tree.item(item, 'text')[2:]}")
        for child in self.tree.get_children(item):
            self.uncheck_item(child)
        self.update_parent(item)

    def check_generate_button_state(self):
        selected_files = self.get_selected_files()
        if selected_files:
            self.generate_button.config(state=tk.NORMAL)
        else:
            self.generate_button.config(state=tk.DISABLED)

    def generate_markdown(self):
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No files selected", "Please select at least one file.")
            return

        markdown_content = self.create_markdown(selected_files)
        output_path = os.path.join(self.directory, "project_structure.md")

        try:
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as md_file:
                    existing_content = md_file.read()
                
                # Update only the Context section
                context_start = existing_content.find("## Context")
                if context_start != -1:
                    updated_content = existing_content[:context_start] + markdown_content
                else:
                    updated_content = existing_content + "\n\n" + markdown_content
            else:
                updated_content = markdown_content

            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write(updated_content)

            messagebox.showinfo("Markdown Generated", f"Markdown file updated at {output_path}")
            
            # Set up file watchers for selected files
            self.setup_file_watchers(selected_files)

        except UnicodeEncodeError as e:
            messagebox.showerror("Encoding Error", f"Error writing markdown file: {str(e)}")

    def get_selected_files(self):
        selected_files = []

        def collect_files(node, parent_path):
            item_path = os.path.join(parent_path, self.tree.item(node, 'text')[2:])  # Skip checkbox character
            if self.tree.item(node, 'tags')[0] == 'checked':
                if os.path.isfile(item_path):
                    selected_files.append(item_path)
                else:
                    for child in self.tree.get_children(node):
                        collect_files(child, item_path)

        for child in self.tree.get_children():
            collect_files(child, self.directory)

        return selected_files

    def create_markdown(self, selected_files):
        structure = self.generate_project_structure(selected_files)
        file_contents = self.get_selected_file_contents(selected_files)

        markdown_text = f"""\
{MARKDOWN_HEADER_CONTEXT}

{MARKDOWN_HEADER_STRUCTURE}
{structure}

{MARKDOWN_HEADER_FILES}
{file_contents}
"""

        return markdown_text

    def generate_project_structure(self, selected_files):
        structure = []
        selected_dirs = set(os.path.dirname(f) for f in selected_files)

        for root, dirs, files in os.walk(self.directory):
            if self.is_ignored(root):
                continue

            level = root.replace(self.directory, "").count(os.sep)
            indent = "│   " * level
            basename = os.path.basename(root)

            if root == self.directory or root in selected_dirs:
                branch = f"{indent}├── {basename}/" if level > 0 else basename
                structure.append(branch)

                selected_files_in_dir = [f for f in files if os.path.join(root, f) in selected_files and not self.is_ignored(os.path.join(root, f))]
                for i, file in enumerate(selected_files_in_dir):
                    file_indent = indent + "    " if i == len(selected_files_in_dir) - 1 else indent + "│   "
                    structure.append(f"{file_indent}└── {file}" if i == len(selected_files_in_dir) - 1 else f"{file_indent}├── {file}")

        return "\n".join(structure)

    def get_selected_file_contents(self, selected_files):
        content = []
        for file in selected_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    file_content = f.read().strip()
            except UnicodeDecodeError:
                with open(file, "rb") as f:
                    file_content = f.read().decode('utf-8', errors='ignore').strip()

            relative_file = os.path.relpath(file, self.directory)
            file_extension = self.get_file_extension(file)
            content.append(f"### {relative_file}\n\n{MARKDOWN_CODE_BLOCK}{file_extension}\n{file_content}\n{MARKDOWN_CODE_BLOCK}")
        
        return "\n\n".join(content)

    def setup_file_watchers(self, selected_files):
        # Remove existing watchers
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()

        # Set up new watcher
        self.observer = Observer()
        for file_path in selected_files:
            event_handler = FileChangeHandler(self, file_path)
            self.observer.schedule(event_handler, os.path.dirname(file_path), recursive=False)
        
        self.observer.start()

    def update_markdown_for_file(self, file_path):
        threading.Thread(target=self._update_markdown_for_file, args=(file_path,)).start()

    def _update_markdown_for_file(self, file_path):
        output_path = os.path.join(self.directory, "project_structure.md")
        if not os.path.exists(output_path):
            return

        with open(output_path, "r", encoding="utf-8") as md_file:
            content = md_file.read()

        relative_file = os.path.relpath(file_path, self.directory)
        file_header = f"#### {relative_file}"
        start_index = content.find(file_header)
        if start_index != -1:
            end_index = content.find("####", start_index + 1)
            if end_index == -1:
                end_index = content.find("</FILE_CONTENTS>", start_index)
            
            with open(file_path, "r", encoding="utf-8") as f:
                new_content = f.read().strip()

            file_extension = self.get_file_extension(file_path)
            updated_file_content = f"{file_header}\n```{file_extension}\n{new_content}\n```"
            
            updated_content = content[:start_index] + updated_file_content + content[end_index:]

            with open(output_path, "w", encoding="utf-8") as md_file:
                md_file.write(updated_content)

        self.update_project_structure(output_path)

    def update_project_structure(self, output_path):
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

    @staticmethod
    def get_file_extension(file):
        return file.split(".")[-1]

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app, file_path):
        self.app = app
        self.file_path = file_path

    def on_modified(self, event):
        if event.src_path == self.file_path:
            self.app.update_markdown_for_file(self.file_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = MarkdownGeneratorApp(root)
    root.mainloop()





