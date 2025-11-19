import os

root_dir = r"." #this . means use current directory (where cd is) as parent directory

# Folders to ignore
ignore_dirs = {"venvcpp", "__pycache__", ".git", ".vscode", "site-packages"}

# Extensions to show
show_ext = {".py", ".html", ".css"}

def print_tree(startpath, prefix=""):
    items = [i for i in os.listdir(startpath) if i not in ignore_dirs]
    for index, item in enumerate(sorted(items)):
        path = os.path.join(startpath, item)
        connector = "└── " if index == len(items) - 1 else "├── "
        if os.path.isdir(path):
            print(prefix + connector + item)
            extension = "    " if index == len(items) - 1 else "│   "
            print_tree(path, prefix + extension)
        else:
            # Only print files with the selected extensions
            if os.path.splitext(item)[1] in show_ext:
                print(prefix + connector + item)

print_tree(root_dir)
