"""
闹钟服务实现
"""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Callable, Awaitable
from uuid import UUID

from .models import (
    Alarm, AlarmCreate, AlarmUpdate, AlarmStatus, RepeatMode,
    AlarmTriggerEvent, AlarmListResponse, AlarmResponse
)

logger = logging.getLogger(__name__)


class AlarmService:
    """闹钟服务类"""
    
    def __init__(self):
        self._alarms: Dict[UUID, Alarm] = {}
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
        self._notification_callbacks: List[Callable[[AlarmTriggerEvent], Awaitable[None]]] = []
        
    async def start(self):
        """启动闹钟服务"""
        if self._is_running:
            logger.warning("闹钟服务已在运行")
            return
            
        self._is_running = True
        self._check_task = asyncio.create_task(self._alarm_checker_loop())
        logger.info("闹钟服务已启动")
        
    async def stop(self):
        """停止闹钟服务"""
        if not self._is_running:
            return
            
        self._is_running = False
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("闹钟服务已停止")
        
    def add_notification_callback(self, callback: Callable[[AlarmTriggerEvent], Awaitable[None]]):
        """添加闹钟触发通知回调"""
        self._notification_callbacks.append(callback)
        
    async def create_alarm(self, alarm_data: AlarmCreate) -> AlarmResponse:
        """创建新闹钟"""
        try:
            # 解析时间
            hour, minute = map(int, alarm_data.time.split(':'))
            alarm_time = time(hour, minute)
            
            # 创建闹钟对象
            alarm = Alarm(
                name=alarm_data.name,
                time=alarm_time,
                repeat_mode=alarm_data.repeat_mode,
                tone=alarm_data.tone,
                volume=alarm_data.volume,
                snooze_duration=alarm_data.snooze_duration,
                enabled=alarm_data.enabled
            )
            
            # 存储闹钟
            self._alarms[alarm.id] = alarm
            
            logger.info(f"创建闹钟: {alarm.name} at {alarm.time}")
            
            return AlarmResponse(
                success=True,
                message="闹钟创建成功",
                alarm=alarm
            )
            
        except Exception as e:
            logger.error(f"创建闹钟失败: {e}")
            return AlarmResponse(
                success=False,
                message=f"创建闹钟失败: {str(e)}"
            )
            
    async def get_alarm(self, alarm_id: UUID) -> Optional[Alarm]:
        """获取单个闹钟"""
        return self._alarms.get(alarm_id)
        
    async def get_all_alarms(self) -> AlarmListResponse:
        """获取所有闹钟"""
        alarms = list(self._alarms.values())
        # 按创建时间排序
        alarms.sort(key=lambda x: x.created_at)
        
        return AlarmListResponse(
            alarms=alarms,
            total=len(alarms)
        )
        
    async def update_alarm(self, alarm_id: UUID, update_data: AlarmUpdate) -> AlarmResponse:
        """更新闹钟"""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return AlarmResponse(
                success=False,
                message="闹钟不存在"
            )
            
        try:
            # 更新字段
            update_dict = update_data.dict(exclude_unset=True)
            
            # 处理时间更新
            if "time" in update_dict:
                hour, minute = map(int, update_dict["time"].split(':'))
                update_dict["time"] = time(hour, minute)
                
            # 更新闹钟对象
            for field, value in update_dict.items():
                setattr(alarm, field, value)
                
            logger.info(f"更新闹钟: {alarm.name}")
            
            return AlarmResponse(
                success=True,
                message="闹钟更新成功",
                alarm=alarm
            )
            
        except Exception as e:
            logger.error(f"更新闹钟失败: {e}")
            return AlarmResponse(
                success=False,
                message=f"更新闹钟失败: {str(e)}"
            )
            
    async def delete_alarm(self, alarm_id: UUID) -> AlarmResponse:
        """删除闹钟"""
        alarm = self._alarms.pop(alarm_id, None)
        if not alarm:
            return AlarmResponse(
                success=False,
                message="闹钟不存在"
            )
            
        logger.info(f"删除闹钟: {alarm.name}")
        
        return AlarmResponse(
            success=True,
            message="闹钟删除成功"
        )
        
    async def toggle_alarm(self, alarm_id: UUID) -> AlarmResponse:
        """切换闹钟启用/禁用状态"""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return AlarmResponse(
                success=False,
                message="闹钟不存在"
            )
            
        alarm.enabled = not alarm.enabled
        status_text = "启用" if alarm.enabled else "禁用"
        
        logger.info(f"{status_text}闹钟: {alarm.name}")
        
        return AlarmResponse(
            success=True,
            message=f"闹钟已{status_text}",
            alarm=alarm
        )
        
    async def snooze_alarm(self, alarm_id: UUID) -> AlarmResponse:
        """暂停闹钟"""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return AlarmResponse(
                success=False,
                message="闹钟不存在"
            )
            
        if alarm.status != AlarmStatus.TRIGGERED:
            return AlarmResponse(
                success=False,
                message="只有已触发的闹钟才能暂停"
            )
            
        # 设置暂停状态
        alarm.status = AlarmStatus.SNOOZED
        
        # 计算新的闹钟时间（当前时间 + 暂停时长）
        now = datetime.now()
        snooze_time = now + timedelta(minutes=alarm.snooze_duration)
        alarm.time = snooze_time.time()
        
        logger.info(f"暂停闹钟: {alarm.name}, 将在 {alarm.snooze_duration} 分钟后重新响起")
        
        return AlarmResponse(
            success=True,
            message=f"闹钟已暂停 {alarm.snooze_duration} 分钟",
            alarm=alarm
        )
        
    async def dismiss_alarm(self, alarm_id: UUID) -> AlarmResponse:
        """关闭闹钟"""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return AlarmResponse(
                success=False,
                message="闹钟不存在"
            )
            
        if alarm.status != AlarmStatus.TRIGGERED:
            return AlarmResponse(
                success=False,
                message="只有已触发的闹钟才能关闭"
            )
            
        # 根据重复模式决定下一步
        if alarm.repeat_mode == RepeatMode.ONCE:
            alarm.enabled = False
            alarm.status = AlarmStatus.INACTIVE
        else:
            alarm.status = AlarmStatus.ACTIVE
            # 如果是重复闹钟，设置下次触发时间
            self._set_next_alarm_time(alarm)
            
        logger.info(f"关闭闹钟: {alarm.name}")
        
        return AlarmResponse(
            success=True,
            message="闹钟已关闭",
            alarm=alarm
        )
        
    def _set_next_alarm_time(self, alarm: Alarm):
        """设置重复闹钟的下次触发时间"""
        now = datetime.now()
        current_time = alarm.time
        
        if alarm.repeat_mode == RepeatMode.DAILY:
            # 每天重复：如果今天时间已过，设置为明天
            next_datetime = datetime.combine(now.date(), current_time)
            if next_datetime <= now:
                next_datetime += timedelta(days=1)
        elif alarm.repeat_mode == RepeatMode.WEEKLY:
            # 每周重复：设置为下周同一天
            next_datetime = datetime.combine(now.date(), current_time)
            if next_datetime <= now:
                next_datetime += timedelta(days=7)
        elif alarm.repeat_mode == RepeatMode.WEEKDAYS:
            # 工作日重复：设置为下个工作日
            next_datetime = datetime.combine(now.date(), current_time)
            while next_datetime <= now or next_datetime.weekday() >= 5:  # 5=Saturday, 6=Sunday
                next_datetime += timedelta(days=1)
        elif alarm.repeat_mode == RepeatMode.WEEKENDS:
            # 周末重复：设置为下个周末
            next_datetime = datetime.combine(now.date(), current_time)
            while next_datetime <= now or next_datetime.weekday() < 5:
                next_datetime += timedelta(days=1)
        else:
            # 默认情况：设置为明天
            next_datetime = datetime.combine(now.date(), current_time) + timedelta(days=1)
            
        alarm.time = next_datetime.time()
        
    async def _alarm_checker_loop(self):
        """闹钟检查循环"""
        logger.info("闹钟检查循环已启动")
        
        while self._is_running:
            try:
                await self._check_alarms()
                # 每10秒检查一次
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"闹钟检查循环出错: {e}")
                await asyncio.sleep(10)
                
        logger.info("闹钟检查循环已停止")
        
    async def _check_alarms(self):
        """检查所有闹钟是否需要触发"""
        now = datetime.now()
        current_time = now.time()
        
        for alarm in self._alarms.values():
            if not alarm.enabled or alarm.status == AlarmStatus.TRIGGERED:
                continue
                
            # 检查是否到了闹钟时间（允许10秒误差）
            alarm_datetime = datetime.combine(now.date(), alarm.time)
            time_diff = abs((alarm_datetime - now).total_seconds())
            
            if time_diff <= 10:  # 10秒内算作触发
                await self._trigger_alarm(alarm, now)
                
    async def _trigger_alarm(self, alarm: Alarm, trigger_time: datetime):
        """触发闹钟"""
        alarm.status = AlarmStatus.TRIGGERED
        alarm.last_triggered = trigger_time
        
        # 创建触发事件
        event = AlarmTriggerEvent(
            alarm_id=alarm.id,
            alarm_name=alarm.name,
            triggered_at=trigger_time,
            tone=alarm.tone,
            volume=alarm.volume,
            message=f"闹钟 '{alarm.name}' 响了！当前时间: {trigger_time.strftime('%H:%M:%S')}"
        )
        
        logger.info(f"触发闹钟: {alarm.name} at {trigger_time}")
        
        # 通知所有回调
        for callback in self._notification_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"闹钟通知回调失败: {e}")
                
    async def get_triggered_alarms(self) -> List[Alarm]:
        """获取所有已触发的闹钟"""
        return [alarm for alarm in self._alarms.values() if alarm.status == AlarmStatus.TRIGGERED]


# 全局闹钟服务实例
alarm_service = AlarmService()