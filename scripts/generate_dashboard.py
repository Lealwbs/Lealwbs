#!/usr/bin/env python3
"""Generate ONE unified Gemini-themed profile SVG (profile/readme-{dark,light}.svg)
with rotating Hero pill, Gemini twinkling sparkles, 14x2 full-bleed Tech Stack,
animated Pac-Man graph, Overview (leadership/networks + NSG), GitHub Activity + Streaks,
30d Waveform, Commit Schedule, Recent Repos, and filtered WakaTime programming languages."""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "profile"
ASSETS_DIR = ROOT / "assets"
OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "Lealwbs")
BRT = dt.timezone(dt.timedelta(hours=-3))

THEMES = {
    "dark": {
        "bg": "#131314",
        "card": "#1e1f20",
        "border": "#333537",
        "border_soft": "#282a2c",
        "text": "#e3e3e3",
        "subtext": "#c4c7c5",
        "muted": "#9aa0a6",
        "faint": "#75787b",
        "accent": "#8ab4f8",
        "accent_pill_text": "#a8c7fa",
        "accent_strong": "#4285f4",
        "accent_violet": "#9b72cb",
        "accent_rose": "#d96570",
        "accent_cyan": "#39c5cf",
        "accent_soft": "#1a2638",
        "accent_border": "#8ab4f844",
        "bar_muted": "#2d2f31",
        "wave_top": "#4285f4",
        "wave_bot": "#131314",
        "dot_ring": "#131314",
        "glow1": "#4285f4",
        "glow2": "#9b72cb",
        "name_start": "#e3e3e3",
        "name_mid": "#c2d7fa",
        "name_end": "#a8c7fa",
    },
    "light": {
        "bg": "#f8fafd",
        "card": "#ffffff",
        "border": "#dde3ea",
        "border_soft": "#e8edf3",
        "text": "#1f1f1f",
        "subtext": "#444746",
        "muted": "#5f6368",
        "faint": "#747775",
        "accent": "#1a73e8",
        "accent_pill_text": "#0b57d0",
        "accent_strong": "#1a73e8",
        "accent_violet": "#8430ce",
        "accent_rose": "#d96570",
        "accent_cyan": "#00838f",
        "accent_soft": "#e8f0fe",
        "accent_border": "#1a73e844",
        "bar_muted": "#e1e5ea",
        "wave_top": "#1a73e8",
        "wave_bot": "#f8fafd",
        "dot_ring": "#f8fafd",
        "glow1": "#1a73e8",
        "glow2": "#8430ce",
        "name_start": "#1f1f1f",
        "name_mid": "#0b57d0",
        "name_end": "#1a73e8",
    },
}

SANS = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
MONO = "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"

# Filter WakaTime noise so only true programming / query / systems languages show prominently
EXCLUDED_WAKA_LANGS = {
    "other",
    "markdown",
    "text",
    "json",
    "json with comments",
    "git config",
    "git",
    "image (png)",
    "image (jpeg)",
    "image (svg)",
    "csv",
    "tsv",
    "ini",
    "toml",
    "yaml",
    "xml",
    "batchfile",
    "dockerfile",
    "docker",
    "makefile",
    "plantuml",
    "restructuredtext",
    "tsconfig",
    "java properties",
    "powershell",
    "tex",
    "latex",
}

LANG_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "Java": "#b07219",
    "ABAP": "#E8274B",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "C": "#6b7280",
    "C++": "#f34b7d",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "SQL": "#e38c00",
    "Standard ML": "#dc566d",
    "Prolog": "#74283c",
    "Bash": "#89e051",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Assembly": "#6E4C13",
    "Go": "#00ADD8",
    "Rust": "#dea584",
}


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def graphql_request(query: str, variables: dict[str, Any], token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Lealwbs-Unified-Readme",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if "errors" in body:
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body["data"]


def build_github_query(start_year: int, end_year: int) -> str:
    year_blocks = "\n".join(
        f'    y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
        "{ contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } }"
        for y in range(start_year, end_year + 1)
    )
    return f"""
query($login: String!) {{
  user(login: $login) {{
    createdAt
    followers {{ totalCount }}
    pullRequests(first: 1) {{ totalCount }}
    issues(first: 1) {{ totalCount }}
{year_blocks}
    contributionsCollection {{
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {{
        totalContributions
        weeks {{
          contributionDays {{
            contributionCount
            date
            weekday
          }}
        }}
      }}
    }}
    contributedRepos: repositories(
      first: 20
      ownerAffiliations: [OWNER, COLLABORATOR]
      privacy: PUBLIC
      orderBy: {{field: PUSHED_AT, direction: DESC}}
    ) {{
      nodes {{
        name
        nameWithOwner
        isPrivate
        description
        stargazerCount
        forkCount
        pushedAt
        primaryLanguage {{ name color }}
        defaultBranchRef {{
          target {{
            ... on Commit {{
              history(first: 25) {{
                nodes {{
                  committedDate
                  messageHeadline
                  author {{ user {{ login }} }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    repositories(
      first: 80
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
      orderBy: {{field: PUSHED_AT, direction: DESC}}
    ) {{
      totalCount
      nodes {{
        name
        description
        stargazerCount
        forkCount
        pushedAt
        primaryLanguage {{ name color }}
        languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
          edges {{
            size
            node {{ name color }}
          }}
        }}
        defaultBranchRef {{
          target {{
            ... on Commit {{
              history(first: 100) {{
                nodes {{
                  committedDate
                  messageHeadline
                  author {{ user {{ login }} }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""


def truncate(text: str, max_len: int) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= max_len else clean[: max_len - 1].rstrip() + "…"


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_dur(seconds: float) -> str:
    mins_total = int(round(seconds / 60.0))
    if mins_total < 1:
        return "1m"
    hrs, mins = divmod(mins_total, 60)
    if hrs == 0:
        return f"{mins}m"
    if mins == 0:
        return f"{hrs}h"
    return f"{hrs}h {mins}m"


def fetch_github_metrics(login: str, token: str) -> dict[str, Any]:
    meta = graphql_request(
        "query($login: String!) { user(login: $login) { createdAt } }",
        {"login": login},
        token,
    )
    start_year = int(meta["user"]["createdAt"][:4])
    end_year = dt.datetime.now(dt.timezone.utc).year
    data = graphql_request(build_github_query(start_year, end_year), {"login": login}, token)
    u = data["user"]

    all_days: dict[str, int] = {}
    all_time_contributions = 0
    for y in range(start_year, end_year + 1):
        cal_y = u[f"y{y}"]["contributionCalendar"]
        all_time_contributions += cal_y["totalContributions"]
        for w in cal_y["weeks"]:
            for d in w["contributionDays"]:
                all_days[d["date"]] = d["contributionCount"]

    dates_sorted = sorted(all_days.keys())
    longest_streak = run = 0
    for d in dates_sorted:
        if all_days[d] > 0:
            run += 1
            longest_streak = max(longest_streak, run)
        else:
            run = 0

    today_brt = dt.datetime.now(BRT).strftime("%Y-%m-%d")
    past_dates = [d for d in dates_sorted if d <= today_brt]
    current_streak = 0
    if past_dates:
        idx = len(past_dates) - 1
        if all_days[past_dates[idx]] == 0 and idx > 0 and all_days[past_dates[idx - 1]] > 0:
            idx -= 1
        while idx >= 0 and all_days[past_dates[idx]] > 0:
            current_streak += 1
            idx -= 1

    cc = u["contributionsCollection"]
    cal_1y = cc["contributionCalendar"]
    days_1y = [d for w in cal_1y["weeks"] for d in w["contributionDays"]]
    days_1y.sort(key=lambda d: d["date"])
    last_30 = days_1y[-30:] if len(days_1y) >= 30 else days_1y

    mon_sun = [0] * 7
    for d in days_1y:
        mon_sun[(d.get("weekday", 0) - 1) % 7] += d["contributionCount"]

    buckets = {"Morning": 0, "Daytime": 0, "Evening": 0, "Night": 0}
    repo_commit_map: dict[str, tuple[dt.datetime, dict[str, Any]]] = {}
    lang_sizes: dict[str, dict[str, Any]] = {}
    total_stars = 0

    for r in u["repositories"]["nodes"]:
        total_stars += int(r.get("stargazerCount") or 0)
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or "#8ab4f8"
            if name not in lang_sizes:
                lang_sizes[name] = {"size": 0, "color": color}
            lang_sizes[name]["size"] += edge["size"]

        ref = r.get("defaultBranchRef")
        latest_user_commit: dt.datetime | None = None
        latest_any_commit: dt.datetime | None = None
        if ref and ref.get("target"):
            for c in ref["target"]["history"]["nodes"]:
                ts_utc = dt.datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00"))
                if latest_any_commit is None or ts_utc > latest_any_commit:
                    latest_any_commit = ts_utc
                au = (c.get("author") or {}).get("user")
                if au and au.get("login", "").lower() != login.lower():
                    continue
                msg = (c.get("messageHeadline") or "").lower()
                if "[skip ci]" not in msg and (latest_user_commit is None or ts_utc > latest_user_commit):
                    latest_user_commit = ts_utc
                ts_brt = ts_utc.astimezone(BRT)
                h = ts_brt.hour
                if 6 <= h < 12:
                    buckets["Morning"] += 1
                elif 12 <= h < 18:
                    buckets["Daytime"] += 1
                elif 18 <= h < 24:
                    buckets["Evening"] += 1
                else:
                    buckets["Night"] += 1

        if r["name"].lower() != login.lower():
            commit_ts = latest_user_commit or latest_any_commit
            if commit_ts is None and r.get("pushedAt"):
                commit_ts = dt.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
            if commit_ts is not None:
                pl = r.get("primaryLanguage") or {}
                lang_lbl = pl.get("name") or "Docs"
                raw_desc = (r.get("description") or "").strip()
                desc_txt = truncate(raw_desc, 52) if raw_desc else f"{lang_lbl} project · active development"
                repo_commit_map[r["name"].lower()] = (
                    commit_ts,
                    {
                        "name": r["name"],
                        "description": desc_txt,
                        "language": lang_lbl,
                        "color": pl.get("color") or "#9aa0a6",
                        "stars": int(r.get("stargazerCount") or 0),
                        "forks": int(r.get("forkCount") or 0),
                        "commit_date": commit_ts.astimezone(BRT).strftime("%d/%m"),
                    },
                )

    for r in (u.get("contributedRepos") or {}).get("nodes", []):
        if r.get("isPrivate") or r["name"].lower() == login.lower():
            continue
        key = r["name"].lower()
        if key in repo_commit_map:
            continue
        ref = r.get("defaultBranchRef")
        latest_user_commit = None
        if ref and ref.get("target"):
            for c in ref["target"]["history"]["nodes"]:
                au = (c.get("author") or {}).get("user")
                if not au or au.get("login", "").lower() != login.lower():
                    continue
                ts_utc = dt.datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00"))
                if latest_user_commit is None or ts_utc > latest_user_commit:
                    latest_user_commit = ts_utc
        if latest_user_commit is not None:
            pl = r.get("primaryLanguage") or {}
            lang_lbl = pl.get("name") or "Docs"
            raw_desc = (r.get("description") or "").strip()
            desc_txt = truncate(raw_desc, 52) if raw_desc else f"{r['nameWithOwner']} · public repository"
            repo_commit_map[key] = (
                latest_user_commit,
                {
                    "name": r["name"],
                    "description": desc_txt,
                    "language": lang_lbl,
                    "color": pl.get("color") or "#9aa0a6",
                    "stars": int(r.get("stargazerCount") or 0),
                    "forks": int(r.get("forkCount") or 0),
                    "commit_date": latest_user_commit.astimezone(BRT).strftime("%d/%m"),
                },
            )

    repo_commit_candidates = sorted(repo_commit_map.values(), key=lambda item: item[0], reverse=True)
    recent_repos = [item[1] for item in repo_commit_candidates[:3]]
    latest_commit_label = ""
    if repo_commit_candidates:
        latest_brt_date = repo_commit_candidates[0][0].astimezone(BRT).date()
        today_brt_date = dt.datetime.now(BRT).date()
        delta_days = max(0, (today_brt_date - latest_brt_date).days)
        if delta_days == 0:
            latest_commit_label = "Today"
        elif delta_days == 1:
            latest_commit_label = "1 day ago"
        else:
            latest_commit_label = f"{delta_days} days ago"

    total_bytes = sum(v["size"] for v in lang_sizes.values()) or 1
    top_gh_langs = sorted(
        (
            {"name": k, "pct": (v["size"] / total_bytes) * 100.0, "color": v["color"]}
            for k, v in lang_sizes.items()
        ),
        key=lambda x: -x["pct"],
    )[:4]

    total_commits_1y = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    total_30d = sum(d["contributionCount"] for d in last_30)
    active_30d = sum(1 for d in last_30 if d["contributionCount"] > 0)

    return {
        "all_time_contributions": all_time_contributions,
        "commits_1y": total_commits_1y,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "public_repos": u["repositories"]["totalCount"],
        "pull_requests": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "total_stars": total_stars,
        "top_gh_langs": top_gh_langs,
        "weeks_1y": cal_1y["weeks"],
        "last_30": last_30,
        "total_30d": total_30d,
        "active_30d": active_30d,
        "avg_30d": total_30d / max(len(last_30), 1),
        "mon_sun": mon_sun,
        "buckets": buckets,
        "recent_repos": recent_repos,
        "latest_commit_label": latest_commit_label,
        "synced_date": dt.datetime.now(dt.timezone.utc).strftime("%d/%m/%Y"),
    }


def fmt_ddmm(iso_date: str) -> str:
    parts = iso_date.strip().split("-")
    if len(parts) == 3:
        return f"{parts[2][:2]}/{parts[1]}"
    return iso_date


def fetch_wakatime_metrics(api_key: str) -> dict[str, Any] | None:
    api_key = api_key.strip()
    if not api_key:
        return None
    headers = {"User-Agent": "Lealwbs-Unified-Readme"}
    if api_key.startswith("waka_tok_") or not api_key.startswith("waka_"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        return None

    selected: dict[str, Any] | None = None
    range_label = "All time"
    for slug, label in (("all_time", "All time"), ("last_year", "Last year"), ("last_30_days", "Last 30 days"), ("last_7_days", "Last 7 days")):
        req = urllib.request.Request(f"https://wakatime.com/api/v1/users/current/stats/{slug}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", {})
            if data.get("languages"):
                selected = data
                range_label = label
                break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
            continue

    if not selected:
        return None

    daily_avg_sec = float(
        selected.get("daily_average_including_other_language")
        or selected.get("daily_average")
        or 0
    )
    daily_avg_text = (
        selected.get("human_readable_daily_average_including_other_language")
        or selected.get("human_readable_daily_average")
        or (fmt_dur(daily_avg_sec) if daily_avg_sec > 0 else "")
    )
    best_day = selected.get("best_day") or {}
    return {
        "range_label": range_label,
        "total_text": selected.get("human_readable_total_including_other_language") or selected.get("human_readable_total") or "",
        "timezone": selected.get("timezone") or "America/Sao_Paulo",
        "daily_avg_text": daily_avg_text,
        "daily_avg_sec": daily_avg_sec,
        "best_day": {
            "date": fmt_ddmm(best_day.get("date") or ""),
            "text": best_day.get("text") or "",
            "total_seconds": float(best_day.get("total_seconds") or 0),
        },
        "categories": sorted((selected.get("categories") or []), key=lambda x: -(x.get("total_seconds") or 0)),
        "languages": sorted((selected.get("languages") or []), key=lambda x: -(x.get("total_seconds") or 0)),
        "editors": sorted(
            [e for e in (selected.get("editors") or []) if (e.get("total_seconds") or 0) > 0],
            key=lambda x: -(x.get("total_seconds") or 0),
        )[:7],
        "operating_systems": sorted((selected.get("operating_systems") or []), key=lambda x: -(x.get("total_seconds") or 0))[:2],
    }


def filter_coding_languages(langs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    filtered = [
        l for l in langs
        if l.get("name", "").strip().lower() not in EXCLUDED_WAKA_LANGS and (l.get("total_seconds") or 0) >= 60
    ]
    if not filtered:
        filtered = langs[:7]
    coding_total_sec = sum(float(l.get("total_seconds") or 0) for l in filtered) or 1.0
    out = []
    for l in filtered[:7]:
        sec = float(l.get("total_seconds") or 0)
        out.append({
            "name": l["name"],
            "total_seconds": sec,
            "coding_pct": (sec / coding_total_sec) * 100.0,
        })
    return out, coding_total_sec


def _http_json(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 12) -> Any:
    hdrs = {"User-Agent": "Lealwbs-Unified-Readme/1.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_platform_metrics() -> list[dict[str, Any]]:
    platforms: list[dict[str, Any]] = []

    # 1. Hugging Face (Lealwbs)
    try:
        hf = _http_json("https://huggingface.co/api/users/Lealwbs/overview")
        models = int(hf.get("numModels") or 0)
        datasets = int(hf.get("numDatasets") or 0)
        spaces = int(hf.get("numSpaces") or 0)
        total_hf = models + datasets + spaces
        if total_hf > 0:
            platforms.append({
                "key": "huggingface",
                "name": "Hugging Face",
                "handle": "@Lealwbs",
                "hero_val": str(total_hf),
                "hero_unit": "artifacts",
                "right_meta": f"{int(hf.get('numLikes') or 0)} likes",
                "sub_text": f"{models} models · {datasets} datasets · {spaces} spaces",
                "dot_color": "#FFD21E",
            })
    except Exception:
        pass

    # 2. Kaggle (lealwbs)
    try:
        ds_list = _http_json("https://www.kaggle.com/api/v1/datasets/list?user=lealwbs")
        ds_cnt = len(ds_list) if isinstance(ds_list, list) else 0
        nb_cnt = 0
        k_user = os.environ.get("KAGGLE_USERNAME", "").strip()
        k_key = os.environ.get("KAGGLE_KEY", "").strip()
        if k_user and k_key:
            import base64
            tok = base64.b64encode(f"{k_user}:{k_key}".encode("utf-8")).decode("ascii")
            k_list = _http_json(
                f"https://www.kaggle.com/api/v1/kernels/list?user={k_user}",
                headers={"Authorization": f"Basic {tok}"},
            )
            nb_cnt = len(k_list) if isinstance(k_list, list) else 0
        if ds_cnt + nb_cnt > 0:
            platforms.append({
                "key": "kaggle",
                "name": "Kaggle",
                "handle": "@lealwbs",
                "hero_val": str(ds_cnt + nb_cnt),
                "hero_unit": "published",
                "right_meta": "",
                "sub_text": f"{nb_cnt} notebooks · {ds_cnt} datasets",
                "dot_color": "#20BEFF",
            })
    except Exception:
        pass

    # 3. LeetCode (italoleallanasantos)
    try:
        payload = json.dumps({
            "query": (
                "query($u:String!){matchedUser(username:$u){username "
                "profile{ranking} "
                "submitStats:submitStatsGlobal{acSubmissionNum{difficulty count}} "
                "userCalendar{streak totalActiveDays}}}"
            ),
            "variables": {"u": "italoleallanasantos"},
        }).encode("utf-8")
        lc = _http_json(
            "https://leetcode.com/graphql",
            data=payload,
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
        )
        mu = (lc.get("data") or {}).get("matchedUser") or {}
        ac = {x["difficulty"]: int(x["count"]) for x in ((mu.get("submitStats") or {}).get("acSubmissionNum") or [])}
        solved = ac.get("All", 0)
        if solved > 0:
            cal = mu.get("userCalendar") or {}
            platforms.append({
                "key": "leetcode",
                "name": "LeetCode",
                "handle": "@italoleallanasantos",
                "hero_val": str(solved),
                "hero_unit": "solved",
                "right_meta": f"{int(cal.get('totalActiveDays') or 0)}d active",
                "sub_text": f"{ac.get('Easy', 0)}E · {ac.get('Medium', 0)}M · {ac.get('Hard', 0)}H",
                "dot_color": "#FFA116",
            })
    except Exception:
        pass

    # 4. Chess.com (lealz)
    try:
        cs = _http_json("https://api.chess.com/pub/player/lealz/stats")
        rapid = int(((cs.get("chess_rapid") or {}).get("last") or {}).get("rating") or 0)
        bullet = int(((cs.get("chess_bullet") or {}).get("last") or {}).get("rating") or 0)
        blitz = int(((cs.get("chess_blitz") or {}).get("last") or {}).get("rating") or 0)
        tactics = int(((cs.get("tactics") or {}).get("highest") or {}).get("rating") or 0)
        total_g = sum(
            int(((cs.get(m) or {}).get("record") or {}).get(k) or 0)
            for m in ("chess_rapid", "chess_bullet", "chess_blitz")
            for k in ("win", "loss", "draw")
        )
        if rapid or blitz or bullet:
            platforms.append({
                "key": "chesscom",
                "name": "Chess.com",
                "handle": "@lealz",
                "hero_val": fmt_num(rapid or blitz or bullet),
                "hero_unit": "Rapid" if rapid else ("Blitz" if blitz else "Bullet"),
                "right_meta": f"Tactics {fmt_num(tactics)}" if tactics else f"{fmt_num(total_g)} games",
                "sub_text": f"Bullet {bullet} · Blitz {blitz} · {fmt_num(total_g)}g",
                "dot_color": "#81B64C",
            })
    except Exception:
        pass

    # 5. Lichess (Lealz)
    try:
        li = _http_json("https://lichess.org/api/user/Lealz")
        perfs = li.get("perfs") or {}
        bullet = int((perfs.get("bullet") or {}).get("rating") or 0)
        blitz = int((perfs.get("blitz") or {}).get("rating") or 0)
        rapid = int((perfs.get("rapid") or {}).get("rating") or 0)
        total_g = int((li.get("count") or {}).get("all") or 0)
        if blitz or bullet or rapid:
            platforms.append({
                "key": "lichess",
                "name": "Lichess",
                "handle": "@Lealz",
                "hero_val": fmt_num(bullet or blitz or rapid),
                "hero_unit": "Bullet" if bullet else ("Blitz" if blitz else "Rapid"),
                "right_meta": f"{fmt_num(total_g)} games" if total_g else "",
                "sub_text": f"Rapid {rapid} · Blitz {blitz}",
                "dot_color": "#e3e3e3",
            })
    except Exception:
        pass

    return platforms


def load_tech_stack_inner(theme_name: str, y_pos: int) -> str:
    p = ASSETS_DIR / f"tech-stack-{theme_name}.svg"
    raw = p.read_text(encoding="utf-8")
    inner = re.sub(r"^<svg[^>]*>", "", raw.strip())
    inner = re.sub(r"</svg>$", "", inner.strip())
    inner = re.sub(r'id="(i\d+_[^"]+)"', rf'id="ts_{theme_name}_\1"', inner)
    inner = re.sub(r'url\(#(i\d+_[^)]+)\)', rf'url(#ts_{theme_name}_\1)', inner)
    return f'<svg x="21.5" y="{y_pos}" width="802" height="89" viewBox="0 0 802 89">{inner}</svg>'


def apply_log_scale_pacman_colors(inner: str, theme_name: str, weeks_1y: list[dict[str, Any]]) -> str:
    if not weeks_1y:
        return inner
    if theme_name == "dark":
        palette = ("#0e4429", "#006d32", "#26a641", "#39d353")
    else:
        palette = ("#9be9a8", "#40c463", "#30a14e", "#216e39")

    max_c = max(
        (d["contributionCount"] for w in weeks_1y for d in w.get("contributionDays", [])),
        default=1,
    )
    log_max = math.log1p(max(max_c, 1)) or 1.0

    # Align calendar weeks to the Pac-Man grid columns (most recent 53 weeks)
    cols = weeks_1y[-53:]
    col_offset = max(0, 53 - len(cols))
    cell_color: dict[str, str] = {}
    for w_idx, week in enumerate(cols):
        grid_x = w_idx + col_offset
        for d in week.get("contributionDays", []):
            cnt = int(d.get("contributionCount") or 0)
            if cnt <= 0:
                continue
            wd = int(d.get("weekday") or 0)
            ratio = math.log1p(cnt) / log_max
            lvl = 0 if ratio <= 0.25 else (1 if ratio <= 0.50 else (2 if ratio <= 0.75 else 3))
            cell_color[f"c-{grid_x}-{wd}"] = palette[lvl]

    if not cell_color:
        return inner

    pal_re = re.compile("|".join(re.escape(c) for c in palette), re.I)

    def _recolor_cell(m: re.Match[str]) -> str:
        cid = m.group(1)
        target = cell_color.get(cid)
        if not target:
            return m.group(0)
        return pal_re.sub(target, m.group(0))

    return re.sub(r'<rect id="(c-\d+-\d+)"[^>]*>.*?</rect>', _recolor_cell, inner, flags=re.S)


def load_pacman_inner(theme_name: str, y_pos: int, weeks_1y: list[dict[str, Any]] | None = None) -> str:
    fn = "pacman-contribution-graph-dark.svg" if theme_name == "dark" else "pacman-contribution-graph.svg"
    raw = ""
    url = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/output/{fn}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Lealwbs-Unified-Readme"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except Exception:
        try:
            raw = subprocess.check_output(["git", "show", f"origin/output:{fn}"], cwd=ROOT, text=True)
        except Exception:
            raw = ""

    if not raw:
        return ""

    inner = re.sub(r"^<svg[^>]*>", "", raw.strip())
    inner = re.sub(r"</svg>$", "", inner.strip())
    inner = re.sub(r'<rect\s+width="100%"\s+height="100%"[^/]*/>', "", inner, count=1)
    inner = re.sub(r"<metadata>.*?</metadata>", "", inner, flags=re.S)
    if weeks_1y:
        inner = apply_log_scale_pacman_colors(inner, theme_name, weeks_1y)
    return f'<svg x="22" y="{y_pos}" width="801" height="126" viewBox="0 0 1166 184">{inner}</svg>'


def render_pill_bar(x: float, y: float, width: float, ratio: float, accent: str, track: str) -> str:
    ratio_clamped = max(0.06, min(1.0, ratio))
    fill_w = width * ratio_clamped
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="6.5" rx="3.25" fill="{track}"/>'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{fill_w:.1f}" height="6.5" rx="3.25" fill="{accent}"/>'
    )


def flowing_grad_def(grad_id: str, theme_name: str, x1: float, x2: float, dur: str = "7s") -> str:
    if theme_name == "dark":
        c0, c1, c2, c3 = "#8ab4f8", "#c58af9", "#f28b82", "#39c5cf"
    else:
        c0, c1, c2, c3 = "#1a73e8", "#8430ce", "#d96570", "#00838f"
    shift = (x2 - x1) * 0.45
    return f"""    <linearGradient id="{grad_id}" gradientUnits="userSpaceOnUse" x1="{x1:.0f}" y1="0" x2="{x2:.0f}" y2="0" spreadMethod="reflect">
      <stop offset="0%" stop-color="{c0}">
        <animate attributeName="stop-color" values="{c0};{c1};{c2};{c3};{c0}" dur="{dur}" repeatCount="indefinite"/>
      </stop>
      <stop offset="50%" stop-color="{c1}">
        <animate attributeName="stop-color" values="{c1};{c2};{c3};{c0};{c1}" dur="{dur}" repeatCount="indefinite"/>
      </stop>
      <stop offset="100%" stop-color="{c3}">
        <animate attributeName="stop-color" values="{c3};{c0};{c1};{c2};{c3}" dur="{dur}" repeatCount="indefinite"/>
      </stop>
      <animate attributeName="x1" values="{x1:.0f};{x1 + shift:.0f};{x1:.0f}" dur="{dur}" repeatCount="indefinite"/>
      <animate attributeName="x2" values="{x2:.0f};{x2 + shift:.0f};{x2:.0f}" dur="{dur}" repeatCount="indefinite"/>
    </linearGradient>"""


def render_hero_svg(theme_name: str) -> str:
    t = THEMES[theme_name]
    dot_cycle = f"{t['accent_strong']};{t['accent_violet']};{t['accent_rose']};{t['accent_cyan']};{t['accent_strong']}"
    pill_lines = [
        "Information Systems · UFMG",
        "SAP ABAP Consultant · Seidor Brasil",
        "AI Agents, Automation & Systems Engineering",
    ]
    pill_keytimes = [
        "0;0.30;0.333;0.967;1",
        "0;0.30;0.333;0.633;0.667;1",
        "0;0.633;0.667;0.967;1",
    ]
    pill_vals = [
        "1;1;0;0;1",
        "0;0;1;1;0;0",
        "0;0;1;1;0",
    ]
    pill_init = ["1", "0", "0"]
    pill_texts = []
    for i, msg in enumerate(pill_lines):
        pill_texts.append(
            f'<text x="422.5" y="72.5" text-anchor="middle" font-family="{SANS}" font-size="11.2" font-weight="500" fill="{t["text"]}" opacity="{pill_init[i]}">'
            f'{html.escape(msg)}'
            f'<animate attributeName="opacity" values="{pill_vals[i]}" keyTimes="{pill_keytimes[i]}" dur="12s" repeatCount="indefinite"/>'
            f'</text>'
        )

    height = 86
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="845" height="{height}" viewBox="0 0 845 {height}" fill="none">
  <defs>
{flowing_grad_def(f"heroNameFlow_{theme_name}", theme_name, 250, 595, "7s")}
{flowing_grad_def(f"heroPillFlow_{theme_name}", theme_name, 265, 580, "7s")}
  </defs>

  <text x="422.5" y="42" text-anchor="middle" font-family="{MONO}" font-size="45" font-weight="900" letter-spacing="-0.8" fill="url(#heroNameFlow_{theme_name})" stroke="url(#heroNameFlow_{theme_name})" stroke-width="2.0" paint-order="stroke">Ítalo Leal</text>

  <rect x="270.5" y="56" width="304" height="25" rx="12.5" fill="{t["accent_soft"]}" stroke="url(#heroPillFlow_{theme_name})" stroke-width="1.2" stroke-opacity="0.72"/>
  {"".join(pill_texts)}
</svg>
'''


def render_unified_readme_svg(
    gh: dict[str, Any],
    waka: dict[str, Any] | None,
    theme_name: str,
    platforms: list[dict[str, Any]] | None = None,
) -> str:
    t = THEMES[theme_name]
    coding_langs: list[dict[str, Any]] = []
    coding_total_sec = 0.0
    if waka and waka.get("languages"):
        coding_langs, coding_total_sec = filter_coding_languages(waka["languages"])
    has_waka = bool(waka and coding_langs)
    active_platforms = platforms or []
    has_platforms = len(active_platforms) > 0

    # Floating Hero (profile/hero-{dark,light}.svg) + 5 Clickable Social Pills sit cleanly above this block.
    # Band 1 (Tech Stack 17x2):             y = 18 .. 121 (svg at y=18, h=89)
    # Band 2 (Pac-Man Contribution Graph):  y = 121 .. 265 (svg at y=131, h=126)
    # Band 3..6 reuse clean relative layout with off = 265!
    off = 265
    base_bottom = 753 + off if has_waka else 530 + off
    plat_card_h = 58
    plat_row_gap = 12
    if has_platforms:
        n_plat = len(active_platforms)
        if n_plat <= 3:
            plat_rows_counts = [n_plat]
        elif n_plat == 4:
            plat_rows_counts = [2, 2]
        elif n_plat == 5:
            plat_rows_counts = [3, 2]
        else:
            plat_rows_counts = [3] * (n_plat // 3) + ([n_plat % 3] if n_plat % 3 else [])
        n_plat_rows = len(plat_rows_counts)
        height = base_bottom + 32 + n_plat_rows * plat_card_h + max(n_plat_rows - 1, 0) * plat_row_gap + 26
    else:
        plat_rows_counts = []
        height = base_bottom + 26

    tech_stack_svg = load_tech_stack_inner(theme_name, y_pos=18)
    pacman_svg = load_pacman_inner(theme_name, y_pos=131, weeks_1y=gh.get("weeks_1y"))

    # --- Band 3: Overview (compact 26..334) & Activity (wider 366..819) ---
    ov_items = [
        ("Student", "Undergraduate 7th Semester", t["accent_strong"]),
        ("Founder", "Coletivo Voa Voa ENEM Prep", t["accent_rose"]),
        ("Alumni", "Aspire Leaders Program '25", t["accent_cyan"]),
        ("Member", "Stanford LC Talent Network", t["accent"]),
        ("President", "Liga ISMART UFMG", t["accent_violet"]),
    ]
    ov_svg = []
    for i, (role_lbl, title_val, dot_col) in enumerate(ov_items):
        ry = 63 + off + i * 28
        ov_svg.append(
            f'<rect x="26" y="{ry - 13.5}" width="308" height="23" rx="7.5" fill="{t["card"]}" stroke="{t["border_soft"]}"/>'
            f'<circle cx="39" cy="{ry - 2}" r="3.0" fill="{dot_col}"/>'
            f'<text x="49" y="{ry + 1.5}" font-family="{SANS}" font-size="10.2" font-weight="500" fill="{t["muted"]}">{html.escape(role_lbl)}</text>'
            f'<text x="104" y="{ry + 1.5}" font-family="{SANS}" font-size="10.9" font-weight="600" fill="{t["text"]}">{html.escape(title_val)}</text>'
        )

    bar_x, bar_w, bar_y = 366, 453, 165 + off
    bar_segs, lang_leg = [], []
    cur_x = float(bar_x)
    top_langs = gh["top_gh_langs"]
    top_sum = sum(l["pct"] for l in top_langs) or 1.0
    leg_widths = [14 + len(f"{l['name']} {l['pct']:.0f}%") * 5.85 for l in top_langs]
    leg_gap = (bar_w - sum(leg_widths)) / max(len(top_langs) - 1, 1) if len(top_langs) > 1 else 0.0
    lx = float(bar_x)
    for i, lang in enumerate(top_langs):
        w = (lang["pct"] / top_sum) * bar_w
        if i == len(top_langs) - 1:
            w = (bar_x + bar_w) - cur_x
        bar_segs.append(f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{max(w, 2.0):.1f}" height="6" rx="1.5" fill="{lang["color"]}"/>')
        cur_x += w
        lang_leg.append(
            f'<circle cx="{lx + 4:.1f}" cy="{186 + off}" r="3.5" fill="{lang["color"]}"/>'
            f'<text x="{lx + 12:.1f}" y="{189.5 + off}" font-family="{SANS}" font-size="10.5" font-weight="500" fill="{t["subtext"]}">{html.escape(lang["name"])} <tspan fill="{t["muted"]}">{lang["pct"]:.0f}%</tspan></text>'
        )
        lx += leg_widths[i] + leg_gap

    # --- Band 4: 30d Waveform (Logarithmic Scale log1p, clean without peak badge or '(log)') ---
    days = gh["last_30"]
    n = len(days)
    x0, x1 = 44.0, 818.0
    wy_top, wy_bot = 252.0 + off, 314.0 + off
    max_val = max((d["contributionCount"] for d in days), default=1)
    y_scale_max = max(max_val, 5)
    log_max = math.log1p(y_scale_max) or 1.0
    pts = [
        (
            x0 + (i / max(n - 1, 1)) * (x1 - x0),
            wy_bot - (math.log1p(d["contributionCount"]) / log_max) * (wy_bot - wy_top),
        )
        for i, d in enumerate(days)
    ]
    cmds = [f"M {pts[0][0]:.2f} {pts[0][1]:.2f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = max(wy_top - 3, min(wy_bot, p1[1] + (p2[1] - p0[1]) / 6.0))
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = max(wy_top - 3, min(wy_bot, p2[1] - (p3[1] - p1[1]) / 6.0))
        cmds.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}")
    line_d = " ".join(cmds)
    area_d = f"{line_d} L {pts[-1][0]:.2f} {wy_bot:.2f} L {pts[0][0]:.2f} {wy_bot:.2f} Z"
    peak_idx = max(range(n), key=lambda i: days[i]["contributionCount"]) if n else 0
    peak_cnt = days[peak_idx]["contributionCount"] if n else 0
    wave_dots = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{3.2 if i == peak_idx else 1.8}" fill="{t["accent"]}" stroke="{t["dot_ring"]}" stroke-width="1"/>'
        for i, (px, py) in enumerate(pts) if days[i]["contributionCount"] > 0
    )
    x_ticks = "".join(
        f'<text x="{pts[idx][0]:.1f}" y="{332 + off}" text-anchor="{"start" if idx == 0 else ("end" if idx == n - 1 else "middle")}" font-family="{MONO}" font-size="9" fill="{t["faint"]}">{fmt_ddmm(days[idx]["date"])}</text>'
        for idx in ([0, 7, 14, 21, n - 1] if n >= 22 else list(range(n)))
    )
    mid_y = (wy_top + wy_bot) / 2.0
    mid_log_val = max(1, int(round(math.expm1(log_max * 0.5))))

    # --- Band 5: Commit Schedule & Recently Committed (stacked language + date right) ---
    b_total = sum(gh["buckets"].values()) or 1
    peak_bucket = max(gh["buckets"].items(), key=lambda kv: kv[1])[0]
    b_max = max(gh["buckets"].values()) or 1
    bucket_rows = []
    period_specs = (
        ("Morning", "06h–12h", lambda cy, c: (
            f'<path d="M27 {cy + 2.5}h10M29 {cy + 2.5}a3 3 0 0 1 6 0M32 {cy - 3.5}v1.5M28.5 {cy - 1.5}l1 1M35.5 {cy - 1.5}l-1 1" '
            f'stroke="{c}" stroke-width="1.25" stroke-linecap="round" fill="none"/>'
        )),
        ("Daytime", "12h–18h", lambda cy, c: (
            f'<circle cx="32" cy="{cy}" r="2.6" stroke="{c}" stroke-width="1.25" fill="none"/>'
            f'<path d="M32 {cy - 4.6}v1.1M32 {cy + 3.5}v1.1M27.4 {cy}h1.1M35.5 {cy}h1.1M28.8 {cy - 3.2}l.8.8M34.4 {cy + 2.4}l.8.8M35.2 {cy - 3.2}l-.8.8M29.6 {cy + 2.4}l-.8.8" '
            f'stroke="{c}" stroke-width="1.15" stroke-linecap="round"/>'
        )),
        ("Evening", "18h–24h", lambda cy, c: (
            f'<path d="M27 {cy + 2}h10M29 {cy + 2}a3 3 0 0 1 6 0M32 {cy - 3.5}v1.5M29.5 {cy - 1.5}l2.5 1.8 2.5-1.8" '
            f'stroke="{c}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        )),
        ("Night", "00h–06h", lambda cy, c: (
            f'<path d="M34.8 {cy + 1.8}A3.9 3.9 0 0 1 30.2 {cy - 3.6}A3.7 3.7 0 1 0 34.8 {cy + 1.8}Z" '
            f'stroke="{c}" stroke-width="1.25" stroke-linejoin="round" fill="none"/>'
        )),
    )
    for idx, (label, window, icon_fn) in enumerate(period_specs):
        cnt = gh["buckets"][label]
        pct = (cnt / b_total) * 100.0
        ry = 398 + off + idx * 23
        is_peak = label == peak_bucket
        bar_col = t["accent"] if is_peak else t["subtext"]
        lbl_col = t["text"] if is_peak else t["subtext"]
        icon_col = t["accent"] if is_peak else t["muted"]
        bucket_rows.append(
            icon_fn(ry - 3.5, icon_col)
            + f'<text x="42" y="{ry}" font-family="{SANS}" font-size="11.2" font-weight="500" fill="{lbl_col}">{label} <tspan font-family="{MONO}" font-size="9.5" fill="{t["faint"]}">({window})</tspan></text>'
            f'<text x="194" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{t["muted"]}">{cnt}</text>'
            + render_pill_bar(204, ry - 7, 160, cnt / b_max, bar_col, t["bar_muted"])
            + f'<text x="414" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="10.5" font-weight="600" fill="{bar_col if is_peak else t["muted"]}">{pct:.1f}%</text>'
        )

    wd_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    wd_counts = gh["mon_sun"]
    wd_peak = max(range(7), key=lambda i: wd_counts[i])
    wd_pills = []
    for i, (lbl, cnt) in enumerate(zip(wd_labels, wd_counts)):
        px = 26 + i * 56
        is_p = i == wd_peak
        fill = t["accent_soft"] if is_p else t["card"]
        stroke = t["accent_border"] if is_p else t["border"]
        tc = t["accent"] if is_p else t["text"]
        wd_pills.append(
            f'<rect x="{px}" y="{484 + off}" width="50" height="28" rx="7" fill="{fill}" stroke="{stroke}"/>'
            f'<text x="{px + 25}" y="{496 + off}" text-anchor="middle" font-family="{SANS}" font-size="8.5" fill="{t["muted"]}">{lbl}</text>'
            f'<text x="{px + 25}" y="{507.5 + off}" text-anchor="middle" font-family="{MONO}" font-size="10" font-weight="600" fill="{tc}">{cnt}</text>'
        )

    repo_cards = []
    fork_icon_path = "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"
    for i, r in enumerate(gh["recent_repos"]):
        cy = 390 + off + i * 42
        name_disp = truncate(r["name"], 24)
        meta_x = 475.0 + len(name_disp) * 6.65 + 8.0
        meta_parts = []
        if r["stars"] > 0:
            s_txt = f'★{r["stars"]}'
            meta_parts.append(
                f'<text x="{meta_x:.1f}" y="{cy + 14.5}" font-family="{MONO}" font-size="9.5" font-weight="500" fill="{t["muted"]}">{s_txt}</text>'
            )
            meta_x += len(s_txt) * 5.8 + 7.0
        if r.get("forks", 0) > 0:
            f_txt = str(r["forks"])
            meta_parts.append(
                f'<g transform="translate({meta_x:.1f}, {cy + 6.2:.1f}) scale(0.62)"><path d="{fork_icon_path}" fill="{t["muted"]}"/></g>'
                f'<text x="{meta_x + 11.0:.1f}" y="{cy + 14.5}" font-family="{MONO}" font-size="9.5" font-weight="500" fill="{t["muted"]}">{f_txt}</text>'
            )
        repo_cards.append(
            f'<rect x="450" y="{cy}" width="369" height="35" rx="9" fill="{t["card"]}" stroke="{t["border"]}"/>'
            f'<circle cx="464" cy="{cy + 17.5}" r="3.5" fill="{r["color"]}"/>'
            f'<text x="475" y="{cy + 14.5}" font-family="{MONO}" font-size="11" font-weight="600" fill="{t["text"]}">{html.escape(name_disp)}</text>'
            + "".join(meta_parts)
            + f'<text x="807" y="{cy + 14.5}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t["muted"]}">{html.escape(r["language"])}</text>'
            f'<text x="475" y="{cy + 27.5}" font-family="{SANS}" font-size="10" fill="{t["muted"]}">{html.escape(truncate(r["description"], 44))}</text>'
            f'<text x="807" y="{cy + 27.5}" text-anchor="end" font-family="{MONO}" font-size="9" fill="{t["faint"]}">{html.escape(r.get("commit_date") or "")}</text>'
        )

    # --- Band 6: WakaTime 3-Column Bento (Col 1: Coding Languages | Col 2: Editors | Col 3: Pace) ---
    waka_svg = ""
    if has_waka and waka is not None:
        max_lang_sec = max((l["total_seconds"] for l in coding_langs), default=1.0)
        w_eds = waka.get("editors", [])[:7]
        max_ed_sec = max((float(e.get("total_seconds") or 0) for e in w_eds), default=1.0) or 1.0
        w_oss = waka.get("operating_systems", [])[:1]

        w_lang_rows = []
        for i, item in enumerate(coding_langs):
            ry = 590 + off + i * 23
            name = item["name"]
            sec = item["total_seconds"]
            dur = fmt_dur(sec)
            pct = item["coding_pct"]
            col = LANG_COLORS.get(name, t["accent"])
            w_lang_rows.append(
                f'<circle cx="30" cy="{ry - 3.5}" r="3.5" fill="{col}"/>'
                f'<text x="40" y="{ry}" font-family="{SANS}" font-size="11" font-weight="500" fill="{t["text"]}">{html.escape(truncate(name, 13))}</text>'
                f'<text x="168" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["muted"]}">{html.escape(dur)}</text>'
                + render_pill_bar(176, ry - 7, 130, sec / max_lang_sec, col, t["bar_muted"])
                + f'<text x="356" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="10" font-weight="600" fill="{t["subtext"]}">{pct:.1f}%</text>'
            )

        ed_rows = []
        for i, e in enumerate(w_eds):
            ry = 590 + off + i * 23
            sec = float(e.get("total_seconds") or 0)
            pct = float(e.get("percent") or 0)
            ed_rows.append(
                f'<text x="384" y="{ry}" font-family="{SANS}" font-size="10.6" font-weight="500" fill="{t["text"]}">{html.escape(truncate(e["name"], 20))}</text>'
                f'<text x="548" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="9.8" fill="{t["muted"]}">{html.escape(fmt_dur(sec))}</text>'
                + render_pill_bar(556, ry - 7, 88, sec / max_ed_sec, t["accent"], t["bar_muted"])
                + f'<text x="685" y="{ry}" text-anchor="end" font-family="{MONO}" font-size="9.8" font-weight="600" fill="{t["subtext"]}">{pct:.1f}%</text>'
            )

        all_time_sec = float(w_oss[0].get("total_seconds") or 0) if w_oss else 0.0
        all_time_lbl = fmt_dur(all_time_sec) if all_time_sec > 0 else waka["total_text"]
        daily_avg_sec = float(waka.get("daily_avg_sec") or 0)
        daily_avg_lbl = fmt_dur(daily_avg_sec) if daily_avg_sec > 0 else "—"
        best_day = waka.get("best_day") or {}
        best_sec = float(best_day.get("total_seconds") or 0)
        best_lbl = fmt_dur(best_sec) if best_sec > 0 else "—"
        best_date_lbl = best_day.get("date") or ""

        p_y0 = 580 + off
        pace_cards = f"""
  <rect x="713" y="{p_y0}" width="106" height="45" rx="9" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="723" y="{p_y0 + 16}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["muted"]}">All time</text>
  <text x="723" y="{p_y0 + 35}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["accent_violet"]}">{html.escape(all_time_lbl)}</text>

  <rect x="713" y="{p_y0 + 53}" width="106" height="45" rx="9" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="723" y="{p_y0 + 69}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["muted"]}">Daily avg</text>
  <text x="723" y="{p_y0 + 88}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["accent_cyan"]}">{html.escape(daily_avg_lbl)}</text>

  <rect x="713" y="{p_y0 + 106}" width="106" height="45" rx="9" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="723" y="{p_y0 + 122}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["muted"]}">Best day</text>
  <text x="810" y="{p_y0 + 122}" text-anchor="end" font-family="{MONO}" font-size="8.8" fill="{t["faint"]}">{html.escape(best_date_lbl)}</text>
  <text x="723" y="{p_y0 + 141}" font-family="{MONO}" font-size="13.5" font-weight="700" fill="{t["accent_rose"]}">{html.escape(best_lbl)}</text>
"""

        waka_svg = f"""
  <!-- Band 6 Divider: WakaTime (3 Columns) -->
  <line x1="26" y1="{530 + off}" x2="819" y2="{530 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="26" y="{553 + off}" font-family="{SANS}" font-size="13.5" font-weight="700" fill="url(#dashWakaFlow_{theme_name})">WakaTime</text>
  <text x="26" y="{571 + off}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["faint"]}">CODING LANGUAGES</text>
  <text x="384" y="{571 + off}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["faint"]}">EDITORS</text>
  <text x="713" y="{571 + off}" font-family="{SANS}" font-size="9.5" font-weight="500" fill="{t["faint"]}">PACE</text>
  <line x1="370" y1="{560 + off}" x2="370" y2="{734 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <line x1="699" y1="{560 + off}" x2="699" y2="{734 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  {"".join(w_lang_rows)}
  {"".join(ed_rows)}
  {pace_cards}
"""

    platforms_svg = ""
    if has_platforms:
        plat_icon_paths = {
            "leetcode": (
                "M13.483 0a1.374 1.374 0 0 0-.961.438L7.116 6.226l-3.854 4.126a5.266 5.266 0 0 0-1.209 2.104 "
                "5.35 5.35 0 0 0-.125.513 5.527 5.527 0 0 0 .062 2.362 5.83 5.83 0 0 0 .349 1.017 5.938 5.938 0 0 0 "
                "1.271 1.818l4.277 4.193.039.038c2.248 2.165 5.852 2.133 8.063-.074l2.396-2.392c.54-.54.54-1.414.003-1.955a1.378 "
                "1.378 0 0 0-1.951-.003l-2.396 2.392a3.021 3.021 0 0 1-4.205.038l-.02-.019-4.276-4.193c-.652-.64-.972-1.469-.948-2.263a2.68 "
                "2.68 0 0 1 .066-.523 2.545 2.545 0 0 1 .619-1.164L9.13 8.114c1.058-1.134 3.204-1.27 4.43-.278l3.501 "
                "2.831c.593.48 1.461.387 1.94-.207a1.384 1.384 0 0 0-.207-1.943l-3.5-2.831c-.8-.647-1.766-1.045-2.774-1.202l2.015-2.158A1.384 "
                "1.384 0 0 0 13.483 0zm-2.866 12.815a1.38 1.38 0 0 0-1.38 1.382 1.38 1.38 0 0 0 1.38 1.382H20.79a1.38 "
                "1.38 0 0 0 1.38-1.382 1.38 1.38 0 0 0-1.38-1.382z"
            ),
            "chesscom": (
                "M12 0a3.85 3.85 0 0 0-3.875 3.846A3.84 3.84 0 0 0 9.73 6.969l-2.79 1.85c0 .622.144 1.114.434 "
                "1.649H9.83c-.014.245-.014.549-.014.925 0 .025.003.048.006.071-.064 1.353-.507 3.472-3.62 5.842-.816.625-1.423 "
                "1.495-1.806 2.533a.33.33 0 0 0-.045.084 8.124 8.124 0 0 0-.39 2.516c0 .1.216 1.561 8.038 1.561s8.038-1.46 "
                "8.038-1.561c0-2.227-.824-4.048-2.24-5.133-4.034-3.08-3.586-5.74-3.644-6.838h2.458c.29-.535.434-1.027.434-1.649l-2.79-1.836a3.86 "
                "3.86 0 0 0 1.604-3.123A3.873 3.873 0 0 0 13.445.275c-.004-.002-.01.004-.015.004A3.76 3.76 0 0 0 12 0Z"
            ),
            "lichess": (
                "M10.457 6.161a.237.237 0 0 0-.296.165c-.8 2.785 2.819 5.579 5.214 7.428.653.504 1.216.939 1.591 1.292 "
                "1.745 1.642 2.564 2.851 2.733 3.178a.24.24 0 0 0 .275.122c.047-.013 4.726-1.3 3.934-4.574a.257.257 0 0 0-.023-.06L18.204 "
                "3.407 18.93.295a.24.24 0 0 0-.262-.293c-1.7.201-3.115.435-4.5 1.425-4.844-.323-8.718.9-11.213 3.539C.334 7.737-.246 "
                "11.515.085 14.128c.763 5.655 5.191 8.631 9.081 9.532.993.229 1.974.34 2.923.34 3.344 0 6.297-1.381 7.946-3.85a.24.24 "
                "0 0 0-.372-.3c-3.411 3.527-9.002 4.134-13.296 1.444-4.485-2.81-6.202-8.41-3.91-12.749C4.741 4.221 8.801 2.362 13.888 "
                "3.31c.056.01.115 0 .165-.029l.335-.197c.926-.546 1.961-1.157 2.873-1.279l-.694 1.993a.243.243 0 0 0 .02.202l6.082 "
                "10.192c-.193 2.028-1.706 2.506-2.226 2.611-.287-.645-.814-1.364-2.306-2.803-.422-.407-1.21-.941-2.124-1.56-2.364-1.601-5.937-4.02-5.391-5.984a.239.239 "
                "0 0 0-.165-.295z"
            ),
            "huggingface": (
                "M12.025 1.13c-5.77 0-10.449 4.647-10.449 10.378 0 1.112.178 2.181.503 3.185.064-.222.203-.444.416-.577a.96.96 "
                "0 0 1 .524-.15c.293 0 .584.124.84.284.278.173.48.408.71.694.226.282.458.611.684.951v-.014c.017-.324.106-.622.264-.874s.403-.487.762-.543c.3-.047.596.06.787.203s.31.313.4.467c.15.257.212.468.233.542.01.026.653 "
                "1.552 1.657 2.54.616.605 1.01 1.223 1.082 1.912.055.537-.096 1.059-.38 1.572.637.121 1.294.187 1.967.187.657 0 1.298-.063 "
                "1.921-.178-.287-.517-.44-1.041-.384-1.581.07-.69.465-1.307 1.081-1.913 1.004-.987 1.647-2.513 1.657-2.539.021-.074.083-.285.233-.542.09-.154.208-.323.4-.467a1.08 "
                "1.08 0 0 1 .787-.203c.359.056.604.29.762.543s.247.55.265.874v.015c.225-.34.457-.67.683-.952.23-.286.432-.52.71-.694.257-.16.547-.284.84-.285a.97 "
                ".97 0 0 1 .524.151c.228.143.373.388.43.625l.006.04a10.3 10.3 0 0 0 .534-3.273c0-5.731-4.678-10.378-10.449-10.378M8.327 "
                "6.583a1.5 1.5 0 0 1 .713.174 1.487 1.487 0 0 1 .617 2.013c-.183.343-.762-.214-1.102-.094-.38.134-.532.914-.917.71a1.487 "
                "1.487 0 0 1 .69-2.803m7.486 0a1.487 1.487 0 0 1 .689 2.803c-.385.204-.536-.576-.916-.71-.34-.12-.92.437-1.103.094a1.487 "
                "1.487 0 0 1 .617-2.013 1.5 1.5 0 0 1 .713-.174m-10.68 1.55a.96.96 0 1 1 0 1.921.96.96 0 0 1 0-1.92m13.838 0a.96.96 0 1 1 0 1.92.96.96 0 0 1 0-1.92"
            ),
            "kaggle": (
                "M5.4 2.5v19h2.9v-5.3l1.7-1.6 5.9 6.9h3.7l-7.5-8.9L18.9 6h-3.6l-7 6.8V2.5z"
            ),
        }
        plat_y0 = base_bottom
        p_gap = 12.0
        plat_cards = []
        plat_idx = 0
        for row_idx, row_n in enumerate(plat_rows_counts):
            card_y = plat_y0 + 32 + row_idx * (plat_card_h + plat_row_gap)
            card_w = (793.0 - (row_n - 1) * p_gap) / row_n
            for col_idx in range(row_n):
                p = active_platforms[plat_idx]
                plat_idx += 1
                px = 26.0 + col_idx * (card_w + p_gap)
                key = p.get("key") or ""
                icon_col = t["text"] if key == "lichess" else p.get("dot_color", t["accent"])
                hero_col = t["accent"] if key == "leetcode" else t["text"]
                icon_d = plat_icon_paths.get(key, "")
                icon_el = (
                    f'<g transform="translate({px + 12:.1f}, {card_y + 9.0:.1f}) scale(0.52)"><path d="{icon_d}" fill="{icon_col}"/></g>'
                    if icon_d
                    else f'<circle cx="{px + 15:.1f}" cy="{card_y + 15.0}" r="3.2" fill="{icon_col}"/>'
                )
                plat_cards.append(
                    f'<rect x="{px:.1f}" y="{card_y}" width="{card_w:.1f}" height="{plat_card_h}" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>'
                    + icon_el
                    + f'<text x="{px + 29:.1f}" y="{card_y + 18.5}" font-family="{SANS}" font-size="11.2" font-weight="600" fill="{t["text"]}">{html.escape(p["name"])}</text>'
                    f'<text x="{px + card_w - 12:.1f}" y="{card_y + 18.5}" text-anchor="end" font-family="{MONO}" font-size="9" fill="{t["faint"]}">{html.escape(p["handle"])}</text>'
                    f'<text x="{px + 12:.1f}" y="{card_y + 37.5}" font-family="{MONO}" font-size="14.5" font-weight="700" fill="{hero_col}">{html.escape(p["hero_val"])} <tspan font-family="{SANS}" font-size="10" font-weight="500" fill="{t["muted"]}">{html.escape(p["hero_unit"])}</tspan></text>'
                    f'<text x="{px + card_w - 12:.1f}" y="{card_y + 37.5}" text-anchor="end" font-family="{MONO}" font-size="9.2" fill="{t["subtext"]}">{html.escape(p.get("right_meta") or "")}</text>'
                    f'<text x="{px + 12:.1f}" y="{card_y + 51}" font-family="{MONO}" font-size="9" fill="{t["muted"]}">{html.escape(p["sub_text"])}</text>'
                )
        platforms_svg = f"""
  <!-- Band 7: External Platforms (Hugging Face, Kaggle, LeetCode | Chess.com, Lichess) -->
  <line x1="26" y1="{plat_y0}" x2="819" y2="{plat_y0}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="26" y="{plat_y0 + 22}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Platforms</text>
  <text x="819" y="{plat_y0 + 22}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t["faint"]}">Live public telemetry</text>
  {"".join(plat_cards)}
"""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="845" height="{height}" viewBox="0 0 845 {height}" fill="none">
  <defs>
    <linearGradient id="dashArea_{theme_name}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t["wave_top"]}" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="{t["wave_bot"]}" stop-opacity="0.0"/>
    </linearGradient>
{flowing_grad_def(f"dashLine_{theme_name}", theme_name, 44, 818, "7s")}
{flowing_grad_def(f"dashContribFlow_{theme_name}", theme_name, 375, 495, "7s")}
{flowing_grad_def(f"dashWakaFlow_{theme_name}", theme_name, 26, 110, "7s")}
  </defs>

  <!-- ONE Unified Homogeneous Outer Frame -->
  <rect x="0.5" y="0.5" width="844" height="{height - 1}" rx="16" fill="{t["bg"]}" stroke="{t["border"]}"/>

  <!-- Band 1: Tech Stack (34 full-bleed brand icons, 17x2) -->
  {tech_stack_svg}

  <!-- Band 2: Pac-Man Contribution Graph (Log Scale) -->
  <line x1="26" y1="121" x2="819" y2="121" stroke="{t["border_soft"]}" stroke-width="1"/>
  {pacman_svg}

  <!-- Band 3: Overview & Activity -->
  <line x1="26" y1="{off}" x2="819" y2="{off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="26" y="{30 + off}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Overview</text>
  <text x="334" y="{30 + off}" text-anchor="end" font-family="{MONO}" font-size="9.2" fill="{t["faint"]}">Academic Average (NSG): 85.1 / 100</text>
  <line x1="26" y1="{40 + off}" x2="334" y2="{40 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  {"".join(ov_svg)}

  <line x1="350" y1="{18 + off}" x2="350" y2="{196 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>

  <text x="366" y="{30 + off}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Activity</text>
  <text x="819" y="{30 + off}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["faint"]}">★{gh["total_stars"]} · {gh["followers"]} followers · {gh["synced_date"]}</text>
  <line x1="366" y1="{40 + off}" x2="819" y2="{40 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>

  <rect x="366" y="{50 + off}" width="144" height="50" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="378" y="{67 + off}" font-family="{SANS}" font-size="10.5" font-weight="500" fill="{t["muted"]}">Contributions</text>
  <text x="378" y="{89 + off}" font-family="{MONO}" font-size="18" font-weight="700" fill="url(#dashContribFlow_{theme_name})">{fmt_num(gh["all_time_contributions"])}</text>

  <rect x="520.5" y="{50 + off}" width="144" height="50" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="532.5" y="{67 + off}" font-family="{SANS}" font-size="10.5" font-weight="500" fill="{t["muted"]}">Commits (1y)</text>
  <text x="532.5" y="{89 + off}" font-family="{MONO}" font-size="18" font-weight="700" fill="{t["text"]}">{fmt_num(gh["commits_1y"])}</text>

  <rect x="675" y="{50 + off}" width="144" height="50" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="687" y="{67 + off}" font-family="{SANS}" font-size="10.5" font-weight="500" fill="{t["muted"]}">Streak · Best</text>
  <text x="687" y="{89 + off}" font-family="{MONO}" font-size="17" font-weight="700" fill="{t["text"]}">{gh["current_streak"]}d <tspan font-size="12" font-weight="500" fill="{t["muted"]}">· {gh["longest_streak"]}d</tspan></text>

  <rect x="366" y="{107 + off}" width="144" height="42" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="378" y="{123 + off}" font-family="{SANS}" font-size="10" font-weight="500" fill="{t["muted"]}">Repositories</text>
  <text x="378" y="{140 + off}" font-family="{MONO}" font-size="14" font-weight="600" fill="{t["text"]}">{gh["public_repos"]}</text>

  <rect x="520.5" y="{107 + off}" width="144" height="42" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="532.5" y="{123 + off}" font-family="{SANS}" font-size="10" font-weight="500" fill="{t["muted"]}">PRs · Issues</text>
  <text x="532.5" y="{140 + off}" font-family="{MONO}" font-size="14" font-weight="600" fill="{t["text"]}">{gh["pull_requests"]} · {gh["issues"]}</text>

  <rect x="675" y="{107 + off}" width="144" height="42" rx="10" fill="{t["card"]}" stroke="{t["border"]}"/>
  <text x="687" y="{123 + off}" font-family="{SANS}" font-size="10" font-weight="500" fill="{t["muted"]}">30d Daily Avg</text>
  <text x="687" y="{140 + off}" font-family="{MONO}" font-size="14" font-weight="600" fill="{t["text"]}">{gh["avg_30d"]:.1f}</text>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="6" rx="3" fill="{t["bar_muted"]}"/>
  {"".join(bar_segs)}
  {"".join(lang_leg)}

  <!-- Band 4: 30d Waveform (Log Scale) -->
  <line x1="26" y1="{210 + off}" x2="819" y2="{210 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="26" y="{234 + off}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Contribution activity <tspan font-weight="400" fill="{t["muted"]}">· Last 30 days</tspan></text>
  <text x="819" y="{234 + off}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["muted"]}"><tspan fill="{t["text"]}" font-weight="600">{gh["total_30d"]}</tspan> total  ·  <tspan fill="{t["accent"]}" font-weight="600">{peak_cnt}</tspan> peak  ·  <tspan fill="{t["text"]}" font-weight="600">{gh["active_30d"]}/30</tspan> active</text>

  <line x1="44" y1="{wy_top}" x2="818" y2="{wy_top}" stroke="{t["border_soft"]}" stroke-width="0.9" stroke-dasharray="3 4"/>
  <line x1="44" y1="{mid_y}" x2="818" y2="{mid_y}" stroke="{t["border_soft"]}" stroke-width="0.9" stroke-dasharray="3 4"/>
  <line x1="44" y1="{wy_bot}" x2="818" y2="{wy_bot}" stroke="{t["border"]}" stroke-width="1"/>
  <text x="36" y="{wy_top + 3}" text-anchor="end" font-family="{MONO}" font-size="8.5" fill="{t["faint"]}">{y_scale_max}</text>
  <text x="36" y="{mid_y + 3}" text-anchor="end" font-family="{MONO}" font-size="8.5" fill="{t["faint"]}">{mid_log_val}</text>
  <text x="36" y="{wy_bot + 3}" text-anchor="end" font-family="{MONO}" font-size="8.5" fill="{t["faint"]}">0</text>

  <path d="{area_d}" fill="url(#dashArea_{theme_name})"/>
  <path d="{line_d}" fill="none" stroke="url(#dashLine_{theme_name})" stroke-width="2.2" stroke-linecap="round"/>
  {wave_dots}
  {x_ticks}

  <!-- Band 5: Commit Schedule & Recently Committed Repositories -->
  <line x1="26" y1="{348 + off}" x2="819" y2="{348 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="26" y="{372 + off}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Commit schedule</text>
  <text x="414" y="{372 + off}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t["faint"]}">Peak: {peak_bucket}</text>
  {"".join(bucket_rows)}
  {"".join(wd_pills)}

  <line x1="432" y1="{360 + off}" x2="432" y2="{516 + off}" stroke="{t["border_soft"]}" stroke-width="1"/>
  <text x="450" y="{372 + off}" font-family="{SANS}" font-size="13.5" font-weight="600" fill="{t["text"]}">Recently committed</text>
  <text x="819" y="{372 + off}" text-anchor="end" font-family="{MONO}" font-size="9.5" fill="{t["faint"]}">{html.escape(gh.get("latest_commit_label") or "")}</text>
  {"".join(repo_cards)}

  {waka_svg}
  {platforms_svg}
</svg>
'''


def render_plain_profile_md(
    gh: dict[str, Any],
    waka: dict[str, Any] | None,
    platforms: list[dict[str, Any]],
) -> str:
    days = gh.get("last_30") or []
    peak_day = max(days, key=lambda d: d["contributionCount"]) if days else {"date": "", "contributionCount": 0}
    buckets_dict = gh.get("buckets") or {}
    total_bucket = sum(buckets_dict.values()) or 1
    bucket_windows = [("Morning", "06h–12h"), ("Daytime", "12h–18h"), ("Evening", "18h–24h"), ("Night", "00h–06h")]
    wd_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    lines = [
        "# Ítalo Leal (`@Lealwbs`)",
        "",
        "> Machine-readable plain-text mirror of the live GitHub Profile (`README.md`). Auto-synced by GitHub Actions.",
        "",
        f"- **Synced:** {gh['synced_date']}",
        "- **Taglines:** Information Systems · UFMG | SAP ABAP Consultant · Seidor Brasil | AI Agents, Automation & Systems Engineering",
        "- **Location:** Contagem / Belo Horizonte, MG, Brazil",
        "",
        "## Links & Socials",
        "- **GitHub:** https://github.com/Lealwbs",
        "- **LinkedIn:** https://www.linkedin.com/in/lealwbs",
        "- **Email:** mailto:italoleallanasantos@gmail.com",
        "- **Lattes CNPq:** http://lattes.cnpq.br/4756437356720090",
        "- **Instagram:** https://www.instagram.com/Lealwbs",
        "- **Discord:** `Leal#8905` (https://discord.com/users/Leal#8905)",
        "- **LeetCode:** https://leetcode.com/u/italoleallanasantos",
        "- **Hugging Face:** https://huggingface.co/Lealwbs",
        "- **Kaggle:** https://www.kaggle.com/lealwbs",
        "- **Chess.com:** https://www.chess.com/member/lealz",
        "- **Lichess:** https://lichess.org/@/Lealz",
        "",
        "## Overview",
        "- **Academic Average (NSG):** 85.1 / 100",
        "- **Student:** Undergraduate 7th Semester (Information Systems, UFMG)",
        "- **Founder:** Coletivo Voa Voa ENEM Prep",
        "- **Alumni:** Aspire Leaders Program '25",
        "- **Member:** Stanford LC Talent Network",
        "- **President:** Liga ISMART UFMG",
        "",
        "## Tech Stack (34 Tools)",
        "- **AI, ML & Data:** Python, PyTorch, scikit-learn, Hugging Face, Google Gemini, Jupyter, Pandas, NumPy, Apache Spark, FastAPI, Streamlit",
        "- **Databases, Cloud & Enterprise:** SQL, PostgreSQL, Supabase, Docker, Amazon Web Services (AWS), Azure, SAP (ABAP / S/4HANA)",
        "- **Systems, Web & Dev Workflow:** C, C++, Java, TypeScript, JavaScript, Next.js, React, Tailwind CSS, Node.js, Vercel, Linux, Git, GitHub, Google Antigravity, Codex, Visual Studio Code",
        "",
        "## GitHub Activity",
        f"- **All-Time Contributions:** {gh['all_time_contributions']:,}",
        f"- **Commits (1y):** {gh['commits_1y']:,}",
        f"- **Current Streak / Longest Streak:** {gh['current_streak']}d / {gh['longest_streak']}d",
        f"- **Public Repositories:** {gh['public_repos']}",
        f"- **Pull Requests / Issues:** {gh['pull_requests']} / {gh['issues']}",
        f"- **30d Daily Average:** {gh['avg_30d']:.1f}",
        f"- **Stars / Followers:** {gh['total_stars']} / {gh['followers']}",
        f"- **Last 30 Days:** {gh['total_30d']} total, {peak_day['contributionCount']} peak ({fmt_ddmm(peak_day['date'])}), {gh['active_30d']}/30 active days",
        "- **Top Repository Languages:** " + ", ".join(f"{l['name']} ({l['pct']:.0f}%)" for l in gh["top_gh_langs"]),
        "",
        "## Commit Schedule (BRT / UTC-3)",
        "- **Time Buckets:** " + " | ".join(
            f"{lbl} ({win}): {buckets_dict.get(lbl, 0)} ({(buckets_dict.get(lbl, 0) / total_bucket) * 100:.1f}%)"
            for lbl, win in bucket_windows
        ),
        "- **Weekday Distribution:** " + " | ".join(f"{d}: {c}" for d, c in zip(wd_names, gh["mon_sun"])),
        "",
        "## Recently Committed Repositories",
    ]
    for r in gh["recent_repos"]:
        star_s = f" | ★{r['stars']}" if r["stars"] > 0 else ""
        fork_s = f" | {r['forks']} forks" if r.get("forks", 0) > 0 else ""
        lines.append(f"- **{r['name']}** ({r['language']}{star_s}{fork_s}, {r['commit_date']}): {r['description']}")

    if waka and waka.get("languages"):
        coding_langs, _ = filter_coding_languages(waka["languages"])
        lines.extend(["", "## WakaTime Telemetry"])
        w_oss = waka.get("operating_systems") or []
        all_time_sec = float(w_oss[0].get("total_seconds") or 0) if w_oss else 0.0
        all_time_lbl = fmt_dur(all_time_sec) if all_time_sec > 0 else (waka.get("total_text") or "")
        daily_avg_lbl = fmt_dur(float(waka.get("daily_avg_sec") or 0))
        bd = waka.get("best_day") or {}
        best_lbl = fmt_dur(float(bd.get("total_seconds") or 0))
        lines.append(f"- **Pace:** All time: {all_time_lbl} | Daily avg: {daily_avg_lbl} | Best day: {best_lbl} ({bd.get('date') or ''})")
        lines.append("- **Coding Languages:** " + ", ".join(f"{x['name']} ({fmt_dur(x['total_seconds'])}, {x['coding_pct']:.1f}%)" for x in coding_langs))
        if waka.get("editors"):
            lines.append("- **Editors & AI Tools:** " + ", ".join(f"{e['name']} ({fmt_dur(float(e.get('total_seconds') or 0))}, {float(e.get('percent') or 0):.1f}%)" for e in waka["editors"]))

    if platforms:
        lines.extend(["", "## External Platforms (Live)"])
        for p in platforms:
            meta = f" | {p['right_meta']}" if p.get("right_meta") else ""
            lines.append(f"- **{p['name']} (`{p['handle']}`):** {p['hero_val']} {p['hero_unit']}{meta} ({p['sub_text']})")

    lines.append("")
    return "\n".join(lines)


def render_llms_txt(
    gh: dict[str, Any],
    waka: dict[str, Any] | None,
    platforms: list[dict[str, Any]],
) -> str:
    plat_summary = " | ".join(f"{p['name']}: {p['hero_val']} {p['hero_unit']} ({p['sub_text']})" for p in platforms)
    return "\n".join([
        "# Ítalo Leal (@Lealwbs)",
        "",
        "> Information Systems Undergraduate (7th Semester, UFMG, NSG 85.1/100), SAP ABAP Consultant at Seidor Brasil, President of Liga ISMART UFMG, Founder of Coletivo Voa Voa ENEM Prep, Harvard Aspire Leaders '25 Alumni, and Stanford LC Talent Network Member.",
        "",
        "## Primary Text Dossier",
        "- [PROFILE.md](https://github.com/Lealwbs/Lealwbs/blob/main/PROFILE.md): Full machine-readable markdown telemetry (Overview, 34-tool Tech Stack, GitHub stats, Commit schedule, Recent repos, WakaTime, LeetCode & Chess ratings).",
        "- [README.md](https://github.com/Lealwbs/Lealwbs/blob/main/README.md): Visual SVG GitHub profile dashboard.",
        "",
        "## Live Snapshot",
        f"- Synced: {gh['synced_date']}",
        f"- GitHub: {gh['all_time_contributions']:,} all-time contributions, {gh['commits_1y']:,} commits (1y), {gh['current_streak']}d streak (best {gh['longest_streak']}d), {gh['public_repos']} public repos",
        f"- Platforms: {plat_summary}" if plat_summary else "- Platforms: GitHub",
        "- Handles: GitHub @Lealwbs | LeetCode @italoleallanasantos | Hugging Face @Lealwbs | Kaggle @lealwbs | Chess.com @lealz | Lichess @Lealz",
        "",
    ])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gh_token = get_github_token()
    gh_metrics = fetch_github_metrics(OWNER, gh_token)

    waka_key = os.environ.get("WAKATIME_API_KEY", "").strip()
    waka_metrics = fetch_wakatime_metrics(waka_key) if waka_key else None
    platforms = fetch_platform_metrics()

    if "--preview-waka" in sys.argv and waka_metrics is None:
        waka_metrics = {
            "range_label": "All time",
            "total_text": "247 hrs 3 mins",
            "timezone": "America/Sao_Paulo",
            "daily_avg_text": "1 hr 48 mins",
            "daily_avg_sec": 6480,
            "best_day": {"date": "16/10", "text": "6 hrs 32 mins", "total_seconds": 23520},
            "categories": [
                {"name": "Coding", "total_seconds": 394200, "percent": 44.3},
            ],
            "languages": [
                {"name": "Markdown", "total_seconds": 232260},
                {"name": "Other", "total_seconds": 127080},
                {"name": "Python", "total_seconds": 99720},
                {"name": "C", "total_seconds": 97560},
                {"name": "ABAP", "total_seconds": 64500},
                {"name": "JavaScript", "total_seconds": 60600},
                {"name": "TypeScript", "total_seconds": 30480},
                {"name": "Standard ML", "total_seconds": 11880},
                {"name": "Java", "total_seconds": 11100},
            ],
            "editors": [
                {"name": "Antigravity IDE", "total_seconds": 485040, "percent": 54.5},
                {"name": "VS Code", "total_seconds": 221400, "percent": 24.9},
                {"name": "Antigravity Desktop", "total_seconds": 120360, "percent": 13.5},
                {"name": "Copilot CLI", "total_seconds": 37560, "percent": 4.2},
                {"name": "Codex Vscode", "total_seconds": 17580, "percent": 2.0},
                {"name": "Eclipse", "total_seconds": 5640, "percent": 0.6},
                {"name": "Copilot", "total_seconds": 1020, "percent": 0.1},
            ],
            "operating_systems": [
                {"name": "Windows", "total_seconds": 890000, "percent": 100.0},
            ],
        }
        for theme in ("dark", "light"):
            (pathlib.Path("/tmp") / f"preview-hero-{theme}.svg").write_text(
                render_hero_svg(theme), encoding="utf-8"
            )
            (pathlib.Path("/tmp") / f"preview-v2-{theme}.svg").write_text(
                render_unified_readme_svg(gh_metrics, waka_metrics, theme, platforms), encoding="utf-8"
            )
        (pathlib.Path("/tmp") / "preview-PROFILE.md").write_text(
            render_plain_profile_md(gh_metrics, waka_metrics, platforms), encoding="utf-8"
        )
        print(f"Wrote local QA preview SVGs + markdown to /tmp/preview-* (platforms={len(platforms)})")
        return

    for theme in ("dark", "light"):
        (OUT_DIR / f"hero-{theme}.svg").write_text(
            render_hero_svg(theme), encoding="utf-8"
        )
        (OUT_DIR / f"readme-{theme}.svg").write_text(
            render_unified_readme_svg(gh_metrics, waka_metrics, theme, platforms), encoding="utf-8"
        )

    (ROOT / "PROFILE.md").write_text(
        render_plain_profile_md(gh_metrics, waka_metrics, platforms), encoding="utf-8"
    )
    (ROOT / "llms.txt").write_text(
        render_llms_txt(gh_metrics, waka_metrics, platforms), encoding="utf-8"
    )

    print(
        f"Generated Hero + Unified dashboard SVGs + PROFILE.md/llms.txt for {OWNER}: "
        f"{gh_metrics['all_time_contributions']} all-time contribs, "
        f"waka={'yes' if waka_metrics else 'no'}, platforms={len(platforms)}."
    )


if __name__ == "__main__":
    main()
