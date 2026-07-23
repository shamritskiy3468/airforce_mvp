from __future__ import annotations

import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, parse, request


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"


def ch_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


class ClickHouseClient:
    def __init__(self, base_url: str, database: str, user: str, password: str):
        self._base_url = base_url.rstrip("/")
        self._database = database
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Basic {token}"

    def query_json_each_row(self, sql: str) -> list[dict[str, Any]]:
        req = request.Request(
            url=f"{self._base_url}/?database={parse.quote(self._database)}&query={parse.quote(sql)}",
            method="GET",
            headers={"Authorization": self._auth_header},
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ClickHouse HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"ClickHouse connection error: {exc.reason}") from exc

        rows = []
        for line in body.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows


class ReplayHandler(BaseHTTPRequestHandler):
    clickhouse: ClickHouseClient
    table: str

    def do_GET(self) -> None:
        parsed = parse.urlparse(self.path)
        try:
            if parsed.path == "/":
                self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            elif parsed.path.startswith("/static/"):
                self._send_static(parsed.path.removeprefix("/static/"))
            elif parsed.path == "/api/health":
                self._send_json({"status": "ok"})
            elif parsed.path == "/api/runs":
                self._handle_runs(parsed.query)
            elif parsed.path == "/api/replay":
                self._handle_replay(parsed.query)
            else:
                self._send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, fmt: str, *args) -> None:
        print(f"http | {self.address_string()} | {fmt % args}")

    def _handle_runs(self, query: str) -> None:
        params = parse.parse_qs(query)
        limit = self._clamp_int(params.get("limit", ["50"])[0], default=50, minimum=1, maximum=200)
        sql = f"""
            SELECT
                run_id,
                count() AS events,
                uniqExact(object_id) AS objects,
                min(event_time) AS min_event_time,
                max(event_time) AS max_event_time
            FROM {self.table}
            GROUP BY run_id
            ORDER BY max_event_time DESC
            LIMIT {limit}
            FORMAT JSONEachRow
        """
        self._send_json({"runs": self.clickhouse.query_json_each_row(sql)})

    def _handle_replay(self, query: str) -> None:
        params = parse.parse_qs(query)
        from_time = self._required(params, "from")
        to_time = self._required(params, "to")
        run_id = params.get("run_id", [""])[0].strip()
        limit = self._clamp_int(
            params.get("limit", ["50000"])[0],
            default=50000,
            minimum=1,
            maximum=200000,
        )

        conditions = [
            f"e.event_time >= parseDateTime64BestEffort({ch_quote(from_time)}, 3, 'UTC')",
            f"e.event_time <= parseDateTime64BestEffort({ch_quote(to_time)}, 3, 'UTC')",
        ]
        if run_id:
            conditions.append(f"e.run_id = {ch_quote(run_id)}")

        sql = f"""
            SELECT
                formatDateTime(e.event_time, '%Y-%m-%dT%H:%i:%S.%fZ') AS event_time,
                event_type,
                run_id,
                object_id,
                scenario_bucket,
                platform_class,
                mission_profile,
                truth_affiliation,
                cooperation_status,
                callsign,
                flight_category,
                origin_label,
                destination_label,
                flight_state,
                lat,
                lon,
                altitude,
                heading,
                speed,
                despawn_reason
            FROM {self.table} AS e
            WHERE {' AND '.join(conditions)}
            ORDER BY e.event_time ASC, object_id ASC
            LIMIT {limit}
            FORMAT JSONEachRow
        """
        rows = self.clickhouse.query_json_each_row(sql)
        self._send_json({"events": rows, "count": len(rows), "limit": limit})

    @staticmethod
    def _required(params: dict[str, list[str]], key: str) -> str:
        value = params.get(key, [""])[0].strip()
        if not value:
            raise ValueError(f"Missing required query param: {key}")
        return value

    @staticmethod
    def _clamp_int(raw: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(raw)
        except ValueError:
            value = default
        return max(minimum, min(maximum, value))

    def _send_static(self, rel_path: str) -> None:
        path = (STATIC_DIR / rel_path).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())) or not path.exists():
            self._send_json({"error": "not found"}, status=404)
            return

        content_type = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".html": "text/html; charset=utf-8",
        }.get(path.suffix, "application/octet-stream")
        self._send_file(path, content_type)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local airspace replay map over ClickHouse.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--clickhouse-url", default="http://localhost:8123")
    parser.add_argument("--clickhouse-database", default="airforce")
    parser.add_argument("--clickhouse-table", default="airforce.truth_events_raw")
    parser.add_argument("--clickhouse-user", default="airforce")
    parser.add_argument("--clickhouse-password", default="airforce_pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ReplayHandler.clickhouse = ClickHouseClient(
        base_url=args.clickhouse_url,
        database=args.clickhouse_database,
        user=args.clickhouse_user,
        password=args.clickhouse_password,
    )
    ReplayHandler.table = args.clickhouse_table

    server = ThreadingHTTPServer((args.host, args.port), ReplayHandler)
    print(f"airspace replay | url=http://{args.host}:{args.port}")
    print(f"clickhouse | url={args.clickhouse_url} | table={args.clickhouse_table}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutdown")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
