"""
WebSocket 실시간 알림 엔드포인트

보호자 앱에서 실시간으로 케이스/알림을 수신합니다.

연결 방식:
- 쿼리 파라미터로 토큰 전달: ws://host/ws/guardian?token=xxx
- 또는 첫 메시지로 인증
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import logger
from app.core.security import decode_token

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # guardian_id -> set of WebSocket connections
        self.active_connections: Dict[uuid.UUID, Set[WebSocket]] = {}
        # care_user_id -> set of guardian_ids
        self.care_user_guardians: Dict[uuid.UUID, Set[uuid.UUID]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        guardian_id: uuid.UUID,
        care_user_id: uuid.UUID,
    ):
        """새 연결 수락"""
        await websocket.accept()
        
        if guardian_id not in self.active_connections:
            self.active_connections[guardian_id] = set()
        self.active_connections[guardian_id].add(websocket)
        
        if care_user_id not in self.care_user_guardians:
            self.care_user_guardians[care_user_id] = set()
        self.care_user_guardians[care_user_id].add(guardian_id)
        
        logger.info(f"WebSocket connected: guardian={guardian_id}")
    
    def disconnect(
        self,
        websocket: WebSocket,
        guardian_id: uuid.UUID,
        care_user_id: uuid.UUID,
    ):
        """연결 해제"""
        if guardian_id in self.active_connections:
            self.active_connections[guardian_id].discard(websocket)
            if not self.active_connections[guardian_id]:
                del self.active_connections[guardian_id]
                
                # 돌봄 대상자 매핑에서도 제거
                if care_user_id in self.care_user_guardians:
                    self.care_user_guardians[care_user_id].discard(guardian_id)
        
        logger.info(f"WebSocket disconnected: guardian={guardian_id}")
    
    async def send_to_guardian(
        self,
        guardian_id: uuid.UUID,
        message: dict,
    ):
        """특정 보호자에게 메시지 전송"""
        if guardian_id not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[guardian_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}")
                disconnected.add(connection)
        
        # 실패한 연결 제거
        self.active_connections[guardian_id] -= disconnected
    
    async def send_to_care_user_guardians(
        self,
        care_user_id: uuid.UUID,
        message: dict,
    ):
        """돌봄 대상자의 모든 보호자에게 메시지 전송"""
        if care_user_id not in self.care_user_guardians:
            return
        
        for guardian_id in self.care_user_guardians[care_user_id]:
            await self.send_to_guardian(guardian_id, message)
    
    async def broadcast_case_update(
        self,
        care_user_id: uuid.UUID,
        case_id: uuid.UUID,
        case_number: str,
        event_type: str,
        severity: str,
        message: str,
    ):
        """케이스 업데이트 브로드캐스트"""
        payload = {
            "type": "case_update",
            "data": {
                "case_id": str(case_id),
                "case_number": case_number,
                "event_type": event_type,
                "severity": severity,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        await self.send_to_care_user_guardians(care_user_id, payload)
    
    async def broadcast_alert(
        self,
        guardian_id: uuid.UUID,
        alert_id: uuid.UUID,
        case_number: str,
        title: str,
        message: str,
        severity: str,
    ):
        """알림 브로드캐스트"""
        payload = {
            "type": "alert",
            "data": {
                "alert_id": str(alert_id),
                "case_number": case_number,
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        await self.send_to_guardian(guardian_id, payload)
    
    def get_connection_count(self) -> int:
        """활성 연결 수"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_connected_guardians(self) -> list:
        """연결된 보호자 목록"""
        return list(self.active_connections.keys())


# 전역 연결 관리자
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """연결 관리자 반환"""
    return manager


@router.websocket("/guardian")
async def websocket_guardian(
    websocket: WebSocket,
    token: str = Query(None, description="JWT 토큰"),
):
    """보호자 WebSocket 엔드포인트"""
    guardian_id = None
    care_user_id = None
    
    try:
        # 토큰 인증
        if not token:
            # 첫 메시지로 토큰 받기
            await websocket.accept()
            first_message = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=10.0,
            )
            try:
                data = json.loads(first_message)
                token = data.get("token")
            except json.JSONDecodeError:
                token = first_message
        
        if not token:
            await websocket.close(code=4001, reason="인증 토큰이 필요합니다.")
            return
        
        payload = decode_token(token)
        if not payload or payload.get("type") != "guardian":
            if websocket.client_state.name != "DISCONNECTED":
                await websocket.close(code=4002, reason="유효하지 않은 토큰입니다.")
            return
        
        guardian_id = uuid.UUID(payload["sub"])
        care_user_id = uuid.UUID(payload["care_user_id"])
        
        # 연결 등록
        await manager.connect(websocket, guardian_id, care_user_id)
        
        # 연결 확인 메시지 전송
        await websocket.send_json({
            "type": "connected",
            "data": {
                "guardian_id": str(guardian_id),
                "care_user_id": str(care_user_id),
                "message": "WebSocket 연결 성공",
            },
        })
        
        # 메시지 수신 대기
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,  # 60초 타임아웃
                )
                
                # 메시지 처리
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "ping":
                        # 핑-퐁
                        await websocket.send_json({"type": "pong"})
                    
                    elif msg_type == "ack":
                        # 알림 확인
                        alert_id = data.get("alert_id")
                        logger.info(f"Alert acknowledged via WebSocket: {alert_id}")
                    
                    else:
                        # 알 수 없는 메시지
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": f"Unknown message type: {msg_type}"},
                        })
                
                except json.JSONDecodeError:
                    pass
            
            except asyncio.TimeoutError:
                # 타임아웃 시 핑 전송
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        if guardian_id and care_user_id:
            manager.disconnect(websocket, guardian_id, care_user_id)


@router.get("/status")
async def websocket_status():
    """WebSocket 상태 조회"""
    return {
        "active_connections": manager.get_connection_count(),
        "connected_guardians": len(manager.get_connected_guardians()),
    }
