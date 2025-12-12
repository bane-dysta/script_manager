import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
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
        self.root.geometry("750x500")
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
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
        env_menu.add_command(label="编辑环境", command=self.edit_env)
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
        
        for script_type, info in self.script_types.items():
            page = ttk.Frame(self.script_notebook)
            self.script_notebook.add(page, text=f"{info['icon']} {info['name']}")
            self.script_pages[script_type] = page
            
            # 创建树形视图
            tree = self.create_script_tree(page, script_type)
            self.script_trees[script_type] = tree
            
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
                # 获取环境名称列表
                env_names = [env["name"] for env in self.config["python_environments"]]
                widgets['env_combo'] = ttk.Combobox(env_frame, state='readonly', values=env_names)
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
                    ttk.Checkbutton(opt_frame, text="显示输出",
                                  variable=widgets['show_output_var']).pack(side=tk.LEFT)
                
                if info["supports_interactive"]:
                    widgets['interactive_var'] = tk.BooleanVar(value=False)
                    ttk.Checkbutton(opt_frame, text="交互模式",
                                  variable=widgets['interactive_var']).pack(side=tk.LEFT, padx=10)
                
                # 添加保存设置复选框
                ttk.Checkbutton(opt_frame, text="保存为默认设置",
                              variable=self.save_var).pack(side=tk.LEFT, padx=10)
            
            # 运行按钮
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill='x', padx=5, pady=5)
            ttk.Button(btn_frame, text="运行脚本",
                      command=self.run_script).pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="打开所在文件夹",
                      command=self.open_script_location).pack(side=tk.LEFT)
        
        # 默认显示Python配置
        self.show_config_frame("python")
        
        # 初始化时更新环境列表
        self.update_run_config_env_list()
    
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
        
        # 获取当前类型的脚本
        for category in self.config["scripts"]:
            scripts = [s for s in self.config["scripts"][category] 
                      if s.get("script_type") == current_type]
            
            if scripts:
                category_node = tree.insert("", "end", text=category, open=True)
                for script in scripts:
                    if filter_text and filter_text not in script["name"].lower():
                        continue
                    
                    values = [script.get("description", "")]
                    if current_type == "python":
                        values.insert(0, script.get("env", ""))
                    
                    tree.insert(
                        category_node,
                        "end",
                        text=script["name"],
                        values=tuple(values)
                    )
    
    def get_current_script_type(self):
        """获取当前选中的脚本类型"""
        current = self.script_notebook.select()
        tab_text = self.script_notebook.tab(current)["text"]
        
        # 从显示名称映射回类型键值
        for type_key, info in self.script_types.items():
            if info['name'] in tab_text:  # 使用 in 因为tab_text包含图标
                return type_key
        
        return "python"  # 默认返回python类型
    
    def on_script_select(self, event, script_type):
        """处理脚本选择事件"""
        tree = event.widget
        selection = tree.selection()
        if not selection:
            return
        
        item = selection[0]
        parent = tree.parent(item)
        
        # 如果选中的是分类节点，则返回
        if not parent:
            return
        
        # 获取脚本信息
        script_name = tree.item(item)["text"]
        category = tree.item(parent)["text"]
        
        script = next((s for s in self.config["scripts"][category] 
                      if s["name"] == script_name), None)
        
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
            if "interactive_var" in widgets:
                widgets['interactive_var'].set(script.get("interactive", False))
            if "show_output_var" in widgets:
                widgets['show_output_var'].set(script.get("show_output", True))
    
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
            
            # 弹出配置对话框
            dialog = ScriptConfigDialog(
                self.root, 
                self.config["python_environments"],
                categories=self.config["scripts"].keys(),
                script_type=script_type
            )
            
            if dialog.result:
                script_info = {
                    "name": dialog.script_name,
                    "path": file_path,
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
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        selection = tree.selection()
        if selection:
            item = selection[0]
            parent = tree.parent(item)
            
            # 如果选中的是分类节点，则返回
            if not parent:
                return
            
            # 获取脚本名称（去除缩进）
            script_name = tree.item(item)["text"]
            
            if messagebox.askyesno("确认", f"确定要删除脚本 {script_name} 吗?"):
                # 在所有分类中查找并删除脚本
                for category in self.config["scripts"]:
                    scripts = self.config["scripts"][category]
                    for i, script in enumerate(scripts):
                        if script["name"] == script_name:
                            del scripts[i]
                            self.config_manager.save_config()
                            self.update_script_list()
                            return
    
    def run_script(self):
        """运行选中的脚本"""
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要运行的脚本")
            return
        
        item = selection[0]
        parent = tree.parent(item)
        
        if not parent:  # 如果选中的是分类节点
            return
        
        script_name = tree.item(item)["text"]
        
        # 在所有分类中查找脚本
        script = None
        for category in self.config["scripts"].values():
            for s in category:
                if s["name"] == script_name:
                    script = s
                    break
            if script:
                break
        
        if not script:
            return
        
        try:
            # 获取当前类型的控件
            widgets = self.config_widgets[current_type]
            info = self.script_types[current_type]
            
            # 创建脚本信息的副本用于运行（避免修改原始配置）
            script_for_run = script.copy()
            
            # 如果是Python脚本，从运行配置面板获取选择的环境
            selected_env = None  # 用于保存设置，只有用户明确选择时才设置
            if current_type == "python" and "env_combo" in widgets:
                env_value = widgets['env_combo'].get().strip()
                # 如果下拉框有选择值，使用选择的环境
                if env_value:
                    script_for_run["env"] = env_value
                    selected_env = env_value  # 用于保存设置
                # 如果下拉框为空，使用脚本配置中的默认环境（但不保存）
                elif script.get("env"):
                    script_for_run["env"] = script.get("env")
            
            # 获取对应的运行器
            runner_class = RunnerFactory.get_runner(script_for_run.get("script_type", "python"))
            runner = runner_class(script_for_run, self.config)
            
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
            
            # 如果选择保存设置且脚本类型支持这些功能
            if hasattr(self, 'save_var') and self.save_var.get():
                save_data = {}
                
                # 如果是Python脚本且选择了环境，保存环境设置
                if current_type == "python" and selected_env:
                    save_data["env"] = selected_env
                
                if info["supports_output"] or info["supports_interactive"]:
                    if arguments:
                        save_data["arguments"] = arguments
                    if working_dir != os.path.dirname(script["path"]):
                        save_data["working_dir"] = working_dir
                
                if info["supports_output"]:
                    save_data["show_output"] = show_output
                
                if info["supports_interactive"] and "interactive_var" in widgets:
                    save_data["interactive"] = widgets['interactive_var'].get()
                
                if save_data:
                    script.update(save_data)
                    self.config_manager.save_config()
            
            # 运行脚本
            process = runner.run(
                arguments=arguments,
                working_dir=working_dir,
                show_output=show_output,  # 使用实际的复选框状态
                interactive=info["supports_interactive"] and widgets.get('interactive_var', tk.BooleanVar(value=False)).get()
            )
            
            # 只在需要时创建输出窗口
            if show_output:
                output_window = OutputWindow(
                    self.root, 
                    script["name"],
                    info["supports_interactive"] and widgets['interactive_var'].get()
                )
                output_window.display_output(process)
        
        except Exception as e:
            messagebox.showerror("错误", f"运行脚本时出错: {str(e)}")
    
    def edit_script_config(self):
        """编辑脚本配置"""
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        selection = tree.selection()
        if selection:
            item = selection[0]
            parent = tree.parent(item)
            
            # 如果选中的是分类节点，则返回
            if not parent:
                return
            
            # 获取脚本名称（去除缩进）
            script_name = tree.item(item)["text"]
            
            # 在所有分类中查找脚本
            script = None
            script_category = None
            for category, scripts in self.config["scripts"].items():
                for s in scripts:
                    if s["name"] == script_name:
                        script = s
                        script_category = category
                        break
                if script:
                    break
                
            if not script:
                return
            
            dialog = ScriptConfigDialog(
                self.root,
                self.config["python_environments"],
                script["name"],
                script.get("env", ""),
                script.get("description", ""),
                script_category,
                categories=self.config["scripts"].keys(),  # 传入当前分类列表
                script_type=script.get("script_type", "python")  # 传入脚本类型
            )
            
            if dialog.result:
                # 如果分类改变，需要移动脚本
                if dialog.category != script_category:
                    # 从原分类中删除
                    self.config["scripts"][script_category].remove(script)
                    # 更新脚本信息
                    script.update({
                        "name": dialog.script_name,
                        "env": dialog.selected_env,
                        "description": dialog.description,
                        "category": dialog.category
                    })
                    # 添加到新分类
                    self.config["scripts"][dialog.category].append(script)
                else:
                    # 直接更新脚本信息
                    script.update({
                        "name": dialog.script_name,
                        "env": dialog.selected_env,
                        "description": dialog.description
                    })
                
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
                # 更新环境列表（如果存在）
                if hasattr(self, 'env_tree'):
                    self.update_env_list()
                # 更新运行配置面板中的下拉框
                self.update_run_config_env_list()
    
    def edit_env(self):
        """编辑选中的环境"""
        # 如果没有环境，提示用户
        if not self.config["python_environments"]:
            messagebox.showinfo("提示", "没有可编辑的环境")
            return
        
        # 创建环境选择对话框
        env_names = [env["name"] for env in self.config["python_environments"]]
        selected_env_name = self._select_env_dialog("选择要编辑的环境", env_names)
        
        if selected_env_name:
            # 找到对应的环境
            env = next((env for env in self.config["python_environments"] 
                       if env["name"] == selected_env_name), None)
            
            if env:
                # 打开编辑对话框，传入现有的名称和描述
                dialog = EnvConfigDialog(
                    self.root, 
                    env["path"], 
                    env_name=env["name"],
                    description=env.get("description", "")
                )
                if dialog.result:
                    # 更新环境信息
                    env["name"] = dialog.env_name
                    env["description"] = dialog.description
                    # 如果路径改变了，也更新路径
                    # 注意：EnvConfigDialog 目前不支持编辑路径，如果需要可以扩展
                    
                    self.config_manager.save_config()
                    # 更新环境列表（如果存在）
                    if hasattr(self, 'env_tree'):
                        self.update_env_list()
                    # 更新运行配置面板中的下拉框
                    self.update_run_config_env_list()
                    messagebox.showinfo("成功", f"已更新环境 {dialog.env_name}")
    
    def remove_env(self):
        """删除选中的环境"""
        # 如果没有环境，提示用户
        if not self.config["python_environments"]:
            messagebox.showinfo("提示", "没有可删除的环境")
            return
        
        # 创建环境选择对话框
        env_names = [env["name"] for env in self.config["python_environments"]]
        selected_env = self._select_env_dialog("选择要删除的环境", env_names)
        
        if selected_env:
            if messagebox.askyesno("确认", f"确定要删除环境 {selected_env} 吗?"):
                # 找到并删除环境
                for i, env in enumerate(self.config["python_environments"]):
                    if env["name"] == selected_env:
                        del self.config["python_environments"][i]
                        self.config_manager.save_config()
                        # 更新环境列表（如果存在）
                        if hasattr(self, 'env_tree'):
                            self.update_env_list()
                        # 更新运行配置面板中的下拉框
                        self.update_run_config_env_list()
                        messagebox.showinfo("成功", f"已删除环境 {selected_env}")
                        break
    
    def test_env(self):
        """测试选中的Python环境"""
        # 如果没有环境，提示用户
        if not self.config["python_environments"]:
            messagebox.showinfo("提示", "没有可测试的环境")
            return
        
        # 创建环境选择对话框
        env_names = [env["name"] for env in self.config["python_environments"]]
        selected_env = self._select_env_dialog("选择要测试的环境", env_names)
        
        if selected_env:
            # 找到对应的环境
            env = next((env for env in self.config["python_environments"] 
                       if env["name"] == selected_env), None)
            
            if env:
                try:
                    result = subprocess.run(
                        [env["path"], "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    messagebox.showinfo("环境测试", f"环境正常\n{result.stdout}")
                except subprocess.TimeoutExpired:
                    messagebox.showerror("错误", "测试超时")
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
        if hasattr(self, 'env_tree'):
            self.env_tree.delete(*self.env_tree.get_children())
            
            # 更新环境下拉框的值
            env_names = []
            
            for env in self.config["python_environments"]:
                self.env_tree.insert(
                    "", 
                    "end",
                    text=env["name"],
                    values=(env["path"], env.get("description", ""))
                )
                env_names.append(env["name"])
        
        # 更新运行配置面板中的环境选择下拉框
        self.update_run_config_env_list()
    
    def update_run_config_env_list(self):
        """更新运行配置面板中的环境下拉框"""
        # 获取环境名称列表
        env_names = [env["name"] for env in self.config["python_environments"]]
        
        # 更新所有脚本类型的下拉框
        for script_type, widgets in self.config_widgets.items():
            if "env_combo" in widgets:
                widgets['env_combo']['values'] = env_names
    
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
        """打开选中脚本所在的文件夹"""
        current_type = self.get_current_script_type()
        tree = self.script_trees[current_type]
        selection = tree.selection()
        if not selection:
            return
        
        item = selection[0]
        parent = tree.parent(item)
        
        # 如果选中的是分类节点，则返回
        if not parent:
            return
        
        # 获取脚本名称
        script_name = tree.item(item)["text"]
        
        # 在所有分类中查找脚本
        script = None
        for category in self.config["scripts"].values():
            for s in category:
                if s["name"] == script_name:
                    script = s
                    break
            if script:
                break
            
        if script and "path" in script:
            try:
                script_dir = Path(script["path"]).parent
                if not script_dir.exists():
                    messagebox.showerror("错误", "脚本所在目录不存在")
                    return
                
                if sys.platform == "win32":
                    os.startfile(script_dir)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", script_dir])
                else:  # Linux
                    subprocess.run(["xdg-open", script_dir])
            except Exception as e:
                messagebox.showerror("错误", f"打开目录失败: {str(e)}")
    
    def on_show_output_changed(self):
        """处理显示输出复选框状态变化"""
        if not self.show_output_var.get():
            self.interactive_var.set(False)  # 如果取消显示输出,则自动取消交互模式

    def on_interactive_changed(self):
        """处理交互模式复选框状态变化"""
        if self.interactive_var.get():
            self.show_output_var.set(True)  # 如果选择交互模式,则自动勾选显示输出
    
    def _select_env_dialog(self, title, env_names):
        """创建环境选择对话框"""
        if not env_names:
            return None
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = [None]  # 使用列表以便在嵌套函数中修改
        
        # 标签
        ttk.Label(dialog, text="请选择环境:").pack(pady=10)
        
        # 创建列表框
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        
        for env_name in env_names:
            listbox.insert(tk.END, env_name)
        
        listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # 默认选择第一项
        if env_names:
            listbox.selection_set(0)
            listbox.see(0)
        
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        def ok():
            selection = listbox.curselection()
            if selection:
                result[0] = listbox.get(selection[0])
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="确定", command=ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=cancel).pack(side=tk.RIGHT)
        
        # 绑定双击事件
        listbox.bind('<Double-1>', lambda e: ok())
        
        # 绑定回车键
        dialog.bind('<Return>', lambda e: ok())
        dialog.bind('<Escape>', lambda e: cancel())
        
        dialog.focus_set()
        dialog.wait_window()
        
        return result[0]
    
    def run(self):
        """运行主程序"""
        self.root.mainloop() 