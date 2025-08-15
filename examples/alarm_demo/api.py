"""
闹钟 API 端点定义
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from .models import (
    AlarmCreate, AlarmUpdate, AlarmListResponse, AlarmResponse,
    Alarm, AlarmTone, RepeatMode
)
from .service import alarm_service

# 创建路由器
router = APIRouter(prefix="/alarms", tags=["闹钟管理"])


@router.post("/", response_model=AlarmResponse, summary="创建闹钟")
async def create_alarm(alarm_data: AlarmCreate):
    """
    创建新的闹钟
    
    - **name**: 闹钟名称
    - **time**: 闹钟时间 (HH:MM 格式)
    - **repeat_mode**: 重复模式
    - **tone**: 闹钟铃声
    - **volume**: 音量 (0-100)
    - **snooze_duration**: 暂停时长（分钟）
    - **enabled**: 是否启用
    """
    return await alarm_service.create_alarm(alarm_data)


@router.get("/", response_model=AlarmListResponse, summary="获取闹钟列表")
async def get_alarms():
    """
    获取所有闹钟列表
    """
    return await alarm_service.get_all_alarms()


@router.get("/{alarm_id}", response_model=Alarm, summary="获取单个闹钟")
async def get_alarm(alarm_id: UUID):
    """
    根据ID获取单个闹钟信息
    """
    alarm = await alarm_service.get_alarm(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="闹钟不存在")
    return alarm


@router.put("/{alarm_id}", response_model=AlarmResponse, summary="更新闹钟")
async def update_alarm(alarm_id: UUID, update_data: AlarmUpdate):
    """
    更新闹钟信息
    """
    return await alarm_service.update_alarm(alarm_id, update_data)


@router.delete("/{alarm_id}", response_model=AlarmResponse, summary="删除闹钟")
async def delete_alarm(alarm_id: UUID):
    """
    删除指定的闹钟
    """
    return await alarm_service.delete_alarm(alarm_id)


@router.post("/{alarm_id}/toggle", response_model=AlarmResponse, summary="切换闹钟状态")
async def toggle_alarm(alarm_id: UUID):
    """
    切换闹钟的启用/禁用状态
    """
    return await alarm_service.toggle_alarm(alarm_id)


@router.post("/{alarm_id}/snooze", response_model=AlarmResponse, summary="暂停闹钟")
async def snooze_alarm(alarm_id: UUID):
    """
    暂停已触发的闹钟
    """
    return await alarm_service.snooze_alarm(alarm_id)


@router.post("/{alarm_id}/dismiss", response_model=AlarmResponse, summary="关闭闹钟")
async def dismiss_alarm(alarm_id: UUID):
    """
    关闭已触发的闹钟
    """
    return await alarm_service.dismiss_alarm(alarm_id)


@router.get("/triggered/list", response_model=List[Alarm], summary="获取已触发的闹钟")
async def get_triggered_alarms():
    """
    获取所有已触发的闹钟列表
    """
    return await alarm_service.get_triggered_alarms()


# 辅助端点
@router.get("/meta/tones", summary="获取可用铃声列表")
async def get_available_tones():
    """
    获取所有可用的闹钟铃声选项
    """
    return {
        "tones": [
            {"value": tone.value, "name": tone.value.title()}
            for tone in AlarmTone
        ]
    }


@router.get("/meta/repeat-modes", summary="获取重复模式列表")
async def get_repeat_modes():
    """
    获取所有可用的重复模式选项
    """
    mode_names = {
        RepeatMode.ONCE: "只响一次",
        RepeatMode.DAILY: "每天",
        RepeatMode.WEEKLY: "每周",
        RepeatMode.WEEKDAYS: "工作日",
        RepeatMode.WEEKENDS: "周末"
    }
    
    return {
        "repeat_modes": [
            {"value": mode.value, "name": mode_names[mode]}
            for mode in RepeatMode
        ]
    }


@router.get("/status/summary", summary="获取闹钟状态摘要")
async def get_alarm_summary():
    """
    获取闹钟系统的状态摘要
    """
    alarms_response = await alarm_service.get_all_alarms()
    alarms = alarms_response.alarms
    
    summary = {
        "total_alarms": len(alarms),
        "enabled_alarms": len([a for a in alarms if a.enabled]),
        "disabled_alarms": len([a for a in alarms if not a.enabled]),
        "triggered_alarms": len([a for a in alarms if a.status.value == "triggered"]),
        "current_time": datetime.now().strftime("%H:%M:%S"),
        "service_running": alarm_service._is_running
    }
    
    return summary


# 快速创建闹钟的便捷端点
@router.post("/quick", response_model=AlarmResponse, summary="快速创建闹钟")
async def create_quick_alarm(
    name: str = Query(..., description="闹钟名称"),
    time: str = Query(..., description="闹钟时间 (HH:MM)", regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"),
    repeat_daily: bool = Query(False, description="是否每天重复")
):
    """
    快速创建闹钟的便捷接口
    
    - **name**: 闹钟名称
    - **time**: 闹钟时间 (HH:MM 格式)
    - **repeat_daily**: 是否每天重复
    """
    alarm_data = AlarmCreate(
        name=name,
        time=time,
        repeat_mode=RepeatMode.DAILY if repeat_daily else RepeatMode.ONCE
    )
    
    return await alarm_service.create_alarm(alarm_data)