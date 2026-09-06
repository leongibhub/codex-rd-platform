"""Read-only, bounded pagination for public lifecycle collections.

The collection name is selected from a fixed mapping, never interpolated from
caller input.  Cursors carry only an opaque, collection/project-bound rowid.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

from .lifecycle import LifecycleService
from .lifecycle_store import TABLES
from .store import Store


COLLECTIONS = frozenset(name for name in TABLES if name != "projects")
_CURSOR_PREFIX = "lc1."
_CURSOR_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
_MAX_CURSOR_LENGTH = 1024
_MAX_SQLITE_ROWID = 2 ** 63 - 1


class LifecycleCollectionQuery:
    """Public lifecycle rows with stable SQLite-rowid keyset pagination."""

    def read(self, connection, project_id: str, collection: str, *, limit: int = 200, after_cursor: str | None = None) -> dict[str, Any]:
        service = LifecycleService()
        service.text(project_id, "project_id")
        if not isinstance(collection, str) or collection not in COLLECTIONS:
            raise ValueError("invalid lifecycle collection")
        service.integer(limit, "limit", 1, 500)
        after = self._decode_cursor(after_cursor, project_id, collection)
        service.project(connection, project_id)

        rows = list(connection.execute(
            f"SELECT rowid, id, data, status FROM lc_{collection} WHERE project_id=? AND rowid>? ORDER BY rowid LIMIT ?",
            (project_id, after, limit + 1),
        ))
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = self._public_items(service, connection, project_id, collection, rows)
        return {
            "schema_version": "lifecycle-collection-v1",
            "project_id": project_id,
            "collection": collection,
            "items": items,
            "total": connection.execute(f"SELECT COUNT(*) FROM lc_{collection} WHERE project_id=?", (project_id,)).fetchone()[0],
            "next_cursor": self._encode_cursor(project_id, collection, rows[-1][0]) if has_more and rows else None,
            "has_more": has_more,
        }

    def _public_items(self, service, connection, project_id, collection, rows):
        projected = {row["id"]: Store.loads(row["data"]) for row in rows}
        if collection == "work_orders":
            projected = {ident: service.public_work(item) for ident, item in projected.items()}
        elif collection == "gates":
            projected = {item["id"]: item for item in service.project_gates(connection, project_id)["gates"]}
        elif collection == "gate_assessments":
            stale = service.project_gates(connection, project_id)["stale_assessment_ids"]
            for item in projected.values():
                if item["id"] in stale:
                    item["status"] = "SUPERSEDED"
                    item["freshness"] = "STALE"
        for item in projected.values():
            # Lease and release digests are internal capability/integrity
            # material, never public collection fields.
            item.pop("lease_digest", None)
            item.pop("release_digest", None)
        return [service.redact_projection(projected[row["id"]]) for row in rows]

    @staticmethod
    def _encode_cursor(project_id: str, collection: str, rowid: int) -> str:
        raw = Store.dumps({"v": 1, "project_id": project_id, "collection": collection, "after": rowid}).encode("utf-8")
        return _CURSOR_PREFIX + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str | None, project_id: str, collection: str) -> int:
        if cursor is None:
            return 0
        if not isinstance(cursor, str) or len(cursor) > _MAX_CURSOR_LENGTH or not cursor.startswith(_CURSOR_PREFIX):
            raise ValueError("invalid lifecycle cursor")
        encoded = cursor[len(_CURSOR_PREFIX):]
        if not encoded or _CURSOR_PATTERN.fullmatch(encoded) is None:
            raise ValueError("invalid lifecycle cursor")
        try:
            decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8")
            data = Store.loads(decoded)
        except (binascii.Error, RecursionError, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("invalid lifecycle cursor") from exc
        if (not isinstance(data, dict) or set(data) != {"v", "project_id", "collection", "after"} or type(data.get("v")) is not int or data["v"] != 1 or data.get("project_id") != project_id
                or data.get("collection") != collection or type(data.get("after")) is not int or data["after"] < 0):
            raise ValueError("invalid lifecycle cursor")
        if data["after"] > _MAX_SQLITE_ROWID:
            raise ValueError("invalid lifecycle cursor")
        return data["after"]
