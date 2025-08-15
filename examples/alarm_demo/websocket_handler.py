"""
WebSocket 处理器 - 实现闹钟的实时通知功能
"""

import json
import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from .models import AlarmTriggerEvent, WebSocketMessage
from .service import alarm_service

logger = logging.getLogger(__name__)


class AlarmWebSocketManager:
    """闹钟 WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储活跃的 WebSocket 连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 订阅闹钟通知的连接
        self.alarm_subscribers: Set[str] = set()
        
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket 客户端连接: {client_id}")
        
        # 发送欢迎消息
        welcome_msg = WebSocketMessage(
            type="welcome",
            data={
                "message": "欢迎连接到闹钟服务",
                "client_id": client_id,
                "features": ["alarm_notifications", "real_time_updates"]
            }
        )
        await self.send_personal_message(welcome_msg, client_id)
        
    def disconnect(self, client_id: str) -> None:
        """断开 WebSocket 连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.alarm_subscribers:
            self.alarm_subscribers.discard(client_id)
        logger.info(f"WebSocket 客户端断开: {client_id}")
        
    async def send_personal_message(self, message: WebSocketMessage, client_id: str) -> None:
        """向特定客户端发送消息"""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(message.json())
            except Exception as e:
                logger.error(f"发送消息到客户端 {client_id} 失败: {e}")
                self.disconnect(client_id)
                
    async def broadcast_message(self, message: WebSocketMessage) -> None:
        """向所有连接的客户端广播消息"""
        if not self.active_connections:
            return
            
        message_text = message.json()
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"广播消息到客户端 {client_id} 失败: {e}")
                disconnected_clients.append(client_id)
                
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    async def broadcast_to_subscribers(self, message: WebSocketMessage) -> None:
        """向订阅闹钟通知的客户端发送消息"""
        if not self.alarm_subscribers:
            return
            
        message_text = message.json()
        disconnected_clients = []
        
        for client_id in list(self.alarm_subscribers):
            websocket = self.active_connections.get(client_id)
            if websocket:
                try:
                    await websocket.send_text(message_text)
                except Exception as e:
                    logger.error(f"发送闹钟通知到客户端 {client_id} 失败: {e}")
                    disconnected_clients.append(client_id)
            else:
                disconnected_clients.append(client_id)
                
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    async def handle_message(self, message_data: str, client_id: str) -> None:
        """处理来自客户端的消息"""
        try:
            data = json.loads(message_data)
            message_type = data.get("type")
            payload = data.get("data", {})
            
            if message_type == "subscribe_alarms":
                # 订阅闹钟通知
                self.alarm_subscribers.add(client_id)
                response = WebSocketMessage(
                    type="subscription_confirmed",
                    data={"message": "已订阅闹钟通知", "type": "alarms"}
                )
                await self.send_personal_message(response, client_id)
                logger.info(f"客户端 {client_id} 订阅了闹钟通知")
                
            elif message_type == "unsubscribe_alarms":
                # 取消订阅闹钟通知
                self.alarm_subscribers.discard(client_id)
                response = WebSocketMessage(
                    type="subscription_cancelled",
                    data={"message": "已取消订阅闹钟通知", "type": "alarms"}
                )
                await self.send_personal_message(response, client_id)
                logger.info(f"客户端 {client_id} 取消订阅闹钟通知")
                
            elif message_type == "ping":
                # 心跳检测
                response = WebSocketMessage(
                    type="pong",
                    data={"message": "pong"}
                )
                await self.send_personal_message(response, client_id)
                
            elif message_type == "get_status":
                # 获取当前状态
                alarms_response = await alarm_service.get_all_alarms()
                triggered_alarms = await alarm_service.get_triggered_alarms()
                
                status_data = {
                    "total_alarms": alarms_response.total,
                    "triggered_alarms": len(triggered_alarms),
                    "service_running": alarm_service._is_running,
                    "subscribers": len(self.alarm_subscribers),
                    "connections": len(self.active_connections)
                }
                
                response = WebSocketMessage(
                    type="status_update",
                    data=status_data
                )
                await self.send_personal_message(response, client_id)
                
            elif message_type == "dismiss_alarm":
                # 通过 WebSocket 关闭闹钟
                alarm_id = payload.get("alarm_id")
                if alarm_id:
                    try:
                        alarm_uuid = UUID(alarm_id)
                        result = await alarm_service.dismiss_alarm(alarm_uuid)
                        
                        response = WebSocketMessage(
                            type="alarm_dismissed",
                            data={
                                "alarm_id": alarm_id,
                                "success": result.success,
                                "message": result.message
                            }
                        )
                        
                        # 向所有订阅者广播
                        await self.broadcast_to_subscribers(response)
                        
                    except ValueError:
                        error_response = WebSocketMessage(
                            type="error",
                            data={"message": "无效的闹钟ID"}
                        )
                        await self.send_personal_message(error_response, client_id)
                        
            elif message_type == "snooze_alarm":
                # 通过 WebSocket 暂停闹钟
                alarm_id = payload.get("alarm_id")
                if alarm_id:
                    try:
                        alarm_uuid = UUID(alarm_id)
                        result = await alarm_service.snooze_alarm(alarm_uuid)
                        
                        response = WebSocketMessage(
                            type="alarm_snoozed",
                            data={
                                "alarm_id": alarm_id,
                                "success": result.success,
                                "message": result.message
                            }
                        )
                        
                        # 向所有订阅者广播
                        await self.broadcast_to_subscribers(response)
                        
                    except ValueError:
                        error_response = WebSocketMessage(
                            type="error",
                            data={"message": "无效的闹钟ID"}
                        )
                        await self.send_personal_message(error_response, client_id)
                        
            else:
                # 未知消息类型
                error_response = WebSocketMessage(
                    type="error",
                    data={"message": f"未知的消息类型: {message_type}"}
                )
                await self.send_personal_message(error_response, client_id)
                
        except json.JSONDecodeError:
            error_response = WebSocketMessage(
                type="error",
                data={"message": "无效的JSON格式"}
            )
            await self.send_personal_message(error_response, client_id)
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 消息时出错: {e}")
            error_response = WebSocketMessage(
                type="error",
                data={"message": f"服务器错误: {str(e)}"}
            )
            await self.send_personal_message(error_response, client_id)


# 全局 WebSocket 管理器实例
websocket_manager = AlarmWebSocketManager()


async def handle_alarm_trigger(event: AlarmTriggerEvent) -> None:
    """处理闹钟触发事件的回调函数"""
    
    # 创建闹钟触发通知消息
    notification = WebSocketMessage(
        type="alarm_triggered",
        data={
            "alarm_id": str(event.alarm_id),
            "alarm_name": event.alarm_name,
            "triggered_at": event.triggered_at.isoformat(),
            "tone": event.tone,
            "volume": event.volume,
            "message": event.message
        }
    )
    
    # 向所有订阅者发送通知
    await websocket_manager.broadcast_to_subscribers(notification)
    
    logger.info(f"已发送闹钟触发通知: {event.alarm_name}")


# WebSocket 端点处理函数
async def websocket_endpoint(websocket: WebSocket, client_id: str = None) -> None:
    """WebSocket 端点处理函数"""
    
    # 如果没有提供 client_id，生成一个
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())[:8]
        
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            await websocket_manager.handle_message(data, client_id)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket 处理出错: {e}")
        websocket_manager.disconnect(client_id)