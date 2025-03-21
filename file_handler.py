import os
import fnmatch
from constants import ADDITIONAL_IGNORE_PATTERNS

class FileHandler:
    def __init__(self, directory):
        self.directory = directory
        self.ignore_patterns = []
        self._load_gitignore()
        self._add_hardcoded_patterns()

    def _load_gitignore(self):
        gitignore_path = os.path.join(self.directory, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8-sig') as f:
                    self.ignore_patterns.extend(
                        line.strip() for line in f 
                        if line.strip() and not line.startswith('#')
                    )
            except Exception as e:
                raise RuntimeError(f"Error reading .gitignore: {str(e)}")

    def _add_hardcoded_patterns(self):
        self.ignore_patterns.extend(ADDITIONAL_IGNORE_PATTERNS)

    def is_ignored(self, path):
        rel_path = os.path.relpath(path, self.directory).replace(os.sep, '/')
        if rel_path.startswith(".git/") or rel_path == ".git":
            return True

        for pattern in self.ignore_patterns:
            pattern = pattern.lstrip('/')
            if not pattern:
                continue

            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                if any(fnmatch.fnmatch(seg, dir_pattern) for seg in rel_path.split('/')):
                    return True
            else:
                if '/' not in pattern:
                    if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                        return True
                elif fnmatch.fnmatch(rel_path, pattern):
                    return True
        return False

    def get_directory_structure(self):
        structure = []
        self._walk_directory(self.directory, structure)
        return structure

    def _walk_directory(self, current_dir, parent_list):
        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        for entry in entries:
            full_path = os.path.join(current_dir, entry)
            if self.is_ignored(full_path):
                continue

            node = {
                'name': entry,
                'path': full_path,
                'is_dir': os.path.isdir(full_path),
                'children': []
            }
            parent_list.append(node)
            
            if node['is_dir']:
                self._walk_directory(full_path, node['children']) 