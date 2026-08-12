"""
Live ops monitoring snapshot for the inDoc Monitoring console.
Pulls Prometheus when available and always includes local host/process gauges.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


def _require_ops(user: User) -> None:
    role = getattr(user.role, "value", user.role)
    if role not in {"Admin", "Manager"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can access monitoring",
        )


def _scalar(result: Dict[str, Any]) -> Optional[float]:
    rows = (result.get("data") or {}).get("result") or []
    if not rows:
        return None
    try:
        return float(rows[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _range_points(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = (result.get("data") or {}).get("result") or []
    if not rows:
        return []
    out: List[Dict[str, Any]] = []
    for ts, val in rows[0].get("values") or []:
        try:
            out.append(
                {
                    "t": int(float(ts)),
                    "v": float(val),
                    "label": datetime.fromtimestamp(float(ts), tz=timezone.utc)
                    .astimezone()
                    .strftime("%H:%M"),
                }
            )
        except (TypeError, ValueError):
            continue
    return out


def _vector_table(result: Dict[str, Any], label_keys: Tuple[str, ...]) -> List[Dict[str, Any]]:
    rows = (result.get("data") or {}).get("result") or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        metric = row.get("metric") or {}
        try:
            value = float(row["value"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        item = {k: metric.get(k, "") for k in label_keys}
        item["value"] = value
        out.append(item)
    out.sort(key=lambda r: r["value"], reverse=True)
    return out


async def _prom_get(client: httpx.AsyncClient, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    resp = await client.get(path, params=params)
    resp.raise_for_status()
    return resp.json()


async def _query_prometheus(window_seconds: int = 1800) -> Tuple[Dict[str, Any], List[str]]:
    """Return prometheus-derived snapshot fields and a list of warnings."""
    warnings: List[str] = []
    base = settings.PROMETHEUS_URL.rstrip("/")
    end = int(time.time())
    start = end - window_seconds
    step = max(15, window_seconds // 60)

    async with httpx.AsyncClient(base_url=base, timeout=4.0) as client:
        try:
            await client.get("/-/ready")
        except Exception as exc:
            warnings.append(f"prometheus_unreachable: {exc}")
            return {}, warnings

        async def q(expr: str) -> Dict[str, Any]:
            return await _prom_get(client, "/api/v1/query", {"query": expr})

        async def qr(expr: str) -> Dict[str, Any]:
            return await _prom_get(
                client,
                "/api/v1/query_range",
                {"query": expr, "start": start, "end": end, "step": step},
            )

        try:
            req_rate = _scalar(await q('sum(rate(http_requests_total{endpoint!="/api/v1/metrics"}[5m]))'))
            err_rate = _scalar(
                await q('sum(rate(http_requests_total{status=~"5..",endpoint!="/api/v1/metrics"}[5m]))')
            ) or 0.0
            success_rate = None
            if req_rate is not None and req_rate > 0:
                success_rate = max(0.0, min(100.0, (1.0 - (err_rate / req_rate)) * 100.0))
            elif req_rate == 0:
                success_rate = 100.0

            latency_s = _scalar(
                await q(
                    'sum(rate(http_request_duration_seconds_sum{endpoint!="/api/v1/metrics"}[5m]))'
                    ' / clamp_min(sum(rate(http_request_duration_seconds_count{endpoint!="/api/v1/metrics"}[5m])), 1e-9)'
                )
            )
            p95_s = _scalar(
                await q(
                    'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{endpoint!="/api/v1/metrics"}[5m])) by (le))'
                )
            )

            cpu = _scalar(await q("system_cpu_usage_percent"))
            mem_pct = _scalar(await q("system_memory_usage_percent"))
            mem_bytes = _scalar(await q("system_memory_usage_bytes"))
            proc_rss = _scalar(await q("indoc_process_resident_memory_bytes"))
            if proc_rss is None:
                proc_rss = _scalar(await q("process_resident_memory_bytes"))
            disk_pct = _scalar(await q('system_disk_usage_percent{path="/"}'))
            websockets = _scalar(await q("websocket_active_connections"))
            backend_up = _scalar(await q('up{job="indoc-backend"}'))
            workers_online = _scalar(await q("sum(flower_worker_online)"))
            tasks_running = _scalar(await q("sum(flower_worker_number_of_currently_executing_tasks)"))

            top_endpoints = _vector_table(
                await q('topk(8, sum by (endpoint, method) (increase(http_requests_total{endpoint!="/api/v1/metrics"}[1h])))'),
                ("endpoint", "method"),
            )
            status_codes = _vector_table(
                await q('sum by (status) (increase(http_requests_total{endpoint!="/api/v1/metrics"}[1h]))'),
                ("status",),
            )

            req_series = _range_points(
                await qr('sum(rate(http_requests_total{endpoint!="/api/v1/metrics"}[1m]))')
            )
            err_series = _range_points(
                await qr('sum(rate(http_requests_total{status=~"5..",endpoint!="/api/v1/metrics"}[1m]))')
            )
            lat_series = _range_points(
                await qr(
                    'sum(rate(http_request_duration_seconds_sum{endpoint!="/api/v1/metrics"}[1m]))'
                    ' / clamp_min(sum(rate(http_request_duration_seconds_count{endpoint!="/api/v1/metrics"}[1m])), 1e-9)'
                )
            )
            cpu_series = _range_points(await qr("system_cpu_usage_percent"))

            return {
                "request_rate_rps": req_rate,
                "error_rate_rps": err_rate,
                "success_rate_pct": success_rate,
                "latency_avg_ms": (latency_s * 1000.0) if latency_s is not None else None,
                "latency_p95_ms": (p95_s * 1000.0) if p95_s is not None else None,
                "cpu_pct": cpu,
                "memory_pct": mem_pct,
                "memory_used_bytes": mem_bytes,
                "process_rss_bytes": proc_rss,
                "disk_pct": disk_pct,
                "websockets": websockets,
                "backend_up": backend_up == 1.0 if backend_up is not None else None,
                "celery_workers_online": workers_online,
                "celery_tasks_running": tasks_running,
                "top_endpoints": top_endpoints,
                "status_codes": status_codes,
                "series": {
                    "request_rate": req_series,
                    "error_rate": err_series,
                    "latency_s": lat_series,
                    "cpu": cpu_series,
                },
            }, warnings
        except Exception as exc:
            warnings.append(f"prometheus_query_failed: {exc}")
            return {}, warnings


def _local_host_gauges() -> Dict[str, Any]:
    try:
        import psutil

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        proc = psutil.Process()
        return {
            "cpu_pct": psutil.cpu_percent(interval=None),
            "memory_pct": mem.percent,
            "memory_used_bytes": mem.used,
            "memory_total_bytes": mem.total,
            "disk_pct": disk.percent,
            "disk_used_bytes": disk.used,
            "disk_total_bytes": disk.total,
            "process_rss_bytes": proc.memory_info().rss,
            "process_cpu_pct": proc.cpu_percent(interval=None),
        }
    except Exception:
        return {}


async def _dependency_health() -> Dict[str, Any]:
    """Lightweight dependency probe — same surface as settings health."""
    from sqlalchemy import text
    from app.db.session import async_engine

    deps: Dict[str, str] = {
        "database": "unknown",
        "elasticsearch": "unknown",
        "qdrant": "unknown",
        "redis": "unknown",
        "ollama": "unknown",
        "prometheus": "unknown",
    }

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        deps["database"] = "healthy"
    except Exception as exc:
        deps["database"] = f"unhealthy: {exc}"

    async with httpx.AsyncClient(timeout=2.5) as client:
        try:
            r = await client.get(f"{settings.ELASTICSEARCH_URL}/_cluster/health")
            deps["elasticsearch"] = "healthy" if r.status_code == 200 else f"unhealthy: {r.status_code}"
        except Exception as exc:
            deps["elasticsearch"] = f"unhealthy: {exc}"

        try:
            r = await client.get(f"{settings.QDRANT_URL}/readyz")
            if r.status_code != 200:
                r = await client.get(f"{settings.QDRANT_URL}/healthz")
            deps["qdrant"] = "healthy" if r.status_code == 200 else f"unhealthy: {r.status_code}"
        except Exception as exc:
            deps["qdrant"] = f"unhealthy: {exc}"

        try:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            deps["ollama"] = "healthy" if r.status_code == 200 else f"unhealthy: {r.status_code}"
        except Exception as exc:
            deps["ollama"] = f"unhealthy: {exc}"

        try:
            r = await client.get(f"{settings.PROMETHEUS_URL.rstrip('/')}/-/ready")
            deps["prometheus"] = "healthy" if r.status_code == 200 else f"unhealthy: {r.status_code}"
        except Exception as exc:
            deps["prometheus"] = f"unhealthy: {exc}"

    try:
        import redis.asyncio as redis

        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        deps["redis"] = "healthy"
        await r.close()
    except Exception as exc:
        deps["redis"] = f"unhealthy: {exc}"

    healthy = sum(1 for v in deps.values() if v == "healthy")
    overall = "healthy" if healthy == len(deps) else ("degraded" if healthy > 0 else "down")
    return {"overall": overall, "healthy": healthy, "total": len(deps), "dependencies": deps}


@router.get("/snapshot")
async def monitoring_snapshot(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Real-time ops snapshot for the Monitoring console.
    Combines Prometheus time series with local host gauges and dependency probes.
    """
    _require_ops(current_user)

    prom, warnings = await _query_prometheus(window_seconds=1800)
    local = _local_host_gauges()
    deps = await _dependency_health()

    # Prefer Prometheus when present; fall back to local host samples.
    def pick(*keys: str, default: Any = None) -> Any:
        for key in keys:
            if prom.get(key) is not None:
                return prom[key]
            if local.get(key) is not None:
                return local[key]
        return default

    cpu = pick("cpu_pct", default=0.0)
    mem_pct = pick("memory_pct", default=0.0)
    backend_up = prom.get("backend_up")
    if backend_up is None:
        backend_up = True

    overall = deps["overall"]
    if not backend_up:
        overall = "down"
    elif (prom.get("error_rate_rps") or 0) > 0.05 or (prom.get("latency_p95_ms") or 0) > 2000:
        if overall == "healthy":
            overall = "degraded"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "grafana_url": settings.GRAFANA_URL.rstrip("/"),
        "prometheus_url": settings.PROMETHEUS_URL.rstrip("/"),
        "warnings": warnings,
        "gauges": {
            "backend_up": backend_up,
            "cpu_pct": cpu,
            "memory_pct": mem_pct,
            "memory_used_bytes": pick("memory_used_bytes"),
            "memory_total_bytes": local.get("memory_total_bytes"),
            "disk_pct": pick("disk_pct"),
            "disk_used_bytes": local.get("disk_used_bytes"),
            "disk_total_bytes": local.get("disk_total_bytes"),
            "process_rss_bytes": pick("process_rss_bytes"),
            "process_cpu_pct": local.get("process_cpu_pct"),
            "request_rate_rps": prom.get("request_rate_rps") or 0.0,
            "error_rate_rps": prom.get("error_rate_rps") or 0.0,
            "success_rate_pct": prom.get("success_rate_pct"),
            "latency_avg_ms": prom.get("latency_avg_ms"),
            "latency_p95_ms": prom.get("latency_p95_ms"),
            "websockets": prom.get("websockets") or 0,
            "celery_workers_online": prom.get("celery_workers_online") or 0,
            "celery_tasks_running": prom.get("celery_tasks_running") or 0,
        },
        "dependencies": deps,
        "top_endpoints": prom.get("top_endpoints") or [],
        "status_codes": prom.get("status_codes") or [],
        "series": prom.get("series")
        or {"request_rate": [], "error_rate": [], "latency_s": [], "cpu": []},
    }
