# 🔔 智能闹钟演示

这是一个完整的闹钟系统演示，展示了如何使用 FastAPI-MCP 和 WebSocket 创建实时交互的应用程序。

## ✨ 功能特性

- **完整的闹钟管理**：创建、编辑、删除、启用/禁用闹钟
- **实时 WebSocket 通知**：闹钟触发时的即时通知
- **多种重复模式**：支持一次性、每日、每周、工作日、周末等模式
- **可配置铃声**：5种不同的铃声选择
- **音量控制**：0-100% 音量调节
- **暂停和关闭**：支持闹钟暂停（snooze）和关闭功能
- **MCP 集成**：通过 HTTP 和 WebSocket 提供 MCP 工具接口
- **美观的前端界面**：现代化的响应式 Web 界面

## 🚀 快速开始

### 1. 运行演示

```bash
# 进入项目根目录
cd /workspace

# 运行闹钟演示
python -m examples.alarm_demo.main
```

### 2. 访问界面

应用启动后，你可以访问以下端点：

- **🌐 主页**: http://localhost:8000
- **🎨 客户端界面**: http://localhost:8000/client
- **📚 API 文档**: http://localhost:8000/docs
- **🔌 WebSocket**: ws://localhost:8000/ws
- **🛠 MCP HTTP**: http://localhost:8000/mcp
- **🔗 MCP WebSocket**: ws://localhost:8000/ws-mcp

## 📱 使用说明

### 网页客户端界面

访问 http://localhost:8000/client 可以使用完整的可视化界面：

1. **创建闹钟**：在左侧面板填写闹钟信息并点击"创建闹钟"
2. **管理闹钟**：在右侧列表中查看、编辑、删除闹钟
3. **实时通知**：当闹钟触发时会收到弹窗通知
4. **WebSocket 日志**：底部显示实时的 WebSocket 通信日志

### API 接口

你也可以直接使用 REST API：

```bash
# 获取所有闹钟
curl http://localhost:8000/alarms/

# 创建新闹钟
curl -X POST http://localhost:8000/alarms/ \
  -H "Content-Type: application/json" \
  -d '{"name":"测试闹钟","time":"14:30","repeat_mode":"once","tone":"chime","volume":70}'

# 快速创建闹钟
curl "http://localhost:8000/alarms/quick?name=午休提醒&time=13:00&repeat_daily=true"

# 获取系统状态
curl http://localhost:8000/alarms/status/summary
```

### WebSocket 通信

连接到 WebSocket 端点可以接收实时通知：

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?client_id=my_client');

// 订阅闹钟通知
ws.send(JSON.stringify({
    type: 'subscribe_alarms',
    data: {}
}));

// 监听闹钟触发事件
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    if (message.type === 'alarm_triggered') {
        console.log('闹钟响了！', message.data);
    }
};
```

## 🔧 项目结构

```
alarm_demo/
├── __init__.py              # 包初始化
├── main.py                  # 主应用文件
├── models.py                # 数据模型定义
├── service.py               # 闹钟服务逻辑
├── api.py                   # REST API 端点
├── websocket_handler.py     # WebSocket 处理器
├── static/
│   └── alarm_client.html    # 前端客户端页面
└── README.md               # 说明文档
```

## 🎛 配置选项

### 闹钟参数

- **name**: 闹钟名称
- **time**: 时间 (HH:MM 格式)
- **repeat_mode**: 重复模式
  - `once`: 只响一次
  - `daily`: 每天
  - `weekly`: 每周
  - `weekdays`: 工作日 (周一到周五)
  - `weekends`: 周末 (周六、周日)
- **tone**: 铃声类型
  - `beep`: 哔哔声
  - `chime`: 钟声
  - `bell`: 铃声
  - `buzz`: 蜂鸣声
  - `melody`: 旋律
- **volume**: 音量 (0-100)
- **snooze_duration**: 暂停时长（分钟，1-60）
- **enabled**: 是否启用

### 系统配置

- **检查频率**: 每10秒检查一次闹钟
- **时间容差**: 10秒内的时间差异都算作触发
- **WebSocket 心跳**: 支持 ping/pong 心跳检测

## 🧪 测试功能

### 1. 基本功能测试

1. 创建一个1分钟后的测试闹钟
2. 观察 WebSocket 日志
3. 等待闹钟触发
4. 测试暂停和关闭功能

### 2. 重复闹钟测试

1. 创建每日重复闹钟
2. 测试启用/禁用功能
3. 观察重复闹钟的重新调度

### 3. WebSocket 连接测试

1. 打开浏览器开发者工具
2. 观察 WebSocket 连接状态
3. 测试重新连接功能
4. 查看实时消息传递

## 🔍 故障排除

### 常见问题

1. **闹钟不响**
   - 检查闹钟是否启用 (`enabled: true`)
   - 确认当前时间和闹钟时间
   - 查看服务器日志

2. **WebSocket 连接失败**
   - 检查防火墙设置
   - 确认端口 8000 未被占用
   - 尝试重新连接

3. **前端界面不显示**
   - 检查文件路径是否正确
   - 确认静态文件访问权限

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 扩展功能

这个演示可以作为基础进行扩展：

- **数据持久化**：添加数据库支持
- **用户系统**：多用户闹钟管理
- **移动应用**：开发移动端应用
- **智能功能**：天气集成、智能暂停等
- **集群部署**：支持多实例部署

## 📝 许可证

MIT License - 详见项目根目录的 LICENSE 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！