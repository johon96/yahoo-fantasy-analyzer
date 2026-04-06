"""yfantasy export — export player data to CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from yfantasy.client import YahooClient
from yfantasy.config import Config

console = Console()

export_app = typer.Typer(help="Export league data to CSV.")


@export_app.callback(invoke_without_command=True)
def export_players(
    ctx: typer.Context,
    league: Optional[str] = typer.Option(None, "--league", "-l", help="League key"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output CSV path"),
    count: int = typer.Option(500, "--count", "-c", help="Max players to fetch"),
) -> None:
    """Export league player stats to CSV."""
    if ctx.invoked_subcommand is not None:
        return

    config = Config()
    league_key = league or config.get("defaults", "league_key")
    if not league_key:
        console.print("[red]No league selected.[/] Run `yfantasy league select`.")
        raise typer.Exit(1)

    if output is None:
        safe = league_key.replace(".", "_")
        output = f"{safe}_analysis.csv"

    client = YahooClient(config, use_cache=False)
    lg = client.get_league(league_key)

    console.print(f"[bold]Exporting:[/] {lg.name} ({league_key})")
    console.print(f"[bold]Output:[/] {output}")

    # --- Fetch draft results -------------------------------------------------
    draft_dict = _fetch_draft(client, league_key)

    # --- Fetch teams ---------------------------------------------------------
    teams_dict = _fetch_teams(client, league_key)

    # --- Fetch players in batches --------------------------------------------
    all_players = _fetch_all_players(client, league_key, lg, count)

    if not all_players:
        console.print("[red]No players found.[/]")
        raise typer.Exit(1)

    # --- Write CSV -----------------------------------------------------------
    _write_csv(output, all_players, draft_dict, teams_dict, lg)

    console.print(f"\n[green]Exported {len(all_players)} players to {output}[/]")


# -- data fetching -----------------------------------------------------------


def _fetch_draft(client: YahooClient, league_key: str) -> dict:
    """Fetch draft picks and return {player_key: {round, pick, team_key}}."""
    console.print("Fetching draft results...")
    try:
        resp = client._request(f"league/{league_key}/draftresults")
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if len(league_arr) < 2:
            return {}

        draft_obj = league_arr[1].get("draft_results", {})
        draft_dict: dict = {}
        for key in draft_obj:
            if key == "count":
                continue
            pick = draft_obj[key].get("draft_result", {})
            pk = pick.get("player_key", "")
            if pk:
                draft_dict[pk] = {
                    "round": pick.get("round", ""),
                    "pick": pick.get("pick", ""),
                    "team_key": pick.get("team_key", ""),
                }
        console.print(f"  Loaded {len(draft_dict)} draft picks")
        return draft_dict
    except Exception as e:
        console.print(f"  [yellow]Draft data unavailable: {e}[/]")
        return {}


def _fetch_teams(client: YahooClient, league_key: str) -> dict:
    """Fetch teams and return {team_key: {name, manager}}."""
    console.print("Fetching teams...")
    try:
        resp = client._request(f"league/{league_key}/teams")
        fc = resp.get("fantasy_content", {})
        league_arr = fc.get("league", [])
        if len(league_arr) < 2:
            return {}

        teams_obj = league_arr[1].get("teams", {})
        teams_dict: dict = {}
        for key in teams_obj:
            if key == "count":
                continue
            team_arr = teams_obj[key].get("team", [])
            if not isinstance(team_arr, list) or not team_arr:
                continue

            info_list = team_arr[0] if isinstance(team_arr[0], list) else team_arr
            tk = ""
            name = "Unknown"
            manager = "Unknown"
            for item in info_list:
                if isinstance(item, dict):
                    if "team_key" in item:
                        tk = item["team_key"]
                    if "name" in item:
                        name = item["name"]
                    if "managers" in item:
                        mgrs = item["managers"]
                        if isinstance(mgrs, list) and mgrs:
                            mgr = mgrs[0].get("manager", {})
                            manager = mgr.get("nickname", "Unknown")
                        elif isinstance(mgrs, dict):
                            mgr = mgrs.get("0", {}).get("manager", {})
                            manager = mgr.get("nickname", "Unknown")
            if tk:
                teams_dict[tk] = {"name": name, "manager": manager}

        console.print(f"  Loaded {len(teams_dict)} teams")
        return teams_dict
    except Exception as e:
        console.print(f"  [yellow]Team data unavailable: {e}[/]")
        return {}


def _fetch_all_players(
    client: YahooClient, league_key: str, lg, max_count: int
) -> list[dict]:
    """Fetch players with stats in batches of 25. Returns list of parsed dicts."""
    players: list[dict] = []
    batch_size = 25
    batches = (max_count + batch_size - 1) // batch_size

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching players...", total=batches)

        for batch in range(batches):
            start = batch * batch_size
            progress.update(task, description=f"Fetching players {start}-{start + batch_size - 1}...")

            try:
                endpoint = (
                    f"league/{league_key}/players;start={start};count={batch_size}"
                    f";sort=PTS;sort_type=season"
                    f";out=ownership,draft_analysis"
                    f"/stats;type=season;extra_stat_ids=0,19,22,25,27,29"
                )
                resp = client._request(endpoint)
            except Exception:
                break

            fc = resp.get("fantasy_content", {})
            league_arr = fc.get("league", [])
            if len(league_arr) < 2:
                break

            players_obj = league_arr[1].get("players", {})
            batch_count = 0

            for key in players_obj:
                if key == "count":
                    continue
                pdata = players_obj[key].get("player", [])
                if not isinstance(pdata, list) or not pdata:
                    continue

                parsed = _parse_player(pdata, lg)
                if parsed:
                    players.append(parsed)
                    batch_count += 1

            progress.advance(task)

            if batch_count == 0:
                break

    console.print(f"  Fetched {len(players)} players")
    return players


def _parse_player(pdata: list, lg) -> Optional[dict]:
    """Parse a single player's Yahoo JSON into a flat dict for CSV."""
    attrs = pdata[0] if isinstance(pdata[0], list) else [pdata[0]]

    # Extract basic info from attrs list
    info: dict = {
        "name": "", "player_key": "", "team": "", "position": "",
        "position_type": "", "status": "",
    }
    for a in attrs:
        if not isinstance(a, dict):
            continue
        if "name" in a:
            info["name"] = a["name"].get("full", "")
        if "player_key" in a:
            info["player_key"] = a["player_key"]
        if "editorial_team_abbr" in a:
            info["team"] = a["editorial_team_abbr"]
        if "display_position" in a:
            info["position"] = a["display_position"]
        if "position_type" in a:
            info["position_type"] = a["position_type"]
        if "status" in a and isinstance(a["status"], str):
            info["status"] = a["status"]
        if "percent_owned" in a:
            po = a["percent_owned"]
            if isinstance(po, list):
                for entry in po:
                    if isinstance(entry, dict) and "value" in entry:
                        info["pct_owned"] = entry["value"]
            elif isinstance(po, dict):
                info["pct_owned"] = po.get("value", "")

    # Ownership, draft_analysis, and stats live in pdata[1:], not inside attrs
    stats: dict[str, str] = {}
    fan_pts = 0.0
    for entry in pdata:
        if not isinstance(entry, dict):
            continue

        # Ownership (separate dict at top level of pdata)
        if "ownership" in entry:
            own = entry["ownership"]
            if isinstance(own, dict):
                info["owner_team_key"] = own.get("owner_team_key", "")

        # Draft analysis — Yahoo returns as a list of single-key dicts
        if "draft_analysis" in entry:
            da = entry["draft_analysis"]
            if isinstance(da, list):
                for item in da:
                    if isinstance(item, dict):
                        if "average_pick" in item:
                            info["adp"] = item["average_pick"]
                        if "percent_drafted" in item:
                            info["pct_drafted"] = item["percent_drafted"]
            elif isinstance(da, dict):
                info["adp"] = da.get("average_pick", "")
                info["pct_drafted"] = da.get("percent_drafted", "")

        # Stats
        if "player_stats" in entry:
            stat_list = entry["player_stats"].get("stats", [])
            for s in stat_list:
                sid = s.get("stat", {}).get("stat_id", "")
                val = s.get("stat", {}).get("value", "-")
                stats[str(sid)] = val
        if "player_points" in entry:
            try:
                fan_pts = float(entry["player_points"].get("total", 0))
            except (ValueError, TypeError):
                pass

    if not info["name"]:
        return None

    # Map stat IDs to names (NHL)
    # 1=G, 2=A, 5=PIM, 14=SOG, 19=W, 22=GA, 25=SV, 27=SO, 28=GS, 29=GP, 31=HIT, 32=BLK
    is_goalie = info["position_type"] == "G"
    # Stat 29=GP works for skaters in batch mode; stat 0=GP/GS works for goalies
    gp_val = stats.get("29", stats.get("0", "-"))
    goals = stats.get("1", "-")
    assists = stats.get("2", "-")
    pim = stats.get("5", "-")
    sog = stats.get("14", "-")
    hits = stats.get("31", "-")
    blk = stats.get("32", "-")
    wins = stats.get("19", "-")
    saves = stats.get("25", "-")
    ga = stats.get("22", "-")
    so = stats.get("27", "-")

    # Derived: Points = G+A
    pts = "-"
    try:
        if goals != "-" and assists != "-":
            pts = str(int(goals) + int(assists))
    except (ValueError, TypeError):
        pass

    # Derived: SV%
    sv_pct = "-"
    try:
        sv = float(saves) if saves != "-" else 0
        ga_f = float(ga) if ga != "-" else 0
        if sv + ga_f > 0:
            sv_pct = f"{sv / (sv + ga_f) * 100:.1f}"
    except (ValueError, TypeError):
        pass

    # Derived: Fan Pts / GP
    fppg = "-"
    try:
        gp_f = float(gp_val) if gp_val not in ("-", "0") else 0
        if gp_f > 0:
            fppg = f"{fan_pts / gp_f:.2f}"
    except (ValueError, TypeError):
        pass

    info.update({
        "fan_pts": fan_pts,
        "gp": gp_val,
        "g": goals, "a": assists, "p": pts,
        "pim": pim, "sog": sog, "hit": hits, "blk": blk,
        "w": wins, "sv": saves, "sv_pct": sv_pct, "ga": ga, "so": so,
        "fppg": fppg,
    })

    return info


# -- CSV writing -------------------------------------------------------------

_CSV_HEADERS = [
    "Player", "Pos", "Team", "Rank", "Fan Pts",
    "Cur Team", "Owner",
    "Draft Team", "Draft Owner", "Rd", "Pick",
    "ADP", "% Draft",
    "GP", "G", "A", "P", "PIM", "SOG", "HIT", "BLK",
    "W", "SV", "SV%", "GA", "SO",
    "% Own", "Fan Pts/GP", "ID",
]


def _write_csv(
    output: str,
    players: list[dict],
    draft_dict: dict,
    teams_dict: dict,
    lg,
) -> None:
    """Write player data to CSV."""
    # Sort by fantasy points desc
    players.sort(key=lambda p: p.get("fan_pts", 0), reverse=True)

    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_HEADERS)
        writer.writeheader()

        for rank, p in enumerate(players, 1):
            pk = p.get("player_key", "")

            # Current ownership
            owner_tk = p.get("owner_team_key", "")
            cur_team = teams_dict.get(owner_tk, {}).get("name", "")
            cur_owner = teams_dict.get(owner_tk, {}).get("manager", "")

            # Draft info
            draft = draft_dict.get(pk, {})
            draft_tk = draft.get("team_key", "")
            draft_team = teams_dict.get(draft_tk, {}).get("name", "")
            draft_owner = teams_dict.get(draft_tk, {}).get("manager", "")

            # Convert player_key to game_code format
            display_id = pk
            if pk and "." in pk:
                parts = pk.split(".")
                if len(parts) >= 3:
                    gc = YahooClient.game_code_from_id(parts[0])
                    display_id = f"{gc}.{parts[1]}.{parts[2]}"

            # Format pct_drafted
            pct_drafted = p.get("pct_drafted", "")
            try:
                pct_drafted_f = float(pct_drafted)
                if pct_drafted_f <= 1:
                    pct_drafted = f"{pct_drafted_f * 100:.0f}"
            except (ValueError, TypeError):
                pass

            writer.writerow({
                "Player": p.get("name", ""),
                "Pos": p.get("position", ""),
                "Team": p.get("team", ""),
                "Rank": rank,
                "Fan Pts": p.get("fan_pts", 0),
                "Cur Team": cur_team,
                "Owner": cur_owner,
                "Draft Team": draft_team,
                "Draft Owner": draft_owner,
                "Rd": draft.get("round", ""),
                "Pick": draft.get("pick", ""),
                "ADP": p.get("adp", ""),
                "% Draft": pct_drafted,
                "GP": p.get("gp", "-"),
                "G": p.get("g", "-"),
                "A": p.get("a", "-"),
                "P": p.get("p", "-"),
                "PIM": p.get("pim", "-"),
                "SOG": p.get("sog", "-"),
                "HIT": p.get("hit", "-"),
                "BLK": p.get("blk", "-"),
                "W": p.get("w", "-"),
                "SV": p.get("sv", "-"),
                "SV%": p.get("sv_pct", "-"),
                "GA": p.get("ga", "-"),
                "SO": p.get("so", "-"),
                "% Own": p.get("pct_owned", ""),
                "Fan Pts/GP": p.get("fppg", "-"),
                "ID": display_id,
            })
