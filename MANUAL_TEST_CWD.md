# 手动测试工作目录保存功能

## 快速测试步骤

### 1. 启动应用
```bash
cd /home/newdisk/work/vector-drawing-board
python main.py
```

应用会以全屏模式打开，并创建一个终端。

### 2. 在终端中切换目录

在终端中输入以下命令：
```bash
cd /tmp
pwd  # 应该显示 /tmp
```

### 3. 添加更多终端并切换到不同目录

- 按 `Ctrl + Shift + T` 创建第二个终端
- 在第二个终端中输入：
  ```bash
  cd ~/Downloads
  pwd
  ```

- 再按 `Ctrl + Shift + T` 创建第三个终端
- 在第三个终端中输入：
  ```bash
  cd ~/Documents
  pwd
  ```

### 4. 关闭应用

按 `Ctrl + Q` 或关闭窗口。

### 5. 重新打开应用

```bash
python main.py
```

### 6. 验证结果

检查每个终端是否自动恢复到上次的工作目录：
- 终端 1 应该在 `/tmp` 目录
- 终端 2 应该在 `~/Downloads` 目录
- 终端 3 应该在 `~/Documents` 目录

在每个终端中运行 `pwd` 命令验证。

## 预期结果

✅ **成功**: 每个终端都自动恢复到上次的工作目录
❌ **失败**: 终端启动在默认目录（通常是 `~`）

## 调试

如果功能不工作，检查以下内容：

### 1. 查看状态文件

```bash
cat ~/.config/TerminalBoard/state.json
```

应该看到类似这样的内容：
```json
{
  "zoom": 1.0,
  "terminals": [
    {
      "lx": 50,
      "ly": 50,
      "lw": 380,
      "lh": 220,
      "cwd": "/tmp"
    },
    {
      "lx": 450,
      "ly": 50,
      "lw": 380,
      "lh": 220,
      "cwd": "/home/user/Downloads"
    }
  ]
}
```

### 2. 检查 /proc 支持

```bash
ls -la /proc/self/cwd
```

应该输出当前目录的符号链接。

### 3. 启用调试输出

编辑 `ui/terminal_widget.py`，在 `get_current_cwd()` 中添加打印：

```python
def get_current_cwd(self) -> str:
    if self._pid is None:
        return os.getcwd()
    try:
        cwd = os.readlink(f"/proc/{self._pid}/cwd")
        print(f"[DEBUG] Terminal PID {self._pid} CWD: {cwd}")
        return cwd
    except (OSError, FileNotFoundError) as e:
        print(f"[DEBUG] Failed to get CWD: {e}")
        return os.getcwd()
```

## 高级测试

### 测试目录不存在的情况

1. 切换到某个目录：`cd /tmp/test-temp-dir`
2. 创建该目录：`mkdir -p /tmp/test-temp-dir`
3. 关闭应用
4. 删除该目录：`rm -rf /tmp/test-temp-dir`
5. 重新打开应用
6. 终端应该启动在默认目录（优雅降级）

### 测试多终端同步

1. 创建多个终端，都在不同目录
2. 拖动终端到不同位置
3. 调整终端大小
4. 关闭应用
5. 重新打开
6. 验证位置、大小和工作目录都正确恢复

## 性能测试

创建 10 个终端，每个在不同目录：
```bash
for i in {1..10}; do
    mkdir -p /tmp/test-$i
done
```

然后在每个终端中切换到对应目录，关闭并重新打开应用，验证所有目录都正确恢复。

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 目录未保存 | 应用异常终止 | 确保使用 Ctrl+Q 正常关闭 |
| 目录未恢复 | 状态文件损坏 | 删除 ~/.config/TerminalBoard/state.json 重试 |
| 所有终端在同一目录 | /proc 不可用 | 检查系统是否支持 /proc 文件系统 |
| 目录恢复错误 | 权限问题 | 检查目录是否有访问权限 |

## 日志位置

应用输出会打印到启动终端的 stderr，查看任何错误信息：
```bash
python main.py 2>&1 | tee terminal-board.log
```
