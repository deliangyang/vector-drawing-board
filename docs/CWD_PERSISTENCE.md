# 终端工作目录保存功能

## 功能描述

当你关闭 Terminal Board 应用时，每个终端的当前工作目录会自动保存。下次打开应用时，每个终端会自动恢复到上次的工作目录。

## 实现原理

### 1. 获取当前工作目录

通过 Linux `/proc` 文件系统读取 shell 进程的当前工作目录：

```python
def get_current_cwd(self) -> str:
    """获取 shell 进程的当前工作目录。"""
    if self._pid is None:
        return os.getcwd()
    try:
        # 通过 /proc 读取进程的当前目录
        return os.readlink(f"/proc/{self._pid}/cwd")
    except (OSError, FileNotFoundError):
        return os.getcwd()
```

### 2. 保存状态

在应用关闭时，`MainWindow.closeEvent()` 会调用 `_save_state()`：

```python
def _save_state(self):
    """保存终端布局和缩放，包括每个终端的工作目录。"""
    path = self._state_file()
    if not path:
        return
    state = {
        "zoom": self._canvas.zoom_factor(),
        "terminals": self._container.get_terminal_layout(),
    }
    # ... 写入 JSON 文件
```

`get_terminal_layout()` 返回的数据结构现在包含 `cwd` 字段：

```python
{
    "lx": 50,      # 逻辑 X 坐标
    "ly": 50,      # 逻辑 Y 坐标
    "lw": 380,     # 逻辑宽度
    "lh": 220,     # 逻辑高度
    "cwd": "/home/user/projects"  # 当前工作目录
}
```

### 3. 恢复终端

启动应用时，`_restore_or_new_terminal()` 读取保存的状态：

```python
def restore_terminals(self, layout_list):
    for rect in layout_list:
        cwd = rect.get("cwd")
        self._add_terminal_at(
            rect.get("lx", 50),
            rect.get("ly", 50),
            rect.get("lw", 380),
            rect.get("lh", 220),
            cwd=cwd,  # 传递保存的工作目录
        )
```

### 4. 设置初始目录

在 shell 进程启动前（子进程中），切换到保存的目录：

```python
if self._initial_cwd and os.path.isdir(self._initial_cwd):
    try:
        os.chdir(self._initial_cwd)
    except OSError:
        pass

os.execve(shell, [shell, "-i"], env)
```

## 状态文件位置

根据操作系统的标准配置目录：

- **Linux**: `~/.config/TerminalBoard/state.json`
- **macOS**: `~/Library/Application Support/TerminalBoard/state.json`
- **Windows**: `C:\Users\<user>\AppData\Local\TerminalBoard\state.json`

## 状态文件格式

```json
{
  "zoom": 1.0,
  "terminals": [
    {
      "lx": 50,
      "ly": 50,
      "lw": 380,
      "lh": 220,
      "cwd": "/home/user/projects/my-app"
    },
    {
      "lx": 450,
      "ly": 50,
      "lw": 380,
      "lh": 220,
      "cwd": "/home/user/downloads"
    }
  ]
}
```

## 兼容性

### 目录不存在时的处理

如果保存的目录已被删除或不可访问，shell 会启动在默认目录（通常是用户主目录）。

```python
if cwd and os.path.isdir(cwd):
    card.set_initial_cwd(cwd)
```

### 跨平台考虑

- **Linux**: 使用 `/proc/{pid}/cwd` 获取当前目录
- **macOS/BSD**: 需要使用 `lsof` 或其他方法
- **Windows**: 不支持 `/proc`，需要替代方案

当前实现主要针对 Linux 系统。

## 测试

运行测试脚本：

```bash
python test_cwd_persistence.py
```

测试会：
1. 创建终端
2. 获取并保存当前工作目录
3. 重新加载终端
4. 验证工作目录是否正确恢复

## 使用示例

### 场景 1: 多项目工作
1. 打开 Terminal Board
2. 创建 3 个终端
3. 在终端 1 中切换到项目 A: `cd ~/projects/project-a`
4. 在终端 2 中切换到项目 B: `cd ~/projects/project-b`
5. 在终端 3 中切换到下载目录: `cd ~/downloads`
6. 关闭应用
7. 重新打开应用
8. ✅ 每个终端自动恢复到各自的工作目录

### 场景 2: 长期会话
- 在一个终端中深入嵌套目录结构工作
- 关闭应用时不需要手动记录路径
- 下次打开时直接继续工作

## 优势

1. **无缝体验**: 不需要手动记录或恢复工作目录
2. **多项目支持**: 每个终端独立保存目录
3. **自动化**: 完全透明，无需用户干预
4. **可靠性**: 即使目录不存在也能优雅降级

## 注意事项

1. 只在应用正常关闭时保存状态
2. 强制终止进程（kill -9）不会保存状态
3. shell 进程必须存活才能正确读取工作目录
4. 当前实现依赖 Linux `/proc` 文件系统

## 未来改进

1. 支持 macOS 和 Windows
2. 保存每个终端的命令历史
3. 保存环境变量
4. 保存终端的 scrollback 缓冲区
5. 支持终端会话快照
