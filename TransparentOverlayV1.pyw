import tkinter as tk
from tkinter import ttk
import json
import os
from pathlib import Path
import sys
import datetime

# 程序中文名称
APP_NAME_CHINESE = "透明悬浮窗"
# 程序英文名称（用于文件夹和配置文件）
APP_NAME_ENGLISH = "TransparentOverlay"
# 程序版本
APP_VERSION = "V1"
# 程序最后修改时间
APP_MODIFIED_DATE = "2025-06-17"

# 获取用户配置文件夹路径
if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME_ENGLISH
else:
    CONFIG_DIR = Path.home() / '.config' / APP_NAME_ENGLISH

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "window_config.json"

class OverlayApp:
    def __init__(self):
        self.root = tk.Tk()

        # 启用HDPI支持
        try:
            import ctypes
            # 设置DPI感知
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # 设置tkinter缩放
        self.root.tk.call('tk', 'scaling', 1.5)  # 适配高DPI

        # 修改：保持无边框但允许在任务栏显示
        # self.root.overrideredirect(True)  # 注释掉这行，让窗口在任务栏显示
        self.root.attributes('-toolwindow', 0)  # 确保在任务栏显示
        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)  # 默认置顶
        # 默认启动时透明度为90%
        self.root.attributes('-alpha', 0.9)
        self.current_alpha = 0.9  # 记录当前透明度

        # 设置窗口标题（虽然无边框，但有助于识别进程）
        self.root.title(APP_NAME_CHINESE)

        # 加载窗口配置
        self.load_window_geometry()

        # 添加拖拽偏移量记录（使用屏幕绝对坐标）
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.window_start_x = 0
        self.window_start_y = 0
        self.window_start_w = 0
        self.window_start_h = 0

        self.dragging = None
        self.resize_zone = 10
        self.setup_bindings()

        # 创建右键菜单
        self.create_context_menu()

        self.root.mainloop()

    def load_window_geometry(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        default_width = screen_width // 4
        default_height = screen_height // 4

        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    x = data.get("x", 100)
                    y = data.get("y", 100)
                    w = data.get("width", default_width)
                    h = data.get("height", default_height)
                    self.root.geometry(f"{w}x{h}+{x}+{y}")
            except:
                self.root.geometry(f"{default_width}x{default_height}+100+100")
        else:
            self.root.geometry(f"{default_width}x{default_height}+100+100")

    def save_window_geometry(self):
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                "x": x,
                "y": y,
                "width": w,
                "height": h
            }, f)

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.root.winfo_screenheight() // 2) - (200 // 2)
        self.root.geometry(f"300x200+{x}+{y}")

    def setup_bindings(self):
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.stop_drag)
        self.root.bind("<Motion>", self.update_cursor)
        self.root.bind("<Button-3>", self.show_context_menu)  # 右键菜单

    def create_context_menu(self):
        menu_font = ("Microsoft YaHei UI", 16)
        bold_font = ("Microsoft YaHei UI", 16, "bold")

        self.context_menu = tk.Menu(self.root, tearoff=0, font=menu_font)
        
        # 第一组：透明度设置
        self.context_menu.add_command(label=" 透明度", state="disabled", font=bold_font)
        self.context_menu.add_separator()
        
        # 透明度选项，向右移动一个字符
        self.context_menu.add_command(label="  25%  ", command=lambda: self.set_alpha_cmd(0.25))
        self.context_menu.add_command(label="  50%  ", command=lambda: self.set_alpha_cmd(0.5))
        self.context_menu.add_command(label="  75%  ", command=lambda: self.set_alpha_cmd(0.75))
        self.context_menu.add_command(label="  90%  ", command=lambda: self.set_alpha_cmd(0.9))
        self.context_menu.add_command(label="  100% ", command=lambda: self.set_alpha_cmd(1.0))
        
        # 第二组：信息
        self.context_menu.add_separator()
        self.context_menu.add_command(label=" 信息", state="disabled", font=bold_font)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  关于本程序", command=self.show_about)
        self.context_menu.add_command(label="  退出", command=self.quit_app)

        # 更新菜单选中状态
        self.update_menu_checkmarks()

    def update_menu_checkmarks(self):
        """更新菜单中的选中状态标识"""
        # 添加当前透明度的加粗标识
        alpha_labels = {0.25: "25%", 0.5: "50%", 0.75: "75%", 0.9: "90%", 1.0: "100%"}
        menu_font = ("Microsoft YaHei UI", 16)
        bold_font = ("Microsoft YaHei UI", 16, "bold")
        
        # 遍历菜单项，找到透明度选项
        for i in range(self.context_menu.index('end') + 1):
            try:
                label = self.context_menu.entrycget(i, 'label').strip()
                if label in alpha_labels.values():
                    # 检查是否是当前透明度
                    if label == alpha_labels.get(self.current_alpha, ""):
                        self.context_menu.entryconfig(i, font=bold_font)
                    else:
                        self.context_menu.entryconfig(i, font=menu_font)
            except:
                pass

    def show_context_menu(self, event):
        self.update_menu_checkmarks()
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def get_cursor_direction(self, x, y):
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if x < self.resize_zone and y < self.resize_zone:
            return "nw"
        elif x > w - self.resize_zone and y < self.resize_zone:
            return "ne"
        elif x < self.resize_zone and y > h - self.resize_zone:
            return "sw"
        elif x > w - self.resize_zone and y > h - self.resize_zone:
            return "se"
        else:
            return "move"

    def update_cursor(self, event):
        direction = self.get_cursor_direction(event.x, event.y)
        if direction == "move":
            # 矩形区域（可移动区域）显示手掌图标
            self.root.config(cursor="hand2")
        else:
            # 调整大小区域显示相应的调整光标
            cursors = {"nw": "size_nw_se", "ne": "size_ne_sw", "sw": "size_ne_sw", "se": "size_nw_se"}
            self.root.config(cursor=cursors[direction])

    def start_drag(self, event):
        self.dragging = self.get_cursor_direction(event.x, event.y)

        # 记录所有必要的初始状态（使用屏幕绝对坐标）
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.window_start_x = self.root.winfo_x()
        self.window_start_y = self.root.winfo_y()
        self.window_start_w = self.root.winfo_width()
        self.window_start_h = self.root.winfo_height()

        # 设置拖拽时光标为手掌
        self.root.config(cursor="hand2")

    def on_drag(self, event):
        if not self.dragging:
            return

        # 计算鼠标在屏幕上的绝对位移
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y

        if self.dragging == "move":
            # 直接使用绝对位移计算新位置
            new_x = self.window_start_x + dx
            new_y = self.window_start_y + dy
            self.root.geometry(f"+{int(new_x)}+{int(new_y)}")

        elif self.dragging == "nw":
            # 西北角调整：同时改变位置和尺寸
            new_w = max(self.window_start_w - dx, 10)
            new_h = max(self.window_start_h - dy, 10)
            new_x = self.window_start_x + (self.window_start_w - new_w)
            new_y = self.window_start_y + (self.window_start_h - new_h)
            self.root.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{int(new_y)}")

        elif self.dragging == "ne":
            # 东北角调整：改变尺寸和Y位置
            new_w = max(self.window_start_w + dx, 10)
            new_h = max(self.window_start_h - dy, 10)
            new_y = self.window_start_y + (self.window_start_h - new_h)
            self.root.geometry(f"{int(new_w)}x{int(new_h)}+{self.window_start_x}+{int(new_y)}")

        elif self.dragging == "sw":
            # 西南角调整：改变尺寸和X位置
            new_w = max(self.window_start_w - dx, 10)
            new_h = max(self.window_start_h + dy, 10)
            new_x = self.window_start_x + (self.window_start_w - new_w)
            self.root.geometry(f"{int(new_w)}x{int(new_h)}+{int(new_x)}+{self.window_start_y}")

        elif self.dragging == "se":
            # 东南角调整：只改变尺寸
            new_w = max(self.window_start_w + dx, 10)
            new_h = max(self.window_start_h + dy, 10)
            self.root.geometry(f"{int(new_w)}x{int(new_h)}+{self.window_start_x}+{self.window_start_y}")

    def stop_drag(self, _):
        self.dragging = None
        # 恢复光标为默认（根据当前位置重新判断）
        self.update_cursor(tk.Event())

    def set_alpha_cmd(self, alpha):
        """设置透明度并更新菜单状态"""
        self.current_alpha = alpha
        self.set_alpha(alpha)
        self.update_menu_checkmarks()

    def set_alpha(self, alpha):
        self.root.attributes('-alpha', alpha)

    def show_about(self):
        """显示关于窗口"""
        about_window = tk.Toplevel(self.root)
        about_window.title("关于 " + APP_NAME_CHINESE)
        about_window.geometry("400x200")
        about_window.resizable(False, False)
        
        # 确保窗口在父窗口中心
        about_window.transient(self.root)
        about_window.grab_set()
        
        # 创建内容
        frame = ttk.Frame(about_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(frame, text=APP_NAME_CHINESE, font=("Microsoft YaHei UI", 16, "bold"))
        title_label.pack(pady=10)
        
        version_label = ttk.Label(frame, text=f"版本: {APP_VERSION}")
        version_label.pack(pady=5)
        
        modified_label = ttk.Label(frame, text=f"最后修改时间: {APP_MODIFIED_DATE}")
        modified_label.pack(pady=5)
        
        # 确定按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ok_button = ttk.Button(button_frame, text="确定", command=about_window.destroy)
        ok_button.pack()

    def quit_app(self):
        self.save_window_geometry()
        self.root.quit()

if __name__ == "__main__":
    app = OverlayApp()