# 透明悬浮窗 (TransparentOverlay)

Windows 桌面上的半透明置顶黑窗，可拖动、改透明度，位置、大小和透明度自动保存。

## 运行

- 双击 `TransparentOverlayV1.pyw`，或运行 `pythonw TransparentOverlayV1.pyw`
- 调试时用 `python TransparentOverlayV1.pyw` 启动，报错会直接显示在终端

## 操作

| 操作 | 效果 |
|------|------|
| 左键拖动窗口任意位置 | 移动 |
| 窗口边框 | 调整大小（系统原生） |
| 右键 | 菜单：透明度、关于、退出 |
| 标题栏关闭按钮 | 保存配置并退出 |

## 配置

保存在 `%APPDATA%\TransparentOverlay\window_config.json`：

| 字段 | 含义 |
|------|------|
| x, y | 窗口左上角坐标，自动夹取到屏幕内 |
| width, height | 窗口尺寸，最小 100 |
| alpha | 透明度，范围 0.1–1.0 |

文件缺失或损坏时自动回退默认值，不影响启动。最小化/最大化状态下退出不会写配置。

## 代码结构

单文件 `TransparentOverlayV1.pyw`，只用标准库：

- `clamp_window_state` / `read_window_state` / `write_window_state`：纯数据逻辑，不依赖界面，可直接测试
- `OverlayApp`：界面与事件绑定
- `main`：创建配置目录并启动

不足 200 行，不拆包：拆分会增加维护面。

## 测试

```
python -m unittest -v
```

覆盖默认值、越界夹取、损坏配置回退和读写往返。修改配置或几何逻辑后请跑一遍。
