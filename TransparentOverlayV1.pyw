import tkinter as tk
from tkinter import ttk
import json
import os
from pathlib import Path
import sys

# 程序中文名称
APP_NAME_CHINESE = "透明悬浮窗"
# 程序英文名称（用于文件夹和配置文件）
APP_NAME_ENGLISH = "TransparentOverlay"
# 程序版本
APP_VERSION = "V1"
# 程序最后修改时间
APP_MODIFIED_DATE = "2026-11-09"

# 获取用户配置文件夹路径
if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME_ENGLISH
else:
    CONFIG_DIR = Path.home() / '.config' / APP_NAME_ENGLISH

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "window_config.json"

# 右键菜单提供的透明度选项
ALPHA_CHOICES = (0.25, 0.5, 0.75, 0.9, 1.0)


class OverlayApp:
    def __init__(self):
        self.root = tk.Tk()

        # 启用HDPI支持
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # 设置tkinter缩放
        self.root.tk.call('tk', 'scaling', 1.5)  # 适配高DPI

        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)  # 默认置顶
        self.root.title(APP_NAME_CHINESE)  # 有标题才能从任务栏找到

        # 恢复位置、大小和透明度
        self.load_window_geometry()
        self.alpha_var = tk.DoubleVar(value=self.current_alpha)

        self._drag_origin = None
        self.root.config(cursor="hand2")
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.stop_drag)
        self.root.bind("<Button-3>", self.show_context_menu)  # 右键菜单
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)  # 点标题栏 X 也要保存

        # 创建右键菜单
        self.create_context_menu()

        self.root.mainloop()

    def load_window_geometry(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x, y, w, h, alpha = 100, 100, sw // 4, sh // 4, 0.9
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                x = int(data.get("x", x))
                y = int(data.get("y", y))
                w = int(data.get("width", w))
                h = int(data.get("height", h))
                alpha = float(data.get("alpha", alpha))
            except (OSError, ValueError, TypeError, AttributeError):
                x, y, w, h, alpha = 100, 100, sw // 4, sh // 4, 0.9
        # 换显示器或配置损坏时，别让窗口跑到屏幕外、缩成点或全透明
        x = min(max(x, 0), max(sw - 100, 0))
        y = min(max(y, 0), max(sh - 100, 0))
        w = max(w, 100)
        h = max(h, 100)
        alpha = min(max(alpha, 0.1), 1.0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.attributes('-alpha', alpha)
        self.current_alpha = alpha

    def save_window_geometry(self):
        if self.root.state() != "normal":
            return  # 最小化/最大化时不保存，避免记下无效坐标
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                "x": self.root.winfo_x(),
                "y": self.root.winfo_y(),
                "width": self.root.winfo_width(),
                "height": self.root.winfo_height(),
                "alpha": self.current_alpha,
            }, f)

    def start_drag(self, event):
        # 记录按下时的鼠标屏幕坐标和窗口位置
        self._drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def on_drag(self, event):
        if self._drag_origin is None:
            return
        start_x, start_y, win_x, win_y = self._drag_origin
        self.root.geometry(f"+{win_x + event.x_root - start_x}+{win_y + event.y_root - start_y}")

    def stop_drag(self, _):
        self._drag_origin = None

    def create_context_menu(self):
        menu_font = ("Microsoft YaHei UI", 16)
        bold_font = ("Microsoft YaHei UI", 16, "bold")

        self.context_menu = tk.Menu(self.root, tearoff=0, font=menu_font)

        # 第一组：透明度设置（选中态由 alpha_var 自动维护）
        self.context_menu.add_command(label=" 透明度", state="disabled", font=bold_font)
        self.context_menu.add_separator()
        for alpha in ALPHA_CHOICES:
            self.context_menu.add_radiobutton(
                label=f" {int(alpha * 100)}%", variable=self.alpha_var, value=alpha,
                command=self.apply_alpha, font=menu_font)

        # 第二组：信息
        self.context_menu.add_separator()
        self.context_menu.add_command(label=" 信息", state="disabled", font=bold_font)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  关于本程序", command=self.show_about)
        self.context_menu.add_command(label="  退出", command=self.quit_app)

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def apply_alpha(self):
        self.current_alpha = self.alpha_var.get()
        self.root.attributes('-alpha', self.current_alpha)

    def show_about(self):
        """显示关于窗口，居中于主窗口"""
        about_window = tk.Toplevel(self.root)
        about_window.title("关于 " + APP_NAME_CHINESE)
        about_window.resizable(False, False)
        about_window.geometry(
            f"400x200+{self.root.winfo_x() + (self.root.winfo_width() - 400) // 2}"
            f"+{self.root.winfo_y() + (self.root.winfo_height() - 200) // 2}")
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
        self.root.destroy()


if __name__ == "__main__":
    app = OverlayApp()
