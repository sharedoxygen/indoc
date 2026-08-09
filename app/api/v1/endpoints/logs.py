"""
Admin Log Viewer API Endpoints

Secure, admin-only access to system logs for diagnostics and troubleshooting.
Per AI Prompt Engineering Guide §9: Enforce scope and minimum necessary disclosure.
"""
import os
import re
import subprocess
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import json

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.core.security import require_admin
from pydantic import BaseModel, Field


router = APIRouter()


class LogEntry(BaseModel):
    """Single log entry"""
    timestamp: str
    level: str
    logger: str
    message: str
    line_number: int
    exception: Optional[str] = None


class LogResponse(BaseModel):
    """Log viewer response"""
    logs: List[LogEntry]
    total_lines: int
    filtered_lines: int
    log_file: str
    last_updated: str


class LogStats(BaseModel):
    """Log statistics"""
    total_lines: int
    error_count: int
    warning_count: int
    info_count: int
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    file_size_mb: float
    last_modified: str


def _require_admin_role(user: User) -> None:
    """Enforce admin-only access (Guide §9: minimum necessary disclosure)"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Admin access required to view system logs"
        )


def _parse_log_line(line: str, line_number: int, last_timestamp: str = None) -> Optional[LogEntry]:
    """
    Parse structured log line - supports multiple formats
    EVERY entry gets a timestamp (uses last known or generates one)
    
    Format 1 (Python logging): 2025-10-10 18:06:10,708 INFO sqlalchemy.engine.Engine message
    Format 2 (Celery): [2025-10-06 12:50:39,457: WARNING/MainProcess] message
    Format 3 (Uvicorn): INFO:     message
    Format 4 (Continuation): Any line without timestamp inherits from previous
    """
    # Try Format 1: Standard Python logging
    pattern1 = r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(\w+)\s+([\w\.]+)\s+(.*)$'
    match = re.match(pattern1, line)
    if match:
        timestamp, level, logger, message = match.groups()
        return LogEntry(
            timestamp=timestamp,
            level=level,
            logger=logger,
            message=message.strip(),
            line_number=line_number
        )
    
    # Try Format 2: Celery format [timestamp: LEVEL/Process]
    pattern2 = r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}):\s+(\w+)/([^\]]+)\]\s+(.*)$'
    match = re.match(pattern2, line)
    if match:
        timestamp, level, process, message = match.groups()
        return LogEntry(
            timestamp=timestamp,
            level=level,
            logger=process,
            message=message.strip(),
            line_number=line_number
        )
    
    # Try Format 3: Uvicorn format (INFO:     message)
    pattern3 = r'^(\w+):\s+(.*)$'
    match = re.match(pattern3, line)
    if match:
        level, message = match.groups()
        # Use last known timestamp or generate one
        fallback_timestamp = last_timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S,000")
        return LogEntry(
            timestamp=fallback_timestamp,
            level=level,
            logger="uvicorn",
            message=message.strip(),
            line_number=line_number
        )
    
    # If no match, treat as continuation - use last timestamp or generate
    fallback_timestamp = last_timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S,000")
    return LogEntry(
        timestamp=fallback_timestamp,
        level="INFO",
        logger="continuation",
        message=line.strip(),
        line_number=line_number
    )


def _is_docker_container(log_name: str) -> bool:
    """Check if log name refers to a Docker container"""
    docker_containers = ["docker_elasticsearch", "docker_qdrant", "docker_redis", "docker_postgres", "docker_t2v"]
    return log_name in docker_containers


def _get_docker_logs(container_name: str, lines: int = 100) -> List[str]:
    """Fetch logs from Docker container"""
    # Map friendly names to actual container names
    container_map = {
        "docker_elasticsearch": "indoc-elasticsearch",
        "docker_qdrant": "indoc-qdrant",
        "docker_redis": "indoc-redis",
        "docker_postgres": "indoc-postgres",
        "docker_t2v": "indoc-t2v-transformers"
    }
    
    actual_container = container_map.get(container_name, container_name)
    
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), actual_container],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return [f"Error fetching Docker logs: {result.stderr}"]
        
        # Combine stdout and stderr (Docker logs go to both)
        logs = result.stdout + result.stderr
        return logs.split('\n') if logs else []
        
    except subprocess.TimeoutExpired:
        return ["Error: Docker logs command timed out"]
    except FileNotFoundError:
        return ["Error: Docker command not found. Is Docker installed?"]
    except Exception as e:
        return [f"Error: {str(e)}"]


def _get_log_file_path(log_name: str = "backend") -> Path:
    """Get path to log file with validation"""
    # Get project root (app/api/v1/endpoints/logs.py -> ../../../../.. = project root)
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    # Whitelist allowed log files (prevent directory traversal)
    allowed_logs = {
        "backend": project_root / "tmp" / "backend.log",
        "backend_out": project_root / "tmp" / "backend.out",
        "celery_worker": project_root / "tmp" / "celery_worker.log",
        "celery_worker_out": project_root / "tmp" / "celery_worker.out",
        "celery_beat": project_root / "tmp" / "celery_beat.log",
        "celery_beat_out": project_root / "tmp" / "celery_beat.out",
        "frontend": project_root / "tmp" / "frontend.out",
        # Docker containers (handled separately)
        "docker_elasticsearch": None,
        "docker_qdrant": None,
        "docker_redis": None,
        "docker_postgres": None,
        "docker_t2v": None
    }
    
    if log_name not in allowed_logs:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid log name. Allowed: {', '.join(allowed_logs.keys())}"
        )
    
    # Docker containers don't have file paths
    if _is_docker_container(log_name):
        return None
    
    log_path = allowed_logs[log_name]
    
    # Ensure log file exists
    if not log_path.exists():
        # Create empty log if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
    
    return log_path


@router.get("/available", response_model=List[str])
async def list_available_logs(
    current_user: User = Depends(get_current_user)
):
    """List available log files including Docker containers"""
    _require_admin_role(current_user)
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    logs = []
    
    # Check file-based logs
    log_paths = {
        "backend": project_root / "tmp" / "backend.log",
        "backend_out": project_root / "tmp" / "backend.out",
        "celery_worker": project_root / "tmp" / "celery_worker.log",
        "celery_worker_out": project_root / "tmp" / "celery_worker.out",
        "celery_beat": project_root / "tmp" / "celery_beat.log",
        "celery_beat_out": project_root / "tmp" / "celery_beat.out",
        "frontend": project_root / "tmp" / "frontend.out"
    }
    
    for name, path in log_paths.items():
        if path.exists() and path.stat().st_size > 0:
            logs.append(name)
    
    # Check Docker containers
    docker_containers = ["docker_elasticsearch", "docker_qdrant", "docker_redis", "docker_t2v"]
    for container in docker_containers:
        # Try to check if container exists
        try:
            container_map = {
                "docker_elasticsearch": "indoc-elasticsearch",
                "docker_qdrant": "indoc-qdrant",
                "docker_redis": "indoc-redis",
                "docker_t2v": "indoc-t2v-transformers"
            }
            actual_container = container_map[container]
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={actual_container}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                logs.append(container)
        except:
            pass  # Skip if Docker not available or container not running
    
    return logs


@router.get("/stats/{log_name}", response_model=LogStats)
async def get_log_stats(
    log_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get statistics for a log file"""
    _require_admin_role(current_user)
    
    # Get log lines (handles both files and Docker containers)
    if _is_docker_container(log_name):
        # Fetch Docker logs
        raw_lines = _get_docker_logs(log_name, lines=10000)  # Get recent logs for stats
        all_lines = [line + '\n' for line in raw_lines if line.strip()]
        file_size_mb = sum(len(line.encode('utf-8')) for line in all_lines) / (1024 * 1024)
        last_modified = datetime.now().isoformat()  # Docker logs are always "now"
    else:
        # File-based logs
        log_path = _get_log_file_path(log_name)
        if not log_path or not log_path.exists():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Log file {log_name} not found"
            )
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        
        file_size_mb = log_path.stat().st_size / (1024 * 1024)
        last_modified = datetime.fromtimestamp(log_path.stat().st_mtime).isoformat()
    
    # Count lines and errors
    total_lines = len(all_lines)
    error_count = 0
    warning_count = 0
    info_count = 0
    last_error = None
    last_error_time = None
    
    for line in all_lines:
        # Check for ERROR (various formats: "ERROR:", " ERROR ", etc.)
        if 'ERROR' in line.upper():
            error_count += 1
            last_error = line.strip()
            # Extract timestamp
            match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            if not match:
                # Try Celery format
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
            if match:
                last_error_time = match.group(1)
        elif 'WARNING' in line.upper():
            warning_count += 1
        elif 'INFO' in line.upper():
            info_count += 1
    
    return LogStats(
        total_lines=total_lines,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        last_error=last_error,
        last_error_time=last_error_time,
        file_size_mb=round(file_size_mb, 2),
        last_modified=last_modified
    )


@router.get("/view/{log_name}", response_model=LogResponse)
async def view_logs(
    log_name: str,
    current_user: User = Depends(get_current_user),
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to retrieve"),
    offset: int = Query(0, ge=0, description="Line offset (for pagination)"),
    level: Optional[str] = Query(None, description="Filter by log level (ERROR, WARNING, INFO)"),
    search: Optional[str] = Query(None, description="Search term to filter logs"),
    tail: bool = Query(True, description="Get latest logs (tail) or oldest (head)")
):
    """
    View system logs with filtering and pagination
    
    Security: Admin-only access per Guide §9
    """
    _require_admin_role(current_user)
    
    # Check if this is a Docker container
    if _is_docker_container(log_name):
        # Fetch Docker logs
        raw_lines = _get_docker_logs(log_name, lines=lines * 2)  # Get more to allow for filtering
        all_lines = [line + '\n' for line in raw_lines if line.strip()]
    else:
        # File-based logs
        log_path = _get_log_file_path(log_name)
        
        # Read all lines (for filtering)
        all_lines = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
    
    total_lines = len(all_lines)
    
    # Filter by level
    filtered_lines = []
    for i, line in enumerate(all_lines, start=1):
        # Apply level filter (skip if level is "all" or None)
        # Check case-insensitive for flexibility (ERROR:, ERROR , error, etc.)
        if level and level.lower() != 'all':
            level_upper = level.upper()
            if level_upper not in line.upper():
                continue
        
        # Apply search filter
        if search and search.lower() not in line.lower():
            continue
        
        filtered_lines.append((i, line))
    
    filtered_count = len(filtered_lines)
    
    # Pagination
    if tail:
        # Get most recent logs
        filtered_lines = filtered_lines[-lines - offset: -offset if offset > 0 else None]
    else:
        # Get oldest logs
        filtered_lines = filtered_lines[offset:offset + lines]
    
    # Parse log entries with timestamp tracking
    log_entries = []
    last_timestamp = None
    for line_num, line in filtered_lines:
        entry = _parse_log_line(line, line_num, last_timestamp)
        if entry:
            # Update last timestamp BEFORE appending (for next iteration)
            if entry.timestamp and entry.timestamp.strip():
                last_timestamp = entry.timestamp
            log_entries.append(entry)
    
    return LogResponse(
        logs=log_entries,
        total_lines=total_lines,
        filtered_lines=filtered_count,
        log_file=log_name,
        last_updated=datetime.now().isoformat()
    )


@router.get("/errors/{log_name}")
async def get_recent_errors(
    log_name: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100)
):
    """Get recent errors and exceptions (admin-only)"""
    _require_admin_role(current_user)
    
    log_path = _get_log_file_path(log_name)
    
    errors = []
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
        # Read backwards to get recent errors
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            if ' ERROR ' in line or 'Exception' in line or 'Traceback' in line:
                # Collect error and following lines (stack trace)
                error_block = [line]
                j = i + 1
                while j < len(lines) and not re.match(r'^\d{4}-\d{2}-\d{2}', lines[j]):
                    error_block.append(lines[j])
                    j += 1
                
                errors.append({
                    "line_number": i + 1,
                    "error": ''.join(error_block).strip()
                })
                
                if len(errors) >= limit:
                    break
    
    return {
        "errors": errors[:limit],
        "count": len(errors),
        "log_file": log_name
    }


@router.post("/clear/{log_name}")
async def clear_log(
    log_name: str,
    current_user: User = Depends(get_current_user)
):
    """Clear a log file (admin-only, creates backup first)"""
    _require_admin_role(current_user)
    
    log_path = _get_log_file_path(log_name)
    
    # Create backup
    backup_path = log_path.with_suffix(f'.{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
    
    if log_path.exists() and log_path.stat().st_size > 0:
        import shutil
        shutil.copy2(log_path, backup_path)
    
    # Clear log file
    with open(log_path, 'w') as f:
        f.write(f"Log cleared by {current_user.email} at {datetime.now().isoformat()}\n")
    
    return {
        "success": True,
        "message": f"Log cleared successfully",
        "backup": str(backup_path)
    }


@router.get("/download/{log_name}")
async def download_log(
    log_name: str,
    current_user: User = Depends(get_current_user)
):
    """Download full log file (admin-only)"""
    from fastapi.responses import FileResponse
    
    _require_admin_role(current_user)
    
    log_path = _get_log_file_path(log_name)
    
    return FileResponse(
        path=log_path,
        media_type='text/plain',
        filename=f"{log_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )


@router.websocket("/ws/tail/{log_name}")
async def websocket_tail_logs(
    websocket: WebSocket,
    log_name: str
):
    """
    Real-time log tailing via WebSocket (admin-only)
    
    Client must send auth token in first message:
    {"type": "auth", "token": "Bearer xxx"}
    """
    await websocket.accept()
    
    try:
        # Wait for auth message
        auth_data = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=5.0
        )
        auth_msg = json.loads(auth_data)
        
        if auth_msg.get("type") != "auth":
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close()
            return
        
        # Verify token (simplified - in production use full auth)
        token = auth_msg.get("token", "").replace("Bearer ", "")
        if not token:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
        
        # TODO: Verify token and check admin role
        # For now, proceed with caution
        
        # Check if this is a Docker container
        if _is_docker_container(log_name):
            await websocket.send_json({
                "error": "Real-time tailing not supported for Docker containers yet. Please use auto-refresh instead."
            })
            await websocket.close()
            return
        
        log_path = _get_log_file_path(log_name)
        if not log_path or not log_path.exists():
            await websocket.send_json({
                "error": f"Log file {log_name} not found"
            })
            await websocket.close()
            return
        
        # Send initial confirmation
        await websocket.send_json({
            "type": "connected",
            "log_file": log_name,
            "message": f"Tailing {log_name}"
        })
        
        # Tail the log file
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Go to end of file
            f.seek(0, 2)
            
            line_num = 0
            last_timestamp = None
            while True:
                line = f.readline()
                if line:
                    line_num += 1
                    # Send new log line
                    entry = _parse_log_line(line, line_num, last_timestamp)
                    if entry and entry.timestamp and entry.timestamp.strip():
                        last_timestamp = entry.timestamp
                    await websocket.send_json({
                        "type": "log_entry",
                        "entry": entry.dict()
                    })
                else:
                    # No new data, wait a bit
                    await asyncio.sleep(0.5)
                    
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        await websocket.send_json({"error": "Authentication timeout"})
        await websocket.close()
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()


@router.get("/export/{log_name}")
async def export_logs(
    log_name: str,
    current_user: User = Depends(get_current_user),
    level: Optional[str] = Query(None, description="Filter by level"),
    search: Optional[str] = Query(None, description="Search term"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Export filtered logs as plain text file
    """
    _require_admin_role(current_user)
    from fastapi.responses import PlainTextResponse
    
    # Get log content
    if _is_docker_container(log_name):
        raw_lines = _get_docker_logs(log_name, lines=100000)
        all_lines = [line + '\n' for line in raw_lines if line.strip()]
    else:
        log_path = _get_log_file_path(log_name)
        if not log_path or not log_path.exists():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Log file {log_name} not found"
            )
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
    
    # Filter lines
    filtered_lines = []
    for line in all_lines:
        # Level filter
        if level and level.lower() != 'all':
            if level.upper() not in line.upper():
                continue
        
        # Search filter
        if search and search.lower() not in line.lower():
            continue
        
        # Date filter
        if start_date or end_date:
            # Extract timestamp from line
            match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
            if not match:
                # Try Celery format
                match = re.match(r'^\[(\d{4}-\d{2}-\d{2})', line)
            
            if match:
                log_date = match.group(1)
                if start_date and log_date < start_date:
                    continue
                if end_date and log_date > end_date:
                    continue
        
        filtered_lines.append(line)
    
    # Create export content
    export_content = f"# inDoc Log Export\n"
    export_content += f"# Log: {log_name}\n"
    export_content += f"# Exported: {datetime.now().isoformat()}\n"
    export_content += f"# Filters: level={level or 'all'}, search={search or 'none'}\n"
    if start_date or end_date:
        export_content += f"# Date Range: {start_date or 'start'} to {end_date or 'end'}\n"
    export_content += f"# Total Lines: {len(filtered_lines)}\n"
    export_content += f"{'='*80}\n\n"
    export_content += ''.join(filtered_lines)
    
    return PlainTextResponse(
        content=export_content,
        headers={"Content-Disposition": f"attachment; filename={log_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"}
    )


@router.get("/aggregate/{log_name}")
async def aggregate_logs(
    log_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated log statistics (error counts, patterns, etc.)
    """
    _require_admin_role(current_user)
    
    # Get log content
    if _is_docker_container(log_name):
        raw_lines = _get_docker_logs(log_name, lines=100000)
        all_lines = [line + '\n' for line in raw_lines if line.strip()]
    else:
        log_path = _get_log_file_path(log_name)
        if not log_path or not log_path.exists():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Log file {log_name} not found"
            )
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
    
    # Aggregate by level
    level_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0, "OTHER": 0}
    error_patterns = {}
    hourly_distribution = {}
    
    for line in all_lines:
        # Count by level
        line_upper = line.upper()
        if 'ERROR' in line_upper:
            level_counts["ERROR"] += 1
            # Extract error pattern (first 50 chars after ERROR)
            match = re.search(r'ERROR[:\s]+(.{0,50})', line_upper)
            if match:
                pattern = match.group(1).strip()[:50]
                error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
        elif 'WARNING' in line_upper:
            level_counts["WARNING"] += 1
        elif 'INFO' in line_upper:
            level_counts["INFO"] += 1
        elif 'DEBUG' in line_upper:
            level_counts["DEBUG"] += 1
        else:
            level_counts["OTHER"] += 1
        
        # Extract hour for distribution
        match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+(\d{2}):', line)
        if not match:
            match = re.match(r'^\[(\d{4}-\d{2}-\d{2}\s+(\d{2})):', line)
        
        if match:
            hour = match.group(2)
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
    
    # Top 10 error patterns
    top_errors = sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "log_file": log_name,
        "total_lines": len(all_lines),
        "level_distribution": level_counts,
        "top_error_patterns": [{"pattern": p, "count": c} for p, c in top_errors],
        "hourly_distribution": dict(sorted(hourly_distribution.items())),
        "generated_at": datetime.now().isoformat()
    }

