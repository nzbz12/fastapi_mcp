"""
闹钟演示的数据模型定义
"""

from datetime import datetime, time
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class AlarmStatus(str, Enum):
    """闹钟状态枚举"""
    ACTIVE = "active"       # 激活状态
    INACTIVE = "inactive"   # 非激活状态
    TRIGGERED = "triggered" # 已触发
    SNOOZED = "snoozed"    # 暂停状态


class RepeatMode(str, Enum):
    """重复模式枚举"""
    ONCE = "once"           # 只响一次
    DAILY = "daily"         # 每天
    WEEKLY = "weekly"       # 每周
    WEEKDAYS = "weekdays"   # 工作日
    WEEKENDS = "weekends"   # 周末


class AlarmTone(str, Enum):
    """闹钟铃声枚举"""
    BEEP = "beep"
    CHIME = "chime"
    BELL = "bell"
    BUZZ = "buzz"
    MELODY = "melody"


class Alarm(BaseModel):
    """闹钟数据模型"""
    id: UUID = Field(default_factory=uuid4, description="闹钟唯一标识")
    name: str = Field(..., description="闹钟名称", max_length=100)
    time: time = Field(..., description="闹钟时间")
    status: AlarmStatus = Field(default=AlarmStatus.ACTIVE, description="闹钟状态")
    repeat_mode: RepeatMode = Field(default=RepeatMode.ONCE, description="重复模式")
    tone: AlarmTone = Field(default=AlarmTone.BEEP, description="闹钟铃声")
    volume: int = Field(default=50, ge=0, le=100, description="音量 (0-100)")
    snooze_duration: int = Field(default=5, ge=1, le=60, description="暂停时长（分钟）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_triggered: Optional[datetime] = Field(default=None, description="最后触发时间")
    enabled: bool = Field(default=True, description="是否启用")

    class Config:
        json_encoders = {
            time: lambda v: v.strftime("%H:%M:%S"),
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AlarmCreate(BaseModel):
    """创建闹钟的请求模型"""
    name: str = Field(..., description="闹钟名称", max_length=100)
    time: str = Field(..., description="闹钟时间 (HH:MM 格式)", regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    repeat_mode: RepeatMode = Field(default=RepeatMode.ONCE, description="重复模式")
    tone: AlarmTone = Field(default=AlarmTone.BEEP, description="闹钟铃声")
    volume: int = Field(default=50, ge=0, le=100, description="音量 (0-100)")
    snooze_duration: int = Field(default=5, ge=1, le=60, description="暂停时长（分钟）")
    enabled: bool = Field(default=True, description="是否启用")


class AlarmUpdate(BaseModel):
    """更新闹钟的请求模型"""
    name: Optional[str] = Field(None, description="闹钟名称", max_length=100)
    time: Optional[str] = Field(None, description="闹钟时间 (HH:MM 格式)", regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    repeat_mode: Optional[RepeatMode] = Field(None, description="重复模式")
    tone: Optional[AlarmTone] = Field(None, description="闹钟铃声")
    volume: Optional[int] = Field(None, ge=0, le=100, description="音量 (0-100)")
    snooze_duration: Optional[int] = Field(None, ge=1, le=60, description="暂停时长（分钟）")
    enabled: Optional[bool] = Field(None, description="是否启用")


class AlarmTriggerEvent(BaseModel):
    """闹钟触发事件模型"""
    alarm_id: UUID = Field(..., description="闹钟ID")
    alarm_name: str = Field(..., description="闹钟名称")
    triggered_at: datetime = Field(default_factory=datetime.now, description="触发时间")
    tone: AlarmTone = Field(..., description="闹钟铃声")
    volume: int = Field(..., description="音量")
    message: str = Field(..., description="触发消息")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class AlarmListResponse(BaseModel):
    """闹钟列表响应模型"""
    alarms: List[Alarm] = Field(..., description="闹钟列表")
    total: int = Field(..., description="总数量")


class AlarmResponse(BaseModel):
    """单个闹钟响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    alarm: Optional[Alarm] = Field(None, description="闹钟数据")


class WebSocketMessage(BaseModel):
    """WebSocket 消息模型"""
    type: str = Field(..., description="消息类型")
    data: dict = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }