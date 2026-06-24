import io
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.event import eventmanager, Event
from app.helper.mediaserver import MediaServerHelper
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None


@dataclass
class SeriesStatusResult:
    item_id: str
    title: str
    year: Optional[str]
    status: str
    reason: str
    updated_tag: bool = False
    updated_poster: bool = False


class SeriesStatusBadge(_PluginBase):
    plugin_name = "媒体库完结/追更角标"
    plugin_desc = "连接 Emby 自动读取媒体库文件，判断剧集是否完结，并在封面显示完结/追更或写入标签。"
    plugin_icon = "Emby_A.png"
    plugin_version = "1.1.0"
    plugin_author = "OpenClaw"
    author_url = "https://github.com/openclaw/openclaw"
    plugin_config_prefix = "seriesstatusbadge_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
    _only_libraries: List[str] = []
    _exclude_libraries: List[str] = []
    _apply_tag = True
    _apply_overlay = False
    _overlay_completed_text = "完结"
    _overlay_updating_text = "追更"
    _tag_completed = "完结"
    _tag_updating = "追更"
    _skip_if_tag_exists = False
    _force_rebuild_overlay = False
    _cron = "0 3 * * *"
    _last_summary: List[Dict[str, Any]] = []

    def init_plugin(self, config: dict = None):
        config = config or {}
        self._enabled = bool(config.get("enabled", False))
        self._only_libraries = config.get("only_libraries") or []
        self._exclude_libraries = config.get("exclude_libraries") or []
        self._apply_tag = bool(config.get("apply_tag", True))
        self._apply_overlay = bool(config.get("apply_overlay", False))
        self._overlay_completed_text = config.get("overlay_completed_text") or "完结"
        self._overlay_updating_text = config.get("overlay_updating_text") or "追更"
        self._tag_completed = config.get("tag_completed") or "完结"
        self._tag_updating = config.get("tag_updating") or "追更"
        self._skip_if_tag_exists = bool(config.get("skip_if_tag_exists", False))
        self._force_rebuild_overlay = bool(config.get("force_rebuild_overlay", False))
        self._cron = config.get("cron") or "0 3 * * *"

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return [
            {
                "cmd": "/series_status_badge_run",
                "event": EventType.PluginAction,
                "desc": "扫描 Emby 剧集完结状态",
                "category": "媒体服务",
                "data": {"action": "series_status_badge_run"},
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/run",
                "endpoint": self.api_run,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "执行 Emby 剧集状态扫描",
                "description": "扫描 Emby 中的电视剧并写入完结/追更状态。",
            },
            {
                "path": "/summary",
                "endpoint": self.api_summary,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取最近一次扫描摘要",
                "description": "返回最近一次扫描的结果摘要。",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        libraries = []
        try:
            for config in MediaServerHelper().get_configs().values():
                if getattr(config, "type", None) == "emby":
                    libraries.append({"title": config.name, "value": config.name})
                else:
                    libraries.append({"title": config.name, "value": config.name})
        except Exception:
            libraries = []

        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "apply_tag",
                                            "label": "写入标签",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "apply_overlay",
                                            "label": "覆盖海报角标",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "tag_completed",
                                            "label": "完结标签",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "tag_updating",
                                            "label": "追更标签",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "skip_if_tag_exists",
                                            "label": "已有状态标签时跳过",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "force_rebuild_overlay",
                                            "label": "每次重建海报角标",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "props": {"show": "{{apply_overlay}}"},
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "overlay_completed_text",
                                            "label": "完结角标文字",
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "overlay_updating_text",
                                            "label": "追更角标文字",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "cron",
                                            "label": "定时 CRON",
                                            "placeholder": "0 3 * * *",
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "warning",
                                            "variant": "tonal",
                                            "text": "Emby 原生并没有通用的自定义右上角角标位。若想稳定看到角标，请开启“覆盖海报角标”，插件会直接改写海报图。",
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "apply_tag": True,
            "apply_overlay": False,
            "tag_completed": "完结",
            "tag_updating": "追更",
            "skip_if_tag_exists": False,
            "force_rebuild_overlay": False,
            "overlay_completed_text": "完结",
            "overlay_updating_text": "追更",
            "cron": "0 3 * * *",
        }

    def get_page(self) -> List[dict]:
        summary_text = "尚未执行扫描" if not self._last_summary else json.dumps(self._last_summary[:20], ensure_ascii=False, indent=2)
        return [
            {
                "component": "VCard",
                "props": {"variant": "tonal"},
                "content": [
                    {
                        "component": "VCardText",
                        "text": summary_text,
                    }
                ],
            }
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        try:
            from apscheduler.triggers.cron import CronTrigger
        except Exception:
            return []
        if not self._enabled:
            return []
        return [
            {
                "id": f"{self.__class__.__name__}.scan",
                "name": "扫描 Emby 剧集完结状态",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.run_scan,
                "kwargs": {},
            }
        ]

    @eventmanager.register(EventType.PluginAction)
    def run_command(self, event: Event):
        event_data = event.event_data or {}
        if event_data.get("action") != "series_status_badge_run":
            return
        self.run_scan()

    def api_run(self):
        results = self.run_scan()
        return {"success": True, "count": len(results), "items": [r.__dict__ for r in results]}

    def api_summary(self):
        return {"success": True, "items": self._last_summary}

    def run_scan(self) -> List[SeriesStatusResult]:
        if not self._enabled:
            logger.info("剧集完结角标插件未启用，跳过扫描")
            return []

        services = MediaServerHelper().get_services(type_filter="emby")
        if not services:
            logger.warning("未找到可用的 Emby 媒体服务")
            return []

        results: List[SeriesStatusResult] = []
        for service_name, service_info in services.items():
            try:
                service = service_info.instance
                if getattr(service, "is_inactive", lambda: False)():
                    logger.warning(f"Emby 服务未连接：{service_name}")
                    continue
                results.extend(self._scan_service(service))
            except Exception as exc:
                logger.exception(f"扫描 Emby 服务失败 {service_name}: {exc}")

        self._last_summary = [r.__dict__ for r in results[:200]]
        if results:
            self.save_data("last_summary", self._last_summary)
        return results

    def _scan_service(self, service) -> List[SeriesStatusResult]:
        libraries = service.get_librarys() or []
        results: List[SeriesStatusResult] = []
        for library in libraries:
            if getattr(library, "type", None) != "tv":
                continue
            library_name = getattr(library, "name", None)
            if self._only_libraries and library_name not in self._only_libraries:
                continue
            if self._exclude_libraries and library_name in self._exclude_libraries:
                continue
            for item in service.get_items(getattr(library, "id", None)):
                if not item:
                    continue
                if getattr(item, "item_type", None) != "Series":
                    continue
                result = self._process_series(service, item)
                if result:
                    results.append(result)
        return results

    def _process_series(self, service, item) -> Optional[SeriesStatusResult]:
        item_id = getattr(item, "item_id", None) or getattr(item, "id", None)
        if not item_id:
            return None
        detail = self._fetch_item_json(service, item_id)
        if not detail:
            return None

        status, reason = self._detect_series_status(service, item_id, detail)
        result = SeriesStatusResult(
            item_id=str(item_id),
            title=detail.get("Name") or getattr(item, "title", "未知剧集"),
            year=str(detail.get("ProductionYear") or getattr(item, "year", "") or "") or None,
            status=status,
            reason=reason,
        )

        if self._skip_if_tag_exists and self._has_status_tag(detail):
            logger.info(f"剧集 {result.title} 已存在状态标签，按配置跳过写入")
            return result

        if self._apply_tag:
            result.updated_tag = self._apply_tags(service, item_id, detail, status)
        if self._apply_overlay:
            result.updated_poster = self._apply_poster_overlay(service, item_id, status, detail)
        logger.info(f"剧集状态扫描: {result.title} => {result.status} ({result.reason})")
        return result

    def _detect_series_status(self, service, item_id: str, detail: Dict[str, Any]) -> Tuple[str, str]:
        status_value = (detail.get("Status") or "").strip().lower()
        if status_value in {"ended", "cancelled"}:
            return "completed", f"Emby/元数据状态为 {detail.get('Status')}"
        if status_value in {"continuing", "returning series", "planned", "pilot", "in production"}:
            return "updating", f"Emby/元数据状态为 {detail.get('Status')}"

        seasons = service.get_tv_episodes(item_id=item_id)[1] if hasattr(service, "get_tv_episodes") else None
        total_episodes = sum(len(v or []) for v in (seasons or {}).values())
        season_count = len(seasons or {})

        if detail.get("EndDate"):
            return "completed", "存在 EndDate，判定为完结"

        airs_days = detail.get("AirsDays")
        if isinstance(airs_days, list) and len(airs_days) == 0 and total_episodes > 0:
            return "completed", "AirsDays 为空且已有剧集，判定为完结"

        if total_episodes <= 0:
            return "updating", "未读取到剧集信息，按追更处理"

        return "updating", f"已收录 {season_count} 季 {total_episodes} 集，未发现完结信号"

    def _apply_tags(self, service, item_id: str, detail: Dict[str, Any], status: str) -> bool:
        current_tags = [tag.get("Name") for tag in (detail.get("TagItems") or []) if isinstance(tag, dict) and tag.get("Name")]
        want = self._tag_completed if status == "completed" else self._tag_updating
        remove = self._tag_updating if status == "completed" else self._tag_completed
        new_tags = [tag for tag in current_tags if tag != remove]
        if want not in new_tags:
            new_tags.append(want)
        if new_tags == current_tags:
            return False

        payload = dict(detail)
        payload["Tags"] = new_tags
        payload.setdefault("ProviderIds", detail.get("ProviderIds") or {})

        res = service.post_data(
            url="[HOST]Items/[ITEMID]?api_key=[APIKEY]".replace("[ITEMID]", str(item_id)),
            data=json.dumps(payload, ensure_ascii=False),
            headers={"Content-Type": "application/json"},
        )
        return bool(res and getattr(res, "status_code", 500) < 300)

    def _has_status_tag(self, detail: Dict[str, Any]) -> bool:
        current_tags = [tag.get("Name") for tag in (detail.get("TagItems") or []) if isinstance(tag, dict) and tag.get("Name")]
        return self._tag_completed in current_tags or self._tag_updating in current_tags

    def _apply_poster_overlay(self, service, item_id: str, status: str, detail: Optional[Dict[str, Any]] = None) -> bool:
        if Image is None:
            logger.warning("Pillow 不可用，无法绘制海报角标")
            return False

        image_res = service.get_data(url="[HOST]Items/[ITEMID]/Images/Primary?api_key=[APIKEY]".replace("[ITEMID]", str(item_id)))
        if not image_res or getattr(image_res, "status_code", 500) >= 300:
            return False

        try:
            if not self._force_rebuild_overlay and self._overlay_already_matches(detail or {}, status):
                return False

            image = Image.open(io.BytesIO(image_res.content)).convert("RGBA")
            draw = ImageDraw.Draw(image)
            w, h = image.size
            text = self._overlay_completed_text if status == "completed" else self._overlay_updating_text
            bg = (220, 20, 60, 235) if status == "completed" else (255, 140, 0, 235)
            font_size = max(24, int(min(w, h) * 0.08))
            try:
                font = ImageFont.truetype("msyh.ttc", font_size)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            pad_x = max(12, int(font_size * 0.45))
            pad_y = max(8, int(font_size * 0.28))
            x2 = w - max(18, int(w * 0.03))
            y1 = max(18, int(h * 0.03))
            x1 = x2 - tw - pad_x * 2
            y2 = y1 + th + pad_y * 2
            draw.rounded_rectangle((x1, y1, x2, y2), radius=max(10, int(font_size * 0.35)), fill=bg)
            draw.text((x1 + pad_x, y1 + pad_y - 2), text, font=font, fill=(255, 255, 255, 255))
            out = io.BytesIO()
            image.convert("RGB").save(out, format="JPEG", quality=95)
            out.seek(0)
            res = service.post_data(
                url="[HOST]Items/[ITEMID]/Images/Primary?api_key=[APIKEY]".replace("[ITEMID]", str(item_id)),
                data=out.getvalue(),
                headers={"Content-Type": "image/jpeg"},
            )
            return bool(res and getattr(res, "status_code", 500) < 300)
        except Exception as exc:
            logger.exception(f"绘制海报角标失败: {exc}")
            return False

    def _overlay_already_matches(self, detail: Dict[str, Any], status: str) -> bool:
        current_tags = [tag.get("Name") for tag in (detail.get("TagItems") or []) if isinstance(tag, dict) and tag.get("Name")]
        expected_tag = self._tag_completed if status == "completed" else self._tag_updating
        return expected_tag in current_tags and not self._force_rebuild_overlay

    def _fetch_item_json(self, service, item_id: str) -> Optional[Dict[str, Any]]:
        res = service.get_data(url="[HOST]Users/[USER]/Items/[ITEMID]?Fields=ProviderIds,TagItems,Overview,OriginalTitle,CommunityRating,PremiereDate,ProductionYear,Status,EndDate,AirsDays,ForcedSortName,OfficialRating&api_key=[APIKEY]".replace("[ITEMID]", str(item_id)))
        if not res or getattr(res, "status_code", 500) >= 300:
            return None
        try:
            return res.json()
        except Exception:
            return None

    def stop_service(self):
        pass
