import os
import tkinter as tk
from tkinter import ttk

class UIBuilder:
    def __init__(self, root):
        self.root = root
        self.tree = None
        self.directory_label = None
        self.start_button = None
        self.stop_button = None
        self._item_path_map = {}
        self._setup_main_frame()

    def _setup_main_frame(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Directory selection frame
        frame = tk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text="Selected Directory:").grid(row=0, column=0, sticky="w")
        self.directory_label = tk.Label(frame, text="")
        self.directory_label.grid(row=0, column=1, sticky="ew")
        
        tk.Button(frame, text="Open Directory", command=lambda: None).grid(row=0, column=2, padx=(10, 0))

        # Treeview frame
        self.tree_frame = tk.Frame(self.root)
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)

        self._setup_treeview()
        self._setup_control_buttons()

    def _setup_treeview(self):
        self.tree = ttk.Treeview(self.tree_frame, selectmode='none', show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _setup_control_buttons(self):
        self.start_button = tk.Button(
            self.root, text="Start Monitoring", state=tk.DISABLED
        )
        self.start_button.grid(row=2, column=0, pady=(10, 5))

        self.stop_button = tk.Button(
            self.root, text="Stop Monitoring", state=tk.DISABLED
        )
        self.stop_button.grid(row=3, column=0, pady=(5, 10))

    def populate_tree(self, structure):
        self.tree.delete(*self.tree.get_children())
        self._item_path_map.clear()
        self._build_tree_nodes('', structure)

    def _build_tree_nodes(self, parent, nodes):
        for node in nodes:
            item = self.tree.insert(
                parent, 'end', 
                text=f"☐ {node['name']}", 
                tags=('unchecked',)
            )
            self._item_path_map[item] = node['path']
            if node['is_dir']:
                self._build_tree_nodes(item, node['children'])

    def bind_tree_click(self, callback):
        self.tree.bind("<Button-1>", lambda e: self._handle_tree_click(e, callback))

    def _handle_tree_click(self, event, callback):
        item = self.tree.identify_row(event.y)
        if not item or self._is_expander_clicked(event, item):
            return

        tags = self.tree.item(item, "tags")
        new_tags = ('checked',) if 'checked' not in tags else ('unchecked',)
        self.tree.item(item, tags=new_tags, text=f"☑ {self.tree.item(item, 'text')[2:]}" if new_tags == ('checked',) else f"☐ {self.tree.item(item, 'text')[2:]}")

        # Propagate selection to children
        if new_tags == ('checked',):
            self._check_children(item)
        else:
            self._uncheck_children(item)
            
        # Update parent status
        self._update_parent(item)
        
        callback()

    def _is_expander_clicked(self, event, item):
        level = 0
        parent = self.tree.parent(item)
        while parent:
            level += 1
            parent = self.tree.parent(parent)
        return event.x < (level * 20 + 20)  # Assuming indent width of 20

    def _check_children(self, item):
        for child in self.tree.get_children(item):
            self.tree.item(
                child,
                tags=('checked',),
                text=f"☑ {self.tree.item(child, 'text')[2:]}"
            )
            self._check_children(child)

    def _uncheck_children(self, item):
        for child in self.tree.get_children(item):
            self.tree.item(
                child,
                tags=('unchecked',),
                text=f"☐ {self.tree.item(child, 'text')[2:]}"
            )
            self._uncheck_children(child)

    def _update_parent(self, item):
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
            self._update_parent(parent)

    def get_selected_files(self):
        return [
            self._item_path_map[item] 
            for item in self._item_path_map 
            if 'checked' in self.tree.item(item, 'tags')
            and not os.path.isdir(self._item_path_map[item])
        ]

    def set_directory_label(self, text):
        self.directory_label.config(text=text)

    def set_button_states(self, start_enabled, stop_enabled):
        self.start_button.config(state=tk.NORMAL if start_enabled else tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL if stop_enabled else tk.DISABLED) 