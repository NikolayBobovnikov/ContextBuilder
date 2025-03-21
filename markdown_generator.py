import os
from constants import MARKDOWN_HEADER_CONTEXT, MARKDOWN_HEADER_STRUCTURE, MARKDOWN_HEADER_FILES, MARKDOWN_CODE_BLOCK

class MarkdownGenerator:
    def __init__(self, directory, selected_files):
        self.directory = directory
        self.selected_files = selected_files
        from file_handler import FileHandler
        self.file_handler = FileHandler(self.directory)

    def generate(self):
        return f"{MARKDOWN_HEADER_CONTEXT}\n\n" \
               f"{self._generate_structure_section()}\n\n" \
               f"{self._generate_files_section()}"

    def _generate_structure_section(self):
        structure = self._generate_project_structure()
        return f"{MARKDOWN_HEADER_STRUCTURE}\n{MARKDOWN_CODE_BLOCK}\n{structure}\n{MARKDOWN_CODE_BLOCK}"

    def _generate_project_structure(self):
        structure_lines = []
        selected_dirs = {os.path.dirname(f) for f in self.selected_files}

        for root, dirs, files in os.walk(self.directory):
            if self.file_handler.is_ignored(root):
                continue

            level = root.replace(self.directory, "").count(os.sep)
            indent = "│   " * level
            basename = os.path.basename(root) or self.directory

            if root == self.directory or root in selected_dirs:
                branch = f"{indent}├── {basename}/" if level > 0 else basename
                structure_lines.append(branch)

                selected_files_in_dir = [
                    f for f in files
                    if os.path.join(root, f) in self.selected_files
                ]
                for i, file in enumerate(selected_files_in_dir):
                    file_indent = indent + ("    " if i == len(selected_files_in_dir)-1 else "│   ")
                    connector = "└──" if i == len(selected_files_in_dir)-1 else "├──"
                    structure_lines.append(f"{file_indent}{connector} {file}")

        return "\n".join(structure_lines)
    
    def is_ignored(self, path):
        return self.file_handler.is_ignored(path)

    def _generate_files_section(self):
        sections = []
        for file_path in self.selected_files:
            sections.append(self._generate_file_section(file_path))
        return f"{MARKDOWN_HEADER_FILES}\n\n" + "\n\n".join(sections)

    def _generate_file_section(self, file_path):
        rel_path = os.path.relpath(file_path, self.directory)
        extension = self._get_file_extension(file_path)
        content = self._read_file_content(file_path)
        return f"### {rel_path}\n\n{MARKDOWN_CODE_BLOCK}{extension}\n{content}\n{MARKDOWN_CODE_BLOCK}"

    def _read_file_content(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except UnicodeDecodeError:
            with open(file_path, "rb") as f:
                return f.read().decode('utf-8', errors='ignore').strip()

    def _get_file_extension(self, file_path):
        _, ext = os.path.splitext(file_path)
        return ext[1:] if ext.startswith('.') else ext 