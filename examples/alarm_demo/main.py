"""
闹钟演示应用主文件

这个演示展示了如何使用 FastAPI-MCP 和 WebSocket 实现一个完整的闹钟系统，
包括：
- 闹钟的 CRUD 操作
- 实时闹钟通知
- WebSocket 双向通信
- MCP 工具集成
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional

from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from fastapi_mcp import FastApiMCP

from .api import router as alarm_router
from .service import alarm_service
from .websocket_handler import websocket_endpoint, handle_alarm_trigger, websocket_manager
from .models import AlarmCreate, RepeatMode, AlarmTone

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="智能闹钟系统",
    description="基于 FastAPI-MCP 和 WebSocket 的智能闹钟演示应用",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 包含闹钟 API 路由
app.include_router(alarm_router)

# 添加客户端页面路由
@app.get("/client", response_class=HTMLResponse)
async def alarm_client():
    """闹钟客户端页面"""
    try:
        with open("/workspace/examples/alarm_demo/static/alarm_client.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>客户端页面未找到</h1>", status_code=404)

# WebSocket 端点
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket, client_id: Optional[str] = Query(None)):
    """WebSocket 连接端点"""
    await websocket_endpoint(websocket, client_id)

# 根路径
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """应用首页"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>智能闹钟系统</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { text-align: center; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .feature { background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }
            .endpoints { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .endpoint { margin: 10px 0; }
            .method { display: inline-block; padding: 2px 8px; border-radius: 3px; font-weight: bold; color: white; font-size: 12px; }
            .get { background-color: #28a745; }
            .post { background-color: #007bff; }
            .put { background-color: #ffc107; color: black; }
            .delete { background-color: #dc3545; }
            .websocket { background-color: #6f42c1; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .status { background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔔 智能闹钟系统</h1>
                <p>基于 FastAPI-MCP 和 WebSocket 的演示应用</p>
            </div>
            
            <div class="status">
                <h3>📊 系统状态</h3>
                <p>当前时间: <span id="current-time"></span></p>
                <p>服务状态: <span style="color: green;">运行中</span></p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h4>🔧 闹钟管理</h4>
                    <p>创建、编辑、删除闹钟</p>
                </div>
                <div class="feature">
                    <h4>⚡ 实时通知</h4>
                    <p>WebSocket 实时闹钟提醒</p>
                </div>
                <div class="feature">
                    <h4>🔄 重复模式</h4>
                    <p>支持多种重复模式</p>
                </div>
                <div class="feature">
                    <h4>🎵 多种铃声</h4>
                    <p>5种内置铃声选择</p>
                </div>
            </div>
            
            <div class="endpoints">
                <h3>📡 API 端点</h3>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/docs">/docs</a> - API 文档 (Swagger UI)
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/alarms/">/alarms/</a> - 获取所有闹钟
                </div>
                
                <div class="endpoint">
                    <span class="method post">POST</span>
                    /alarms/ - 创建新闹钟
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    /alarms/status/summary - 获取系统状态摘要
                </div>
                
                <div class="endpoint">
                    <span class="method websocket">WS</span>
                    <a href="javascript:void(0)" onclick="testWebSocket()">ws://localhost:8000/ws</a> - WebSocket 连接
                </div>
                
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/mcp">/mcp</a> - MCP HTTP 端点
                </div>
                
                <div class="endpoint">
                    <span class="method websocket">WS</span>
                    ws://localhost:8000/ws-mcp - MCP WebSocket 端点
                </div>
            </div>
            
            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p>💡 提示：访问 <a href="/docs">/docs</a> 来测试 API 功能</p>
                <p>🎨 或使用 <a href="/client" target="_blank" style="font-weight: bold; color: #007bff;">可视化客户端界面</a></p>
                <p>🔗 快速操作链接：
                    <a href="/alarms/quick?name=测试闹钟&time=18:00&repeat_daily=true" target="_blank">创建测试闹钟 (18:00)</a> |
                    <a href="/alarms/" target="_blank">查看所有闹钟</a> |
                    <a href="/alarms/status/summary" target="_blank">系统状态</a>
                </p>
            </div>
        </div>
        
        <script>
            // 更新当前时间
            function updateTime() {
                const now = new Date();
                document.getElementById('current-time').textContent = now.toLocaleTimeString();
            }
            
            // 每秒更新时间
            setInterval(updateTime, 1000);
            updateTime();
            
            // 测试 WebSocket 连接
            function testWebSocket() {
                if (typeof window.testWS !== 'undefined') {
                    alert('WebSocket 测试已在进行中');
                    return;
                }
                
                window.testWS = new WebSocket('ws://localhost:8000/ws?client_id=test_client');
                
                window.testWS.onopen = function(event) {
                    alert('WebSocket 连接成功！');
                    console.log('WebSocket 连接成功');
                };
                
                window.testWS.onmessage = function(event) {
                    console.log('收到消息:', event.data);
                };
                
                window.testWS.onclose = function(event) {
                    console.log('WebSocket 连接关闭');
                    delete window.testWS;
                };
                
                window.testWS.onerror = function(error) {
                    alert('WebSocket 连接失败');
                    console.error('WebSocket 错误:', error);
                };
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "alarm_service_running": alarm_service._is_running,
        "active_connections": len(websocket_manager.active_connections),
        "alarm_subscribers": len(websocket_manager.alarm_subscribers)
    }

# 应用生命周期事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 启动闹钟演示应用")
    
    # 启动闹钟服务
    await alarm_service.start()
    
    # 注册闹钟触发通知回调
    alarm_service.add_notification_callback(handle_alarm_trigger)
    
    # 创建一些示例闹钟（仅用于演示）
    await create_demo_alarms()
    
    logger.info("✅ 闹钟服务已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 关闭闹钟演示应用")
    
    # 停止闹钟服务
    await alarm_service.stop()
    
    logger.info("✅ 闹钟服务已停止")

async def create_demo_alarms():
    """创建一些演示用的闹钟"""
    try:
        # 获取当前时间，创建一个1分钟后的测试闹钟
        now = datetime.now()
        test_time = now.replace(second=0, microsecond=0)
        test_time = test_time.replace(minute=test_time.minute + 1)
        
        demo_alarms = [
            AlarmCreate(
                name="演示闹钟",
                time=test_time.strftime("%H:%M"),
                repeat_mode=RepeatMode.ONCE,
                tone=AlarmTone.CHIME,
                volume=70,
                enabled=True
            ),
            AlarmCreate(
                name="每日提醒",
                time="09:00",
                repeat_mode=RepeatMode.DAILY,
                tone=AlarmTone.BELL,
                volume=60,
                enabled=False  # 默认禁用，避免每天9点响铃
            ),
            AlarmCreate(
                name="工作日闹钟",
                time="07:30",
                repeat_mode=RepeatMode.WEEKDAYS,
                tone=AlarmTone.BUZZ,
                volume=80,
                enabled=False  # 默认禁用
            )
        ]
        
        for alarm_data in demo_alarms:
            result = await alarm_service.create_alarm(alarm_data)
            if result.success:
                logger.info(f"创建演示闹钟: {alarm_data.name}")
            else:
                logger.warning(f"创建演示闹钟失败: {result.message}")
                
    except Exception as e:
        logger.error(f"创建演示闹钟时出错: {e}")

# 创建 FastAPI-MCP 实例
mcp = FastApiMCP(app)

# 挂载 MCP 传输
mcp.mount_http(mount_path="/mcp")
mcp.mount_websocket(mount_path="/ws-mcp")

if __name__ == "__main__":
    import uvicorn
    
    print("🔔 智能闹钟系统")
    print("=" * 50)
    print("🌐 Web 界面: http://localhost:8000")
    print("📚 API 文档: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("🛠  MCP HTTP: http://localhost:8000/mcp")
    print("🔗 MCP WebSocket: ws://localhost:8000/ws-mcp")
    print("=" * 50)
    print("按 Ctrl+C 停止服务")
    
    try:
        uvicorn.run(
            "examples.alarm_demo.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # 生产环境建议设为 False
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 再见！")