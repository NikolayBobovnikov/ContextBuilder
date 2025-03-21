# Markdown constants
MARKDOWN_HEADER_CONTEXT = "# Context"
MARKDOWN_HEADER_STRUCTURE = "## Project Structure"
MARKDOWN_HEADER_FILES = "## Files"
MARKDOWN_CODE_BLOCK = "```"

# Application settings
DEFAULT_WINDOW_SIZE = "800x600"
DEFAULT_WINDOW_TITLE = "Markdown Generator"
OUTPUT_FILENAME = "project_structure.md"

# File handling settings
ADDITIONAL_IGNORE_PATTERNS = [
    ".git/", ".gitignore", "requirements.txt", "package-lock.json",
    "*.ico", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.tiff",
    "*.svg", "*.bin", "*.exe", "*.dll", "*.lib", "*.exp", "*.obj",
    "*.def", "*.db", "*.sqlite*", "*.log", "*.tmp"
] 