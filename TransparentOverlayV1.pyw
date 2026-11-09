import tkinter as tk
from tkinter import ttk
import ctypes
import json
import math
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

CONFIG_FILE = CONFIG_DIR / "window_config.json"

# 右键菜单提供的透明度选项
ALPHA_CHOICES = (0.25, 0.5, 0.75, 0.9, 1.0)

# 界面字体
UI_FONT = ("Microsoft YaHei UI", 16)
UI_FONT_BOLD = ("Microsoft YaHei UI", 16, "bold")


def desktop_bounds(screen_w, screen_h):
    """可完整容纳窗口外框的虚拟桌面范围 (left, top, right, bottom)；失败退回主屏"""
    try:
        metrics = ctypes.windll.user32.GetSystemMetrics
        left, top = metrics(76), metrics(77)
        width, height = metrics(78), metrics(79)
        if width > 0 and height > 0:
            border = metrics(32) + metrics(92)  # SM_CXSIZEFRAME + SM_CXPADDEDBORDER
            frame_w = 2 * border
            frame_h = metrics(4) + 2 * (metrics(33) + metrics(92))  # 标题栏 + 上下边框
            return left, top, left + width - frame_w, top + height - frame_h
    except (AttributeError, OSError):
        pass
    return 0, 0, screen_w, screen_h


def clamp_window_state(x, y, w, h, alpha, left, top, right, bottom):
    """把窗口状态限制在桌面内，尺寸和透明度保持在可用范围"""
    w = min(max(w, 100), right - left)
    h = min(max(h, 100), bottom - top)
    x = min(max(x, left), max(right - w, left))
    y = min(max(y, top), max(bottom - h, top))
    alpha = min(max(alpha, 0.1), 1.0)
    return x, y, w, h, alpha


def read_window_state(path, screen_w, screen_h, bounds=None):
    """读取配置；文件不存在、内容损坏或数值异常时回到默认值"""
    defaults = (100, 100, screen_w // 4, screen_h // 4, 0.9)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        state = (
            int(data.get("x", defaults[0])),
            int(data.get("y", defaults[1])),
            int(data.get("width", defaults[2])),
            int(data.get("height", defaults[3])),
            float(data.get("alpha", defaults[4])),
        )
        if not math.isfinite(state[4]):
            raise ValueError("alpha is not finite")
    except (OSError, ValueError, TypeError, AttributeError, OverflowError):
        state = defaults
    left, top, right, bottom = bounds or (0, 0, screen_w, screen_h)
    return clamp_window_state(*state, left, top, right, bottom)


def write_window_state(path, x, y, w, h, alpha):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "alpha": alpha,
    }), encoding="utf-8")
    os.replace(tmp, path)


def geometry_pos(x, y):
    """Tk 几何串的绝对坐标：负值必须写成 '+-1500'，'-1500' 会被当成距右边缘"""
    return f"+{x}+{y}"


def step_alpha(alpha, delta):
    """滚轮调整透明度，限制在 0.1–1.0"""
    return min(max(round(alpha + delta, 2), 0.1), 1.0)


def compute_ui_scale(screen_h, dpi):
    """以 1080p/96DPI 为基准，取分辨率与 DPI 中更大的缩放需求，小屏不缩小"""
    return max(1.0, screen_h / 1080, dpi / 96)


class OverlayApp:
    def __init__(self):
        # 启用HDPI支持（必须在创建窗口前设置）
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)  # 默认置顶
        self.root.title(APP_NAME_CHINESE)  # 有标题才能从任务栏找到

        # 按屏幕分辨率和 DPI 缩放界面
        self.ui_scale = compute_ui_scale(
            self.root.winfo_screenheight(), self.root.winfo_fpixels('1i'))
        self.root.tk.call('tk', 'scaling', (96 / 72) * self.ui_scale)

        # 恢复位置、大小和透明度
        self.load_window_geometry()
        self.alpha_var = tk.DoubleVar(value=self.current_alpha)

        self._drag_origin = None
        self.root.config(cursor="hand2")
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.stop_drag)
        self.root.bind("<Button-3>", self.show_context_menu)  # 右键菜单
        self.root.bind("<MouseWheel>", self.on_wheel)  # 滚轮调透明度
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)  # 点标题栏 X 也要保存

        # 创建右键菜单
        self.create_context_menu()

        self.root.mainloop()

    def load_window_geometry(self):
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y, w, h, alpha = read_window_state(
            CONFIG_FILE, screen_w, screen_h, desktop_bounds(screen_w, screen_h))
        self.root.geometry(f"{w}x{h}{geometry_pos(x, y)}")
        self.root.attributes('-alpha', alpha)
        self.current_alpha = alpha

    def save_window_geometry(self):
        if self.root.state() != "normal":
            return  # 最小化/最大化时不保存，避免记下无效坐标
        write_window_state(
            CONFIG_FILE, self.root.winfo_x(), self.root.winfo_y(),
            self.root.winfo_width(), self.root.winfo_height(), self.current_alpha)

    def start_drag(self, event):
        # 记录按下时的鼠标屏幕坐标和窗口位置
        self._drag_origin = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def on_drag(self, event):
        if self._drag_origin is None:
            return
        start_x, start_y, win_x, win_y = self._drag_origin
        x = win_x + event.x_root - start_x
        y = win_y + event.y_root - start_y
        self.root.geometry(geometry_pos(x, y))

    def stop_drag(self, _):
        self._drag_origin = None

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, font=UI_FONT)

        # 第一组：透明度设置（选中态由 alpha_var 自动维护）
        self.context_menu.add_command(label=" 透明度（滚轮可调）", state="disabled", font=UI_FONT_BOLD)
        self.context_menu.add_separator()
        for alpha in ALPHA_CHOICES:
            self.context_menu.add_radiobutton(
                label=f" {int(alpha * 100)}%", variable=self.alpha_var, value=alpha,
                command=self.apply_alpha, font=UI_FONT)

        # 第二组：信息
        self.context_menu.add_separator()
        self.context_menu.add_command(label=" 信息", state="disabled", font=UI_FONT_BOLD)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="  关于本程序", command=self.show_about)
        self.context_menu.add_command(label="  退出", command=self.quit_app)

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_wheel(self, event):
        """滚轮上/下调整透明度，5% 一档"""
        self.alpha_var.set(step_alpha(self.current_alpha, 0.05 if event.delta > 0 else -0.05))
        self.apply_alpha()

    def apply_alpha(self):
        self.current_alpha = self.alpha_var.get()
        self.root.attributes('-alpha', self.current_alpha)

    def show_about(self):
        """显示关于窗口，按内容定尺寸并居中于主窗口"""
        scale = self.ui_scale
        about_window = tk.Toplevel(self.root)
        about_window.withdraw()
        about_window.title("关于 " + APP_NAME_CHINESE)
        about_window.resizable(False, False)

        # 创建内容
        frame = ttk.Frame(about_window, padding=int(20 * scale))
        frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(frame, text=APP_NAME_CHINESE, font=UI_FONT_BOLD)
        title_label.pack(pady=int(10 * scale))

        version_label = ttk.Label(frame, text=f"版本: {APP_VERSION}")
        version_label.pack(pady=int(5 * scale))

        modified_label = ttk.Label(frame, text=f"最后修改时间: {APP_MODIFIED_DATE}")
        modified_label.pack(pady=int(5 * scale))

        # 确定按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=int(20 * scale))

        ok_button = ttk.Button(button_frame, text="确定", command=about_window.destroy)
        ok_button.pack()

        # 尺寸由内容决定，再居中到主窗口
        about_window.update_idletasks()
        w, h = about_window.winfo_reqwidth(), about_window.winfo_reqheight()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        # 只取夹取后的位置，保证对话框完整可见，尺寸仍由内容决定
        x, y, _, _, _ = clamp_window_state(
            x, y, w, h, 1.0, *desktop_bounds(
                self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
        about_window.geometry(geometry_pos(x, y))
        about_window.transient(self.root)
        about_window.deiconify()
        about_window.grab_set()
        about_window.bind("<Escape>", lambda _: about_window.destroy())

    def quit_app(self):
        try:
            self.save_window_geometry()
        finally:
            self.root.destroy()


def main():
    OverlayApp()


if __name__ == "__main__":
    main()
