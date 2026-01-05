import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from tkinter import messagebox
import threading
import queue
from pathlib import Path

class ScriptConfigDialog:
    """脚本配置对话框"""
    def __init__(self, parent, environments, name="", path="", env="", description="", 
                 category="其他", categories=None, script_type="python"):
        self.result = False
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("脚本配置")
        self.dialog.geometry("400x400")  # 增加高度以容纳新控件
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 初始化变量
        self.env_var = tk.StringVar(value=env if env else "")
        self.path_var = tk.StringVar(value=path if path else "")
        self.category_var = tk.StringVar(value=category)
        self.script_type_var = tk.StringVar(value=script_type)
        
        # 名称
        ttk.Label(self.dialog, text="脚本名称:").pack(pady=5)
        self.name_entry = ttk.Entry(self.dialog)
        self.name_entry.pack(fill='x', padx=5)
        self.name_entry.insert(0, name)
        
        # 路径编辑（可选）
        ttk.Label(self.dialog, text="脚本路径:").pack(pady=5)
        path_frame = ttk.Frame(self.dialog)
        path_frame.pack(fill='x', padx=5)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Button(path_frame, text="浏览", command=self.browse_script_path).pack(side=tk.RIGHT, padx=(5,0))

        # 脚本类型选择
        ttk.Label(self.dialog, text="脚本类型:").pack(pady=5)
        self.script_type_combo = ttk.Combobox(
            self.dialog,
            textvariable=self.script_type_var,
            values=["python", "batch", "powershell", "executable"],
            state="readonly"
        )
        self.script_type_combo.pack(fill='x', padx=5)
        
        # 分类选择
        ttk.Label(self.dialog, text="分类:").pack(pady=5)
        self.category_combo = ttk.Combobox(
            self.dialog,
            textvariable=self.category_var,
            values=sorted(categories) if categories else ["其他"]
        )
        self.category_combo.pack(fill='x', padx=5)
        
        # Python环境选择(只在Python脚本类型时显示)
        self.env_frame = ttk.Frame(self.dialog)
        self.env_frame.pack(fill='x', padx=5)
        ttk.Label(self.env_frame, text="Python环境:").pack(pady=5)
        self.env_combo = ttk.Combobox(
            self.env_frame,
            textvariable=self.env_var,
            values=[e["name"] for e in environments]
        )
        self.env_combo.pack(fill='x')
        
        # 根据脚本类型显示/隐藏环境选择
        self.script_type_combo.bind('<<ComboboxSelected>>', self.on_type_changed)
        self.on_type_changed(None)  # 初始化显示状态
        
        # 描述
        ttk.Label(self.dialog, text="描述:").pack(pady=5)
        self.desc_text = tk.Text(self.dialog, height=5)
        self.desc_text.pack(fill='both', expand=True, padx=5)
        self.desc_text.insert('1.0', description)
        
        # 按钮
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="确定", command=self.ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        
        # 设置对话框为模态
        self.dialog.grab_set()
        self.dialog.focus_set()
        self.dialog.wait_window()
    
    def browse_script_path(self):
        """选择脚本文件路径（用于编辑时修改路径）"""
        file_path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[
                ("所有支持的文件", "*.py;*.bat;*.cmd;*.ps1;*.psm1;*.psd1;*.exe"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.path_var.set(file_path)

    def on_type_changed(self, event):
        """处理脚本类型变化"""
        if self.script_type_var.get() == "python":
            self.env_frame.pack(fill='x', padx=5)
        else:
            self.env_frame.pack_forget()
    
    def ok(self):
        """确认配置"""
        self.script_name = self.name_entry.get().strip()
        self.selected_env = self.env_var.get()
        self.path = self.path_var.get().strip()
        self.category = self.category_var.get()
        self.description = self.desc_text.get('1.0', tk.END).strip()
        self.script_type = self.script_type_var.get()
        
        if not self.script_name:
            messagebox.showerror("错误", "请填写脚本名称")
            return
        
        if self.script_type == "python" and not self.selected_env:
            messagebox.showerror("错误", "请选择Python环境")
            return
        
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """取消配置"""
        self.dialog.destroy()

class OutputWindow:
    """脚本输出窗口"""
    def __init__(self, parent, title, interactive=False):
        self.window = tk.Toplevel(parent)
        self.window.title(f"运行: {title}")
        self.window.geometry("400x500")
        
        # 创建输出文本框和滚动条的容器
        text_frame = ttk.Frame(self.window)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 创建输出文本框
        self.output_text = tk.Text(text_frame, wrap=tk.NONE)  # 改为 NONE 以支持水平滚动
        
        # 创建垂直滚动条
        y_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.output_text.yview)
        # 创建水平滚动条
        x_scrollbar = ttk.Scrollbar(text_frame, orient='horizontal', command=self.output_text.xview)
        
        # 配置文本框的滚动
        self.output_text.configure(
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set
        )
        
        # 使用网格布局来放置文本框和滚动条
        self.output_text.grid(row=0, column=0, sticky='nsew')
        y_scrollbar.grid(row=0, column=1, sticky='ns')
        x_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # 配置网格权重，使文本框可以扩展
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # 如果是交互模式，添加输入区域
        if interactive:
            input_frame = ttk.Frame(self.window)
            input_frame.pack(fill='x', padx=5, pady=5)
            
            self.input_entry = ttk.Entry(input_frame)
            self.input_entry.pack(side=tk.LEFT, fill='x', expand=True)
            
            ttk.Button(input_frame, text="发送", command=self.send_input).pack(side=tk.RIGHT, padx=5)
            self.input_entry.bind('<Return>', lambda e: self.send_input())
        
        # 添加状态和关闭按钮
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        self.status_label = ttk.Label(btn_frame, text="运行中...")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.close_button = ttk.Button(btn_frame, text="关闭", state='disabled', command=self.window.destroy)
        self.close_button.pack(side=tk.RIGHT, padx=5)
        
        # 配置错误文本样式
        self.output_text.tag_configure('error', foreground='red')
        
        # 初始化进程变量和队列
        self.process = None
        self.output_queue = queue.Queue()
        self.error_queue = queue.Queue()
        
        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 标记进程是否应该继续运行
        self.running = True
    
    def send_input(self):
        """发送输入到脚本"""
        if self.process and self.process.poll() is None:
            input_text = self.input_entry.get() + '\n'
            try:
                self.process.stdin.write(input_text)
                self.process.stdin.flush()
                self.input_entry.delete(0, tk.END)
                # 显示输入内容
                self.output_text.insert(tk.END, f"> {input_text}")
                self.output_text.see(tk.END)
            except:
                # 如果写入失败，可能是进程已经结束
                pass
    
    def display_output(self, process):
        """显示脚本输出"""
        self.process = process
        
        # 创建读取输出的线程
        stdout_thread = threading.Thread(target=self.read_output, args=(process.stdout, self.output_queue))
        stderr_thread = threading.Thread(target=self.read_output, args=(process.stderr, self.error_queue))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # 启动更新输出的定时器
        self.update_output()
        
        # 启动进程监控
        self.window.after(100, self.check_process)
    
    def read_output(self, pipe, queue):
        """在线程中读取输出"""
        try:
            for line in iter(pipe.readline, ''):
                if not self.running:
                    break
                queue.put(line)
            pipe.close()
        except:
            pass
    
    def update_output(self):
        """更新输出显示"""
        # 处理标准输出
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.output_text.insert(tk.END, line)
                self.output_text.see(tk.END)
        except queue.Empty:
            pass
        
        # 处理错误输出
        try:
            while True:
                line = self.error_queue.get_nowait()
                self.output_text.insert(tk.END, line, 'error')
                self.output_text.see(tk.END)
        except queue.Empty:
            pass
        
        # 如果窗口还在运行，继续更新
        if self.running:
            self.window.after(100, self.update_output)
    
    def check_process(self):
        """检查进程状态"""
        if self.process.poll() is not None:
            # 进程已结束
            self.status_label.config(text="已完成")
            self.close_button.config(state='normal')
            self.running = False
            
            # 确保所有输出都被读取
            self.update_output()
            
            # 添加结束标记
            self.output_text.insert(tk.END, "\n--- 运行结束 ---\n")
            self.output_text.see(tk.END)
        elif self.running:
            # 继续检查
            self.window.after(100, self.check_process)
    
    def on_closing(self):
        """处理窗口关闭事件"""
        if self.process and self.process.poll() is None:
            if messagebox.askokcancel("确认", "脚本正在运行，确定要关闭窗口吗？"):
                self.running = False
                try:
                    self.process.terminate()
                except:
                    pass
                self.window.destroy()
        else:
            self.running = False
            self.window.destroy()

class EnvConfigDialog:
    """环境配置对话框"""
    def __init__(self, parent, python_path=None):
        self.result = False
        self.python_path = python_path
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("环境配置")
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 名称
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(name_frame, text="环境名称:").pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame)
        self.name_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=(5,0))
        
        # 路径显示
        path_frame = ttk.Frame(self.dialog)
        path_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(path_frame, text="解释器路径:").pack(side=tk.LEFT)
        self.path_label = ttk.Label(path_frame, text=python_path or "")
        self.path_label.pack(side=tk.LEFT, fill='x', expand=True, padx=(5,0))
        
        # 描述
        desc_frame = ttk.LabelFrame(self.dialog, text="环境描述")
        desc_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.desc_text = tk.Text(desc_frame, height=5, wrap=tk.WORD)
        self.desc_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 包列表
        packages_frame = ttk.LabelFrame(self.dialog, text="已安装的包")
        packages_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.packages_text = tk.Text(packages_frame, height=5, wrap=tk.WORD)
        self.packages_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 如果提供了 python_path，获取环境信息
        if python_path:
            self.load_env_info()
        
        # 按钮
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="确定", command=self.ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        
        self.dialog.wait_window()
    
    def load_env_info(self):
        """加载环境信息"""
        from src.utils import get_python_info
        info = get_python_info(self.python_path)
        
        # 设置默认名称
        if info["version"]:
            self.name_entry.insert(0, info["version"].replace("Python ", ""))
        
        # 显示包列表
        self.packages_text.insert('1.0', info["packages"])
        self.packages_text.config(state='disabled')
    
    def ok(self):
        """确认配置"""
        self.env_name = self.name_entry.get().strip()
        self.description = self.desc_text.get('1.0', tk.END).strip()
        
        if not self.env_name:
            messagebox.showerror("错误", "请填写环境名称")
            return
        
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """取消配置"""
        self.dialog.destroy()

class CategoryDialog:
    """分类编辑对话框"""
    def __init__(self, parent, current_categories, category_order=None):
        self.result = False
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑分类")
        self.dialog.geometry("300x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建列表框和滚动条
        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.listbox = tk.Listbox(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        
        self.listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        # 添加当前分类（除了"其他"）
        categories = list(current_categories)
        if "其他" in categories:
            categories.remove("其他")
        
        # 按照已有顺序排序
        if category_order:
            def get_category_order(cat):
                try:
                    return category_order.index(cat)
                except ValueError:
                    return len(category_order)
            categories.sort(key=get_category_order)
        
        for category in categories:
            self.listbox.insert(tk.END, category)
        
        # 按钮框
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="添加", command=self.add_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="编辑", command=self.edit_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="上移", command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="下移", command=self.move_down).pack(side=tk.LEFT, padx=2)
        
        # 确定取消按钮
        action_frame = ttk.Frame(self.dialog)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(action_frame, text="确定", command=self.ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        
        # 设置对话框为模态
        self.dialog.grab_set()
        self.dialog.focus_set()
        self.dialog.wait_window()
    
    def add_category(self):
        """添加新分类"""
        name = simpledialog.askstring("添加分类", "请输入分类名称:")
        if name:
            name = name.strip()
            if name and name != "其他":  # 不允许添加空分类和"其他"分类
                self.listbox.insert(tk.END, name)
    
    def edit_category(self):
        """编辑分类"""
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            old_name = self.listbox.get(idx)
            if old_name == "其他":  # 不允许编辑"其他"分类
                messagebox.showwarning("警告", '"其他"分类不能修改')
                return
            
            new_name = simpledialog.askstring("编辑分类", "请输入新的分类名称:", initialvalue=old_name)
            if new_name:
                new_name = new_name.strip()
                if new_name and new_name != "其他":
                    self.listbox.delete(idx)
                    self.listbox.insert(idx, new_name)
    
    def delete_category(self):
        """删除分类"""
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            name = self.listbox.get(idx)
            if name == "其他":  # 不允许删除"其他"分类
                messagebox.showwarning("警告", '"其他"分类不能删除')
                return
            
            if messagebox.askyesno("确认", f'确定要删除分类"{name}"吗？\n该分类下的脚本将移动到"其他"分类'):
                self.listbox.delete(idx)
    
    def move_up(self):
        """上移选中的分类"""
        selection = self.listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            text = self.listbox.get(idx)
            self.listbox.delete(idx)
            self.listbox.insert(idx-1, text)
            self.listbox.selection_set(idx-1)
    
    def move_down(self):
        """下移选中的分类"""
        selection = self.listbox.curselection()
        if selection and selection[0] < self.listbox.size()-1:
            idx = selection[0]
            text = self.listbox.get(idx)
            self.listbox.delete(idx)
            self.listbox.insert(idx+1, text)
            self.listbox.selection_set(idx+1)
    
    def ok(self):
        """确认修改"""
        categories = list(self.listbox.get(0, tk.END))
        # 添加"其他"分类到最后
        if "其他" not in categories:
            categories.append("其他")
        self.categories = categories
        # 保存分类顺序（不包括"其他"）
        self.category_order = categories[:-1] if categories[-1] == "其他" else categories
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """取消修改"""
        self.dialog.destroy()
