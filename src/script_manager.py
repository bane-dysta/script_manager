import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import subprocess
import shutil
import os
from pathlib import Path
from src.config_manager import ConfigManager
from src.dialogs import ScriptConfigDialog, OutputWindow, EnvConfigDialog, CategoryDialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from src.runners import RunnerFactory

class ScriptManager:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("脚本管理器")

        # 树形列表的拖拽排序状态
        self.drag_state = {
            "tree": None,
            "item": None,
            "script": None,
            "source_category": None,
            "script_type": None,
            "start_y": 0,
            "dragging": False,
        }
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config

        # 恢复窗口大小设置（只保存 WxH，不保存位置）
        window_size = self.config.get("settings", {}).get("window_size", "750x500")
        self.root.geometry(window_size)
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_close)
        
        # 脚本类型定义
        self.script_types = {
            "python": {
                "name": "Python脚本",
                "extensions": [".py"],
                "needs_env": True,
                "supports_output": True,
                "supports_interactive": True,
                "icon": "🐍"  # 可选的图标
            },
            "powershell": {
                "name": "PowerShell脚本",
                "extensions": [".ps1", ".psm1", ".psd1"],
                "needs_env": False,
                "supports_output": True,
                "supports_interactive": True,
                "icon": "💻"
            },
            "batch": {
                "name": "批处理脚本",
                "extensions": [".bat", ".cmd"],
                "needs_env": False,
                "supports_output": True,
                "supports_interactive": True,
                "icon": "📜"
            },
            "executable": {
                "name": "可执行文件",
                "extensions": [".exe"],
                "needs_env": False,
                "supports_output": False,
                "supports_interactive": False,
                "icon": "⚙️"
            }
        }
        
        self.create_menu()
        self.create_toolbar()
        self.create_gui()
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="添加脚本", command=self.add_script, accelerator="Ctrl+N")
        file_menu.add_command(label="编辑脚本", command=self.edit_script_config, accelerator="Ctrl+E")
        file_menu.add_command(label="删除脚本", command=self.remove_script, accelerator="Delete")
        file_menu.add_separator()
        file_menu.add_command(label="编辑分类", command=self.edit_categories)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit, accelerator="Alt+F4")
        
        # 环境菜单
        env_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="环境", menu=env_menu)
        env_menu.add_command(label="添加环境", command=self.add_env)
        env_menu.add_command(label="删除环境", command=self.remove_env)
        env_menu.add_command(label="测试环境", command=self.test_env)
        
        # 绑定快捷键
        self.root.bind("<Control-n>", lambda e: self.add_script())
        self.root.bind("<Control-e>", lambda e: self.edit_script_config())
        self.root.bind("<Delete>", lambda e: self.remove_script())
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        # 搜索框
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_scripts)
        ttk.Entry(toolbar, textvariable=self.search_var).pack(side=tk.LEFT, fill='x', expand=True)
    
    def create_gui(self):
        """创建主界面"""
        # 创建主分割窗口
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 左侧面板
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # 创建脚本类型notebook
        self.script_notebook = ttk.Notebook(left_frame)
        self.script_notebook.pack(fill='both', expand=True)
        
        # 为每种脚本类型创建页面
        self.script_pages = {}
        self.script_trees = {}
        self.tree_item_refs = {}
        
        for script_type, info in self.script_types.items():
            page = ttk.Frame(self.script_notebook)
            self.script_notebook.add(page, text=f"{info['icon']} {info['name']}")
            self.script_pages[script_type] = page
            
            # 创建树形视图
            tree = self.create_script_tree(page, script_type)
            self.script_trees[script_type] = tree
            self.tree_item_refs[script_type] = {}
            
            # 创建按钮框
            self.create_script_buttons(page, script_type)
        
        # 右侧配置面板
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)
        
        # 脚本信息面板
        info_frame = ttk.LabelFrame(right_paned, text="脚本信息")
        right_paned.add(info_frame, weight=1)
        self.create_info_panel(info_frame)
        
        # 运行配置面板
        config_frame = ttk.LabelFrame(right_paned, text="运行配置")
        right_paned.add(config_frame, weight=2)
        self.create_run_config_panel(config_frame)
        
        # 绑定notebook切换事件
        self.script_notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
    
    def create_script_tree(self, parent, script_type):
        """创建脚本树形视图"""
        # 创建树形视图和滚动条的容器
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True)
        
        # 创建内部框架用于grid布局
        inner_frame = ttk.Frame(tree_frame)
        inner_frame.pack(fill='both', expand=True)
        
        tree = ttk.Treeview(inner_frame, selectmode='browse')
        
        # 创建滚动条
        y_scrollbar = ttk.Scrollbar(inner_frame, orient='vertical', command=tree.yview)
        x_scrollbar = ttk.Scrollbar(inner_frame, orient='horizontal', command=tree.xview)
        
        # 配置树形视图的滚动
        tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )
        
        # 配置列
        if script_type == "python":
            tree['columns'] = ('env', 'description')
            tree.column('env', width=100)
        else:
            tree['columns'] = ('description',)
        
        tree.column('#0', width=200)
        tree.column('description', width=300)
        
        tree.heading('#0', text='名称')
        if script_type == "python":
            tree.heading('env', text='环境')
        tree.heading('description', text='描述')
        
        # 使用grid布局
        tree.grid(row=0, column=0, sticky='nsew')
        y_scrollbar.grid(row=0, column=1, sticky='ns')
        x_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # 配置grid权重
        inner_frame.grid_rowconfigure(0, weight=1)
        inner_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定事件
        tree.bind('<<TreeviewSelect>>', lambda e: self.on_script_select(e, script_type))
        tree.bind('<Double-1>', lambda e: self.run_script())
        tree.bind('<ButtonPress-1>', lambda e, st=script_type: self.on_tree_drag_start(e, st))
        tree.bind('<B1-Motion>', lambda e, st=script_type: self.on_tree_drag_motion(e, st))
        tree.bind('<ButtonRelease-1>', lambda e, st=script_type: self.on_tree_drag_release(e, st))
        
        # 启用拖放功能
        tree.drop_target_register(DND_FILES)
        tree.dnd_bind('<<Drop>>', lambda e, st=script_type: self.on_drop_script(e, st))
        
        return tree
    
    def create_script_buttons(self, parent, script_type):
        """创建脚本操作按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(
            btn_frame, 
            text="添加脚本",
            command=lambda: self.add_script(script_type=script_type)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="编辑脚本",
            command=self.edit_script_config
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="删除脚本",
            command=self.remove_script
        ).pack(side=tk.LEFT, padx=2)
    
    def create_info_panel(self, parent):
        """创建脚本信息面板"""
        # 脚本路径
        path_frame = ttk.Frame(parent)
        path_frame.pack(fill='x', padx=5, pady=2)
        ttk.Label(path_frame, text="路径:").pack(side=tk.LEFT)
        self.path_label = ttk.Label(path_frame, text="")
        self.path_label.pack(side=tk.LEFT, fill='x', expand=True)

        
        # 脚本描述
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill='both', expand=True, padx=5, pady=2)
        ttk.Label(desc_frame, text="描述:").pack(anchor='w')
        self.desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD)
        self.desc_text.pack(fill='both', expand=True)
        self.desc_text.config(state='disabled')
    
    def create_run_config_panel(self, parent):
        """创建运行配置面板"""
        # 创建不同类型脚本的配置框架
        self.config_frames = {}
        self.config_widgets = {}
        
        # 创建保存设置复选框（全局）
        self.save_var = tk.BooleanVar(value=False)
        
        for script_type, info in self.script_types.items():
            frame = ttk.Frame(parent)
            self.config_frames[script_type] = frame
            # 初始化当前类型的控件字典
            widgets = {}
            self.config_widgets[script_type] = widgets
            
            if info["needs_env"]:
                # Python环境选择
                env_frame = ttk.Frame(frame)
                env_frame.pack(fill='x', padx=5, pady=2)
                ttk.Label(env_frame, text="Python环境:").pack(side=tk.LEFT)
                widgets['env_combo'] = ttk.Combobox(env_frame, state='readonly')
                widgets['env_combo'].pack(side=tk.LEFT, fill='x', expand=True)
            
            if info["supports_output"] or info["supports_interactive"]:
                # 命令行参数
                args_frame = ttk.Frame(frame)
                args_frame.pack(fill='x', padx=5, pady=2)
                ttk.Label(args_frame, text="命令行参数:").pack(side=tk.LEFT)
                widgets['args_entry'] = ttk.Entry(args_frame)
                widgets['args_entry'].pack(side=tk.LEFT, fill='x', expand=True)
                
                # 工作目录
                dir_frame = ttk.Frame(frame)
                dir_frame.pack(fill='x', padx=5, pady=2)
                ttk.Label(dir_frame, text="工作目录:").pack(side=tk.LEFT)
                widgets['dir_entry'] = ttk.Entry(dir_frame)
                widgets['dir_entry'].pack(side=tk.LEFT, fill='x', expand=True)
                ttk.Button(dir_frame, text="浏览", 
                          command=self.browse_dir).pack(side=tk.RIGHT)
                
                # 运行选项
                opt_frame = ttk.Frame(frame)
                opt_frame.pack(fill='x', padx=5, pady=2)
                
                if info["supports_output"]:
                    widgets['show_output_var'] = tk.BooleanVar(value=True)
                    widgets['show_output_check'] = ttk.Checkbutton(
                        opt_frame,
                        text="显示输出",
                        variable=widgets['show_output_var'],
                        command=lambda st=script_type: self.on_show_output_changed(st)
                    )
                    widgets['show_output_check'].pack(side=tk.LEFT)

                if info["supports_interactive"]:
                    widgets['interactive_var'] = tk.BooleanVar(value=False)
                    widgets['interactive_check'] = ttk.Checkbutton(
                        opt_frame,
                        text="交互模式",
                        variable=widgets['interactive_var'],
                        command=lambda st=script_type: self.on_interactive_changed(st)
                    )
                    widgets['interactive_check'].pack(side=tk.LEFT, padx=10)

                    widgets['capture_output_var'] = tk.BooleanVar(value=True)
                    widgets['capture_output_check'] = ttk.Checkbutton(
                        opt_frame,
                        text="捕获输出（取消则终端输出）",
                        variable=widgets['capture_output_var']
                    )
                    widgets['capture_output_check'].pack(side=tk.LEFT)

                # 添加保存设置复选框
                ttk.Checkbutton(opt_frame, text="保存为默认设置",
                              variable=self.save_var).pack(side=tk.LEFT, padx=10)

                self.update_run_option_states(script_type)
            
            # 运行按钮
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill='x', padx=5, pady=5)
            ttk.Button(btn_frame, text="运行脚本",
                      command=self.run_script).pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="用编辑器打开",
                      command=self.open_in_editor).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="打开所在文件夹",
                      command=self.open_script_location).pack(side=tk.LEFT)
        
        # 默认显示Python配置
        self.show_config_frame("python")

        # 初始化环境下拉框内容（即便没有环境管理页面也要能工作）
        self.update_env_list()
    
    def show_config_frame(self, script_type):
        """显示指定类型的配置框架"""
        # 隐藏所有配置框架
        for frame in self.config_frames.values():
            frame.pack_forget()
        
        # 显示指定类型的配置框架
        self.config_frames[script_type].pack(fill='both', expand=True)
    
    def on_tab_changed(self, event):
        """处理标签页切换事件"""
        current = self.script_notebook.select()
        tab_text = self.script_notebook.tab(current)["text"]
        
        # 从显示名称映射回类型键值
        script_type = None
        for type_key, info in self.script_types.items():
            if info['name'] in tab_text:  # 使用 in 因为tab_text包含图标
                script_type = type_key
                break
        
        if script_type:
            self.show_config_frame(script_type)
            self.update_script_list()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="运行", command=self.run_script)
        self.context_menu.add_command(label="编辑", command=self.edit_script_config)
        self.context_menu.add_command(label="打开所在文件夹", command=self.open_script_location)
        self.context_menu.add_command(label="用编辑器打开", command=self.open_in_editor)
        self.context_menu.add_command(label="删除", command=self.remove_script)
        
        # 绑定右键菜单
        for tree in self.script_trees.values():
            tree.bind('<Button-3>', self.show_context_menu)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        tree = event.widget
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def filter_scripts(self, *args):
        """根据搜索条件过滤脚本"""
        search_text = self.search_var.get().lower()
        self.update_script_list(search_text)
    
    def update_script_list(self, filter_text=""):
        """更新脚本列表"""
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        tree.delete(*tree.get_children())
        self.tree_item_refs[current_type] = {}
        
        scripts_by_category = self.config.get("scripts", {}) or {}

        # 获取当前类型的脚本（按用户设置的分类顺序展示）
        for category in self._ordered_categories():
            scripts = [
                s
                for s in scripts_by_category.get(category, [])
                if s.get("script_type", "python") == current_type
            ]
            visible_scripts = [
                s for s in scripts
                if not filter_text or filter_text in s.get("name", "").lower()
            ]
            
            if visible_scripts:
                category_node = tree.insert("", "end", text=category, open=True)
                for script in visible_scripts:
                    values = [script.get("description", "")]
                    if current_type == "python":
                        values.insert(0, script.get("env", ""))
                    
                    item_id = tree.insert(
                        category_node,
                        "end",
                        text=script["name"],
                        values=tuple(values)
                    )
                    self.tree_item_refs[current_type][item_id] = {
                        "category": category,
                        "script": script,
                    }
    
    def get_current_script_type(self):
        """获取当前选中的脚本类型"""
        current = self.script_notebook.select()
        tab_text = self.script_notebook.tab(current)["text"]
        
        # 从显示名称映射回类型键值
        for type_key, info in self.script_types.items():
            if info['name'] in tab_text:  # 使用 in 因为tab_text包含图标
                return type_key
        
        return "python"  # 默认返回python类型

    def _ordered_categories(self):
        """按照用户设置的分类顺序返回分类列表。"""
        scripts = self.config.get("scripts", {}) or {}
        categories = list(scripts.keys())

        order = (self.config.get("settings", {}) or {}).get("category_order", []) or []

        def sort_key(cat: str):
            if cat == "其他":
                return (2, 0)
            if cat in order:
                return (0, order.index(cat))
            return (1, cat)

        categories.sort(key=sort_key)
        return categories

    def _get_selected_script(self):
        """获取当前选中的脚本信息。

        返回 (script, category, script_type)。如果未选择脚本，则 script 为 None。
        """
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        selection = tree.selection()
        if not selection:
            return None, None, current_type

        item = selection[0]
        script, category = self._get_script_from_tree_item(current_type, item)
        return script, category, current_type

    def _get_script_from_tree_item(self, script_type, item_id):
        """根据树节点 id 获取脚本对象和所属分类。"""
        if not item_id:
            return None, None

        ref = self.tree_item_refs.get(script_type, {}).get(item_id)
        if ref:
            return ref.get("script"), ref.get("category")

        tree = self.script_trees.get(script_type)
        if tree is None:
            return None, None

        parent = tree.parent(item_id)
        if not parent:
            return None, None

        script_name = tree.item(item_id).get("text")
        category = tree.item(parent).get("text")
        script_list = (self.config.get("scripts", {}) or {}).get(category, [])
        script = next(
            (
                s
                for s in script_list
                if s.get("name") == script_name
                and s.get("script_type", "python") == script_type
            ),
            None,
        )
        return script, category

    def _get_selected_env_name(self):
        """尝试从界面状态中获取一个 Python 环境名称。"""
        # 1) 若有环境列表（env_tree），优先使用其选中项
        if hasattr(self, "env_tree"):
            try:
                selection = self.env_tree.selection()
                if selection:
                    return self.env_tree.item(selection[0]).get("text", "").strip()
            except Exception:
                pass

        # 2) 否则尝试使用右侧 Python 配置面板的下拉框
        widgets = self.config_widgets.get("python", {})
        env_combo = widgets.get("env_combo")
        if env_combo is not None:
            name = (env_combo.get() or "").strip()
            if name:
                return name

        # 3) 如果只有一个环境，直接返回
        envs = self.config.get("python_environments", []) or []
        if len(envs) == 1:
            return (envs[0].get("name") or "").strip()

        # 4) 最后兜底：让用户输入环境名称
        if envs:
            hint = "、".join([e.get("name", "") for e in envs if e.get("name")])
            prompt = f"请输入要操作的环境名称（可选：{hint}）:"
        else:
            prompt = "当前未配置任何 Python 环境，请先添加环境。"
        return (simpledialog.askstring("选择环境", prompt) or "").strip()
    
    def on_script_select(self, event, script_type):
        """处理脚本选择事件"""
        tree = event.widget
        selection = tree.selection()
        if not selection:
            return
        
        item = selection[0]
        script, category = self._get_script_from_tree_item(script_type, item)
        
        if script:
            # 更新信息面板
            self.path_label.config(text=script["path"])
            self.desc_text.config(state='normal')
            self.desc_text.delete('1.0', tk.END)
            self.desc_text.insert('1.0', script.get("description", ""))
            self.desc_text.config(state='disabled')
            
            # 获取当前类型的控件
            widgets = self.config_widgets[script_type]
            
            # 更新运行配置
            if script_type == "python" and "env_combo" in widgets:
                widgets['env_combo'].set(script["env"])
            
            if "args_entry" in widgets:
                widgets['args_entry'].delete(0, tk.END)
                if "arguments" in script:
                    widgets['args_entry'].insert(0, script["arguments"])
            
            if "dir_entry" in widgets:
                widgets['dir_entry'].delete(0, tk.END)
                if "working_dir" in script:
                    widgets['dir_entry'].insert(0, script["working_dir"])
            
            # 更新复选框状态
            if "show_output_var" in widgets:
                widgets['show_output_var'].set(script.get("show_output", True))
            if "interactive_var" in widgets:
                widgets['interactive_var'].set(script.get("interactive", False))
            if "capture_output_var" in widgets:
                widgets['capture_output_var'].set(script.get("capture_output", True))
            self.update_run_option_states(script_type)

    def _reset_drag_state(self):
        """重置脚本拖拽状态。"""
        tree = self.drag_state.get("tree")
        if tree is not None:
            try:
                tree.configure(cursor="")
            except Exception:
                pass

        self.drag_state = {
            "tree": None,
            "item": None,
            "script": None,
            "source_category": None,
            "script_type": None,
            "start_y": 0,
            "dragging": False,
        }

    def on_tree_drag_start(self, event, script_type):
        """记录拖拽起点，仅脚本节点允许参与排序。"""
        tree = event.widget
        item = tree.identify_row(event.y)
        script, category = self._get_script_from_tree_item(script_type, item)

        if not script:
            self._reset_drag_state()
            return

        self.drag_state = {
            "tree": tree,
            "item": item,
            "script": script,
            "source_category": category,
            "script_type": script_type,
            "start_y": event.y,
            "dragging": False,
        }

    def on_tree_drag_motion(self, event, script_type):
        """处理脚本树的拖拽过程。"""
        state = self.drag_state
        tree = event.widget

        if (
            state.get("tree") is not tree
            or state.get("script_type") != script_type
            or not state.get("item")
        ):
            return

        if not state.get("dragging"):
            if abs(event.y - state.get("start_y", 0)) < 5:
                return
            state["dragging"] = True

        try:
            tree.configure(cursor="fleur")
        except Exception:
            pass

        # 靠近顶部/底部时自动滚动，便于长列表拖动
        if event.y < 20:
            tree.yview_scroll(-1, "units")
        elif event.y > max(20, tree.winfo_height() - 20):
            tree.yview_scroll(1, "units")

    def _get_drop_target_item(self, tree, y):
        """获取拖拽释放时的目标节点。"""
        item = tree.identify_row(y)
        if item:
            return item

        categories = tree.get_children()
        if not categories:
            return ""

        if y < 0:
            first_category = categories[0]
            children = tree.get_children(first_category)
            return children[0] if children else first_category

        last_category = categories[-1]
        children = tree.get_children(last_category)
        return children[-1] if children else last_category

    def _rebuild_category_with_type_order(self, full_list, script_type, ordered_scripts):
        """按新的同类型顺序重建分类列表，保持其他类型脚本位置不变。"""
        ordered_iter = iter(ordered_scripts)
        rebuilt = []

        for item in full_list:
            if item.get("script_type", "python") == script_type:
                rebuilt.append(next(ordered_iter))
            else:
                rebuilt.append(item)

        return rebuilt

    def _reorder_scripts_in_same_category(self, category, script, target_script=None, place_after=False):
        """在同一分类内重排同类型脚本，保留其他类型脚本的插入位置。"""
        full_list = list((self.config.get("scripts", {}) or {}).get(category, []))
        script_type = script.get("script_type", "python")

        current_type_scripts = [
            item for item in full_list
            if item.get("script_type", "python") == script_type
        ]
        if script not in current_type_scripts:
            return False

        new_type_order = list(current_type_scripts)
        new_type_order.remove(script)

        if target_script is None:
            new_type_order.append(script)
        else:
            try:
                target_index = new_type_order.index(target_script)
            except ValueError:
                new_type_order.append(script)
            else:
                new_type_order.insert(target_index + (1 if place_after else 0), script)

        if new_type_order == current_type_scripts:
            return False

        self.config["scripts"][category] = self._rebuild_category_with_type_order(
            full_list,
            script_type,
            new_type_order,
        )
        return True

    def _get_cross_category_insert_index(self, target_list, script_type, target_script=None, place_after=False):
        """计算跨分类拖拽时在目标分类中的插入位置。"""
        if target_script is not None:
            try:
                target_index = target_list.index(target_script)
            except ValueError:
                target_index = None
            if target_index is not None:
                return target_index + (1 if place_after else 0)

        for index in range(len(target_list) - 1, -1, -1):
            if target_list[index].get("script_type", "python") == script_type:
                return index + 1

        return len(target_list)

    def _move_script_by_drag(self, script, source_category, target_category, target_script=None, place_after=False):
        """根据拖拽结果更新配置中的脚本顺序。"""
        if source_category == target_category:
            return self._reorder_scripts_in_same_category(
                source_category,
                script,
                target_script=target_script,
                place_after=place_after,
            )

        scripts_by_category = self.config.setdefault("scripts", {})
        source_list = list(scripts_by_category.get(source_category, []))
        target_list = list(scripts_by_category.get(target_category, []))

        if script not in source_list:
            return False

        source_list.remove(script)

        insert_index = self._get_cross_category_insert_index(
            target_list,
            script.get("script_type", "python"),
            target_script=target_script,
            place_after=place_after,
        )
        target_list.insert(insert_index, script)

        scripts_by_category[source_category] = source_list
        scripts_by_category[target_category] = target_list
        script["category"] = target_category
        return True

    def _select_script_in_tree(self, script_type, script):
        """刷新列表后重新选中指定脚本。"""
        tree = self.script_trees.get(script_type)
        if tree is None:
            return

        for item_id, ref in self.tree_item_refs.get(script_type, {}).items():
            if ref.get("script") is script:
                tree.selection_set(item_id)
                tree.focus(item_id)
                tree.see(item_id)
                tree.event_generate('<<TreeviewSelect>>')
                return

    def on_tree_drag_release(self, event, script_type):
        """拖拽释放时完成脚本重排。"""
        state = self.drag_state
        tree = event.widget

        if (
            state.get("tree") is not tree
            or state.get("script_type") != script_type
            or not state.get("item")
        ):
            self._reset_drag_state()
            return

        if not state.get("dragging"):
            self._reset_drag_state()
            return

        target_item = self._get_drop_target_item(tree, event.y)
        source_item = state.get("item")
        dragged_script = state.get("script")
        source_category = state.get("source_category")

        if not target_item or not dragged_script or not source_category:
            self._reset_drag_state()
            return

        target_script = None
        target_category = None
        place_after = False

        potential_target_script, potential_target_category = self._get_script_from_tree_item(script_type, target_item)
        if potential_target_script is not None:
            target_script = potential_target_script
            target_category = potential_target_category

            if target_script is dragged_script:
                self._reset_drag_state()
                return

            bbox = tree.bbox(target_item)
            if bbox:
                place_after = event.y >= bbox[1] + (bbox[3] / 2)
        else:
            target_category = tree.item(target_item).get("text")

        if not target_category:
            self._reset_drag_state()
            return

        moved = self._move_script_by_drag(
            dragged_script,
            source_category,
            target_category,
            target_script=target_script,
            place_after=place_after,
        )

        if moved:
            self.config_manager.save_config()
            self.update_script_list(self.search_var.get().lower())
            self._select_script_in_tree(script_type, dragged_script)

        self._reset_drag_state()
    
    def on_drop_script(self, event, script_type=None):
        """处理脚本文件拖放"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            # 获取文件扩展名
            ext = Path(file_path).suffix.lower()
            
            # 根据扩展名确定脚本类型
            detected_type = None
            for type_key, info in self.script_types.items():
                if ext in info["extensions"]:
                    detected_type = type_key
                    break
            
            # 如果找到匹配的类型，且与当前标签页类型相符或未指定类型
            if detected_type and (script_type is None or detected_type == script_type):
                # 添加脚本
                self.add_script(file_path, script_type=detected_type)
    
    def add_script(self, file_path=None, script_type=None):
        """添加新脚本"""
        try:
            # 如果没有提供文件路径，弹出文件选择对话框
            if not file_path:
                initial_dir = self.config.get("settings", {}).get("last_directory")
                if not initial_dir or not Path(initial_dir).exists():
                    initial_dir = str(Path.home())
            
                file_path = filedialog.askopenfilename(
                    title="选择脚本文件",
                    filetypes=[
                        ("所有支持的文件", "*.py;*.bat;*.cmd;*.ps1;*.psm1;*.psd1;*.exe"),
                        ("Python文件", "*.py"),
                        ("批处理文件", "*.bat;*.cmd"),
                        ("PowerShell脚本", "*.ps1;*.psm1;*.psd1"),
                        ("可执行文件", "*.exe"),
                        ("所有文件", "*.*")
                    ],
                    initialdir=initial_dir
                )
                if not file_path:  # 用户取消选择
                    return
        
            # 记住最后使用的目录
            if "settings" not in self.config:
                self.config["settings"] = self.config_manager.default_config["settings"]
            self.config["settings"]["last_directory"] = str(Path(file_path).parent)
            self.config_manager.save_config()
            
            # 根据文件扩展名确定默认脚本类型
            ext = Path(file_path).suffix.lower()
            if not script_type:
                for type, info in self.script_types.items():
                    if ext in info["extensions"]:
                        script_type = type
                        break
                else:
                    script_type = "python"
            
            # 弹出配置对话框（传入初始文件路径，用户可在对话框中修改）
            dialog = ScriptConfigDialog(
                self.root,
                self.config["python_environments"],
                path=file_path,
                categories=self.config["scripts"].keys(),
                script_type=script_type
            )
            
            if dialog.result:
                script_info = {
                    "name": dialog.script_name,
                    "path": getattr(dialog, "path", file_path),
                    "env": dialog.selected_env if script_type == "python" else "",
                    "description": dialog.description,
                    "category": dialog.category,
                    "script_type": script_type
                }
                
                category = script_info["category"]
                if category not in self.config["scripts"]:
                    category = self.config["settings"]["default_category"]
                self.config["scripts"][category].append(script_info)
                self.config_manager.save_config()
                self.update_script_list()
            
        except Exception as e:
            messagebox.showerror("错误", f"添加脚本时出错: {str(e)}")
    
    def remove_script(self):
        """删除选中的脚本"""
        script, category, _ = self._get_selected_script()
        if not script:
            return

        script_name = script.get("name", "")
        if messagebox.askyesno("确认", f"确定要删除脚本 {script_name} 吗?"):
            try:
                self.config.get("scripts", {}).get(category, []).remove(script)
            except Exception:
                pass
            self.config_manager.save_config()
            self.update_script_list()
            return
    
    def run_script(self):
        """运行选中的脚本"""
        script, category, current_type = self._get_selected_script()
        if not script:
            messagebox.showwarning("警告", "请先选择要运行的脚本")
            return
        
        try:
            # 获取对应的运行器
            widgets = self.config_widgets[current_type]
            info = self.script_types[current_type]

            # 运行时脚本信息（避免在未勾选“保存”为默认设置时修改配置）
            script_to_run = dict(script)

            # Python 环境下拉框：用于本次运行（勾选保存时才落盘）
            selected_env = ""
            if current_type == "python" and "env_combo" in widgets:
                selected_env = widgets["env_combo"].get().strip()
                if selected_env:
                    script_to_run["env"] = selected_env

            runner_class = RunnerFactory.get_runner(script_to_run.get("script_type", "python"))
            runner = runner_class(script_to_run, self.config)
            
            # 准备参数
            arguments = ""
            working_dir = os.path.dirname(script["path"])
            
            # 只有当脚本类型支持这些功能时才获取相应的值
            if info["supports_output"] or info["supports_interactive"]:
                if "args_entry" in widgets:
                    arguments = widgets['args_entry'].get().strip()
                if "dir_entry" in widgets:
                    working_dir = widgets['dir_entry'].get().strip() or working_dir
            
            # 获取显示输出设置
            show_output = False
            if info["supports_output"] and "show_output_var" in widgets:
                show_output = widgets['show_output_var'].get()

            # 获取交互模式设置
            interactive = False
            if info["supports_interactive"] and "interactive_var" in widgets:
                interactive = widgets["interactive_var"].get()

            if interactive and not show_output:
                show_output = True
                if "show_output_var" in widgets:
                    widgets["show_output_var"].set(True)

            # 交互模式下可选择：捕获输出（内置交互窗口）或终端输出
            capture_output = True
            if info["supports_interactive"] and "capture_output_var" in widgets:
                capture_output = widgets['capture_output_var'].get()
            
            # 如果选择保存设置且脚本类型支持这些功能
            if hasattr(self, 'save_var') and self.save_var.get():
                save_data = {}
                if selected_env and selected_env != script.get("env"):
                    save_data["env"] = selected_env
                if info["supports_output"] or info["supports_interactive"]:
                    if arguments:
                        save_data["arguments"] = arguments
                    if working_dir != os.path.dirname(script["path"]):
                        save_data["working_dir"] = working_dir
                
                if info["supports_output"]:
                    save_data["show_output"] = show_output

                if info["supports_interactive"] and "interactive_var" in widgets:
                    save_data["interactive"] = interactive
                    if "capture_output_var" in widgets:
                        save_data["capture_output"] = widgets['capture_output_var'].get()
                
                if save_data:
                    script.update(save_data)
                    self.config_manager.save_config()
            
            # 运行脚本
            process = runner.run(
                arguments=arguments,
                working_dir=working_dir,
                show_output=show_output,
                interactive=interactive,
                capture_output=capture_output
            )

            # 显示输出时，非交互脚本始终使用内置窗口；
            # 交互脚本则根据“捕获输出”决定使用内置窗口还是系统终端。
            use_internal_window = show_output and (not interactive or capture_output)
            if use_internal_window:
                output_window = OutputWindow(
                    self.root,
                    script_to_run.get("name", ""),
                    interactive
                )
                output_window.display_output(process)
        
        except Exception as e:
            messagebox.showerror("错误", f"运行脚本时出错: {str(e)}")
    
    def edit_script_config(self):
        """编辑脚本配置"""
        script, script_category, _ = self._get_selected_script()
        if not script:
            return

        dialog = ScriptConfigDialog(
            self.root,
            self.config.get("python_environments", []),
            name=script.get("name", ""),
            path=script.get("path", ""),
            env=script.get("env", ""),
            description=script.get("description", ""),
            category=script_category,
            categories=(self.config.get("scripts", {}) or {}).keys(),
            script_type=script.get("script_type", "python"),
        )

        if not dialog.result:
            return

        # 分类可能是用户手动输入的，确保存在
        new_category = dialog.category or script_category
        if new_category not in (self.config.get("scripts", {}) or {}):
            self.config.setdefault("scripts", {})[new_category] = []
            # 若用户没有显式排序，新增分类追加到末尾（"其他"永远最后）
            if new_category != "其他":
                order = self.config.setdefault("settings", {}).setdefault("category_order", [])
                if new_category not in order:
                    order.append(new_category)

        # 如果分类改变，需要移动脚本
        if new_category != script_category:
            try:
                self.config["scripts"][script_category].remove(script)
            except Exception:
                pass
            self.config["scripts"][new_category].append(script)
            script_category = new_category

        # 直接更新脚本信息
        new_type = getattr(dialog, "script_type", script.get("script_type", "python"))
        script.update(
            {
                "name": dialog.script_name,
                "script_type": new_type,
                "env": dialog.selected_env if new_type == "python" else "",
                "description": dialog.description,
                "category": new_category,
                "path": getattr(dialog, "path", script.get("path", "")),
            }
        )

        self.config_manager.save_config()
        self.update_script_list()
    
    def add_env(self):
        """添加新的Python环境"""
        python_path = filedialog.askopenfilename(
            title="选择Python解释器",
            filetypes=[("Python解释器", "python*.exe" if sys.platform == "win32" else "*")]
        )
        if python_path:
            dialog = EnvConfigDialog(self.root, python_path)
            if dialog.result:
                env_info = {
                    "name": dialog.env_name,
                    "path": python_path,
                    "description": dialog.description
                }
                self.config["python_environments"].append(env_info)
                self.config_manager.save_config()
                self.update_env_list()
    
    def remove_env(self):
        """删除选中的环境"""
        env_name = self._get_selected_env_name()
        if not env_name:
            return

        if messagebox.askyesno("确认", f"确定要删除环境 {env_name} 吗?"):
            # 找到并删除环境
            for i, env in enumerate(self.config.get("python_environments", []) or []):
                if env.get("name") == env_name:
                    del self.config["python_environments"][i]
                    self.config_manager.save_config()
                    self.update_env_list()
                    return

            messagebox.showwarning("提示", f"未找到名为 {env_name} 的环境")
    
    def test_env(self):
        """测试选中的Python环境"""
        env_name = self._get_selected_env_name()
        if not env_name:
            return

        # 找到对应的环境
        env = next(
            (
                env
                for env in (self.config.get("python_environments", []) or [])
                if env.get("name") == env_name
            ),
            None,
        )

        if not env:
            messagebox.showwarning("提示", f"未找到名为 {env_name} 的环境")
            return

        try:
            result = subprocess.run(
                [env.get("path", ""), "--version"],
                capture_output=True,
                text=True,
            )
            version = (result.stdout or result.stderr).strip()
            messagebox.showinfo("环境测试", f"环境正常\n{version}")
        except Exception as e:
            messagebox.showerror("错误", f"测试环境时出错: {str(e)}")
    
    def browse_dir(self):
        """选择工作目录"""
        dir_path = filedialog.askdirectory(title="选择工作目录")
        if dir_path:
            self.config_widgets[self.get_current_script_type()]['dir_entry'].delete(0, tk.END)
            self.config_widgets[self.get_current_script_type()]['dir_entry'].insert(0, dir_path)
    
    def handle_drop(self, event):
        """处理文件拖放"""
        files = self.root.tk.splitlist(event.data)
        # 将文件路径添加到参数中
        current_args = self.config_widgets[self.get_current_script_type()]['args_entry'].get().strip()
        file_paths = ' '.join(f'"{f}"' if ' ' in f else f for f in files)
        
        if current_args:
            self.config_widgets[self.get_current_script_type()]['args_entry'].delete(0, tk.END)
            self.config_widgets[self.get_current_script_type()]['args_entry'].insert(0, f"{current_args} {file_paths}")
        else:
            self.config_widgets[self.get_current_script_type()]['args_entry'].insert(0, file_paths)
    
    def create_env_page(self, parent):
        """创建Python环境管理页面"""
        # 创建容器框架
        container = ttk.Frame(parent)
        container.pack(fill='both', expand=True)
        
        # 创建树形视图
        self.env_tree = ttk.Treeview(container, selectmode='browse')
        
        # 创建滚动条
        y_scrollbar = ttk.Scrollbar(container, orient='vertical', command=self.env_tree.yview)
        x_scrollbar = ttk.Scrollbar(container, orient='horizontal', command=self.env_tree.xview)
        
        # 配置树形视图的滚动
        self.env_tree.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )
        
        # 配置列
        self.env_tree['columns'] = ('path', 'description')
        self.env_tree.column('#0', width=150)
        self.env_tree.column('path', width=250)
        self.env_tree.column('description', width=200)
        
        self.env_tree.heading('#0', text='名称')
        self.env_tree.heading('path', text='路径')
        self.env_tree.heading('description', text='描述')
        
        # 使用网格布局
        self.env_tree.grid(row=0, column=0, sticky='nsew')
        y_scrollbar.grid(row=0, column=1, sticky='ns')
        x_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # 配置网格权重
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # 按钮框
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text="添加环境", command=self.add_env).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除环境", command=self.remove_env).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="测试环境", command=self.test_env).pack(side=tk.LEFT, padx=2)
        
        # 更新环境列表
        self.update_env_list()
        
        # 创建右键菜单
        self.env_context_menu = tk.Menu(self.root, tearoff=0)
        self.env_context_menu.add_command(label="测试环境", command=self.test_env)
        self.env_context_menu.add_command(label="删除环境", command=self.remove_env)
        
        # 绑定右键菜单
        self.env_tree.bind('<Button-3>', self.show_env_context_menu)
    
    def update_env_list(self):
        """更新环境列表"""
        env_names = [e.get("name") for e in (self.config.get("python_environments", []) or []) if e.get("name")]

        # 1) 如果存在环境列表（env_tree），同步刷新
        if hasattr(self, "env_tree"):
            try:
                self.env_tree.delete(*self.env_tree.get_children())
                for env in self.config.get("python_environments", []) or []:
                    self.env_tree.insert(
                        "",
                        "end",
                        text=env.get("name", ""),
                        values=(env.get("path", ""), env.get("description", "")),
                    )
            except Exception:
                # env_tree 不是强依赖，忽略刷新失败
                pass

        # 2) 更新右侧运行配置面板中的 Python 环境下拉框
        python_widgets = self.config_widgets.get("python", {})
        env_combo = python_widgets.get("env_combo")
        if env_combo is not None:
            env_combo["values"] = env_names
    
    def show_env_context_menu(self, event):
        """显示环境右键菜单"""
        item = self.env_tree.identify_row(event.y)
        if item:
            self.env_tree.selection_set(item)
            self.env_context_menu.post(event.x_root, event.y_root)
    
    def edit_categories(self):
        """编辑脚本分类"""
        dialog = CategoryDialog(
            self.root, 
            self.config["scripts"].keys(),
            self.config["settings"].get("category_order", [])
        )
        if dialog.result:
            # 获取新的分类列表
            old_categories = set(self.config["scripts"].keys())
            new_categories = set(dialog.categories)
            
            # 处理删除的分类
            for category in old_categories - new_categories:
                # 将该分类下的脚本移动到"其他"分类
                if category != "其他":  # 不允许删除"其他"分类
                    scripts = self.config["scripts"].pop(category)
                    self.config["scripts"]["其他"].extend(scripts)
            
            # 处理新增的分类
            for category in new_categories - old_categories:
                self.config["scripts"][category] = []
            
            # 保存分类顺序
            self.config["settings"]["category_order"] = dialog.category_order
            
            # 保存配置
            self.config_manager.save_config()
            # 更新显示
            self.update_script_list()
    
    def open_script_location(self):
        """打开选中脚本所在的文件夹，并尽量选中脚本文件"""
        script, _, _ = self._get_selected_script()
        if not script or "path" not in script:
            return

        try:
            script_path = Path(script["path"])
            if not script_path.exists():
                messagebox.showerror("错误", "脚本文件不存在")
                return

            script_dir = script_path.parent
            if not script_dir.exists():
                messagebox.showerror("错误", "脚本所在目录不存在")
                return

            if sys.platform == "win32":
                # Windows Explorer 支持 /select, 参数，打开父目录并选中文件
                subprocess.run(["explorer", f"/select,{script_path}"])
            elif sys.platform == "darwin":  # macOS
                # Finder 的 -R 参数会 reveal 文件，即打开父目录并选中文件
                subprocess.run(["open", "-R", str(script_path)])
            else:  # Linux
                # freedesktop FileManager1 接口支持 ShowItems，常见文件管理器可据此选中文件
                try:
                    subprocess.run([
                        "dbus-send",
                        "--session",
                        "--dest=org.freedesktop.FileManager1",
                        "--type=method_call",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:{script_path.resolve().as_uri()}",
                        "string:",
                    ], check=True)
                except Exception:
                    # 部分 Linux 文件管理器不支持选中文件，降级为打开所在目录
                    subprocess.run(["xdg-open", str(script_dir)])
        except Exception as e:
            messagebox.showerror("错误", f"打开目录失败: {str(e)}")

    def open_in_editor(self):
        """用编辑器打开选中脚本"""
        script, _, _ = self._get_selected_script()
        if not script or "path" not in script:
            return

        try:
            script_path = Path(script["path"])
            if not script_path.exists():
                messagebox.showerror("错误", "脚本文件不存在")
                return

            # 优先使用 PATH 中的 `code` 命令
            tried_paths = []
            code_cmd = shutil.which("code")
            if code_cmd:
                subprocess.run([code_cmd, str(script_path)])
                return

            # 常见的 VSCode 可执行文件路径回退（Windows）
            if sys.platform == "win32":
                candidate_paths = [
                    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
                    Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code" / "Code.exe",
                    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft VS Code" / "Code.exe",
                ]

                for p in candidate_paths:
                    tried_paths.append(str(p))
                    if p.exists():
                        subprocess.run([str(p), str(script_path)])
                        return

            # 作为回退，尝试用系统默认程序打开该文件
            if sys.platform == "win32":
                try:
                    os.startfile(script_path)
                    return
                except Exception:
                    pass
            elif sys.platform == "darwin":
                subprocess.run(["open", str(script_path)])
                return
            else:
                subprocess.run(["xdg-open", str(script_path)])
                return

            # 如果都失败，给出更友好的提示并列出尝试过的路径
            message = (
                "无法找到 VSCode 的命令行工具 `code` 或可执行文件。\n"
                "请确保已在 PATH 中安装 `code`（在 VSCode 命令面板中运行 'Shell Command: Install \'code\' command in PATH'），\n"
                "或者将 VSCode 可执行文件添加到 PATH，或手动在系统中打开文件。\n\n"
                f"已尝试路径:\n{chr(10).join(tried_paths)}"
            )
            messagebox.showerror("错误", message)
        except Exception as e:
            messagebox.showerror("错误", f"打开编辑器失败: {str(e)}")

    def update_run_option_states(self, script_type=None):
        """根据当前勾选状态更新运行选项的可用性。"""
        script_type = script_type or self.get_current_script_type()
        widgets = self.config_widgets.get(script_type, {})

        show_output_var = widgets.get('show_output_var')
        interactive_var = widgets.get('interactive_var')
        interactive_check = widgets.get('interactive_check')
        capture_output_check = widgets.get('capture_output_check')

        show_output = show_output_var.get() if show_output_var is not None else False

        if interactive_var is not None and not show_output:
            interactive_var.set(False)

        if interactive_check is not None:
            if show_output:
                interactive_check.state(['!disabled'])
            else:
                interactive_check.state(['disabled'])

        interactive_enabled = interactive_var.get() if interactive_var is not None else False
        if capture_output_check is not None:
            if show_output and interactive_enabled:
                capture_output_check.state(['!disabled'])
            else:
                capture_output_check.state(['disabled'])

    def on_show_output_changed(self, script_type=None):
        """处理“显示输出”复选框状态变化。"""
        self.update_run_option_states(script_type)

    def on_interactive_changed(self, script_type=None):
        """处理“交互模式”复选框状态变化。"""
        script_type = script_type or self.get_current_script_type()
        widgets = self.config_widgets.get(script_type, {})

        show_output_var = widgets.get('show_output_var')
        interactive_var = widgets.get('interactive_var')

        if show_output_var is None or interactive_var is None:
            return

        if interactive_var.get() and not show_output_var.get():
            show_output_var.set(True)

        self.update_run_option_states(script_type)

    def on_app_close(self):
        """窗口关闭时保存必要的界面状态。"""
        try:
            # Tk 的 geometry 形如 "1000x600+120+80"，这里只保存 WxH
            geom = self.root.geometry() or ""
            size = geom.split("+")[0] if "+" in geom else geom
            if size:
                self.config.setdefault("settings", {})["window_size"] = size
                self.config_manager.save_config()
        except Exception:
            # 关闭时不阻塞退出
            pass
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass
    
    def run(self):
        """运行主程序"""
        self.root.mainloop() 