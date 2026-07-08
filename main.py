import asyncio
import os
import socket
import sys
import time
import traceback
import webbrowser
from pathlib import Path

import requests
import urllib3
from colr import color as colr
from InquirerPy import inquirer
from rich.console import Console as RichConsole

from src.colors import Colors
from src.config import Config
from src.configurator import configure
from src.constants import *
from src.content import Content
from src.dashboard_http import start_dashboard_http, get_dashboard_url
from src.errors import Error
from src.Loadouts import Loadouts
from src.logs import Logging
from src.names import Names
from src.player_stats import PlayerStats
from src.presences import Presences
from src.presences import get_party_state
from src.rank import Rank
from src.requestsV import Requests
from src.rpc import Rpc
from src.server import Server
from src.states.coregame import Coregame
from src.states.menu import Menu
from src.states.pregame import Pregame
from src.stats import Stats
from src.table import Table
from src.websocket import Ws
from src.os_info import get_os

from src.account_manager.account_manager import AccountManager
from src.account_manager.account_config import AccountConfig
from src.account_manager.account_auth import AccountAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STARTUP_CREDIT = "Optimized & Extended by h4y5 on Discord"
STARTUP_BANNER = f"VALORANT rank yoinker v{version} | {STARTUP_CREDIT}"

os.system(f"title {STARTUP_BANNER}")

server = ""
_loading_status_width = 0


def set_loading_status(message: str):
    global _loading_status_width
    status = f"[loading] {message}"
    _loading_status_width = max(_loading_status_width, len(status))
    print("\r" + status.ljust(_loading_status_width), end="", flush=True)


def set_loading_step(step: str, detail: str = "", log_func=None):
    message = f"{step}: {detail}" if detail else step
    set_loading_status(message)
    if log_func is not None:
        log_func(f"startup loading -> {message}")


def update_player_loading_status(status, loaded: int, total: int, name: str, agent: str, phase: str, elapsed_ms=None):
    elapsed_suffix = f" ({int(elapsed_ms)}ms)" if elapsed_ms is not None else ""
    status.update(
        f"Loading players... [{loaded}/{total}] {name} ({agent}) - {phase}{elapsed_suffix}"
    )


def clear_loading_status():
    global _loading_status_width
    if _loading_status_width <= 0:
        return
    print("\r" + (" " * _loading_status_width) + "\r", end="", flush=True)
    _loading_status_width = 0


def play_startup_animation():
    frames = ["█░░░░░░", "██░░░░░", "███░░░░", "████░░░", "█████░░", "██████░", "███████"]
    for frame in frames:
        print("\r" + f"[vRY] booting {frame}", end="", flush=True)
        time.sleep(0.06)
    print("\r" + " " * 40 + "\r", end="", flush=True)


def get_local_dashboard_uri(log_func):
    """Get embedded dashboard HTTP URL."""
    return get_dashboard_url(1101)  # Serve on different port from WebSocket (1100)


def load_dashboard_assets():
    """Load the dashboard CSS/JS from docs when available.

    Falls back to the embedded copies so packaged builds keep working if the
    docs folder is missing.
    """
    docs_dir = Path(__file__).resolve().parent / "docs"
    css_path = docs_dir / "style.css"
    js_path = docs_dir / "app.js"

    if css_path.exists() and js_path.exists():
        return (
            css_path.read_text(encoding="utf-8"),
            js_path.read_text(encoding="utf-8"),
        )

    from src.dashboard_http import DASHBOARD_CSS, DASHBOARD_JS

    return DASHBOARD_CSS, DASHBOARD_JS


def prompt_open_local_dashboard(log_func):
    uri = get_local_dashboard_uri(log_func)
    if not uri:
        return "[dashboard] local dashboard URL unavailable"

    try:
        should_open = inquirer.confirm(
            message="Open local dashboard?", default=True
        ).execute()
    except Exception as ex:
        log_func(f"dashboard prompt failed: {ex}")
        return "[dashboard] prompt failed"

    if should_open:
        try:
            webbrowser.open(uri)
            log_func(f"opened local dashboard: {uri}")
            return f"[dashboard] opened {uri}"
        except Exception as ex:
            log_func(f"failed to open local dashboard: {ex}")
            return "[dashboard] failed to open local dashboard"
    else:
        log_func("skipped opening local dashboard")
        return "[dashboard] skipped opening local dashboard"


def program_exit(status: int):  # so we don't need to import the entire sys module
    log(f"exited program with error code {status}")
    raise sys.exit(status)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(("10.254.254.254", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


try:
    Logging = Logging()
    log = Logging.log

    # OS Logging
    log(f"Operating system: {get_os()}\n")

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--config":
            configure()
            run_app = inquirer.confirm(
                message="Do you want to run vRY now?", default=True
            ).execute()
            if run_app:
                os.system("cls")
            else:
                os._exit(0)
        else:
            os.system("cls")
    except Exception as e:
        print("Something went wrong while running configurator!")
        log(f"configurator encountered an error")
        log(str(traceback.format_exc()))
        input("press enter to exit...\n")
        os._exit(1)

    acc_manager = AccountManager(log, AccountConfig, AccountAuth, NUMBERTORANKS)

    ErrorSRC = Error(log, acc_manager)

    set_loading_step("service status", "checking remote API availability", log)
    Requests.check_status()
    set_loading_step("requests client", f"initializing core API bindings (v{version})", log)
    Requests = Requests(version, log, ErrorSRC)

    set_loading_step("configuration", "loading config.json and feature flags", log)
    cfg = Config(log)

    set_loading_step("content metadata", "priming static content service", log)
    content = Content(Requests, log)

    set_loading_step("stat services", "initializing rank and player stat providers", log)
    rank = Rank(Requests, log, content, before_ascendant_seasons)
    pstats = PlayerStats(Requests, log, cfg)

    namesClass = Names(Requests, log)

    presences = Presences(Requests, log)

    menu = Menu(Requests, log, presences)
    pregame = Pregame(Requests, log)
    coregame = Coregame(Requests, log)

    set_loading_step("websocket server", "starting local feed broadcaster", log)
    Server = Server(log, ErrorSRC)
    Server.start_server()
    set_loading_step("dashboard", "preparing local dashboard service", log)

    set_loading_step("game content", "loading agents and maps", log)
    agent_dict = content.get_all_agents()
    agent_icon_dict = content.get_all_agent_icons()
    set_loading_step(
        "game content",
        f"loaded {len(agent_dict)} agents and {len(agent_icon_dict)} agent icons",
        log,
    )

    map_info = content.get_all_maps()
    map_urls = content.get_map_urls(map_info)
    map_splashes = content.get_map_splashes(map_info)
    set_loading_step(
        "game content",
        f"loaded {len(map_info)} maps, {len(map_urls)} map URLs, {len(map_splashes)} splash assets",
        log,
    )

    current_map = coregame.get_current_map(map_urls, map_splashes)

    colors = Colors(log, hide_names, agent_dict, AGENTCOLORLIST)

    loadoutsClass = Loadouts(Requests, log, colors, Server, current_map)
    table = Table(cfg, log)

    stats = Stats()

    # Send match history to clients
    import time
    time.sleep(0.5)  # Wait for server to be ready
    Server.send_payload("matchHistory", {"matches": stats.read_matches()})

    if cfg.get_feature_flag("discord_rpc"):
        rpc = Rpc(map_urls, gamemodes, colors, log)
    else:
        rpc = None

    Wss = Ws(Requests.lockfile, Requests, cfg, colors, hide_names, Server, rpc)
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_forever()

    play_startup_animation()

    log(STARTUP_BANNER)
    clear_loading_status()
    print(STARTUP_BANNER)
    
    # Load dashboard CSS/JS from docs when available, with embedded fallback.
    try:
        dashboard_css, dashboard_js = load_dashboard_assets()
        start_dashboard_http(1101, dashboard_css, dashboard_js, log)
    except Exception as ex:
        log(f"failed to start dashboard HTTP server: {ex}")
    
    dashboard_status_line = prompt_open_local_dashboard(log)

    set_loading_step("startup", "fetching weapon skin catalog", log)
    try:
        valoApiSkins = requests.get("https://valorant-api.com/v1/weapons/skins", timeout=6)
    except requests.exceptions.RequestException as ex:
        log(f"weapons/skins api fetch failed on startup: {ex}")
        valoApiSkins = requests.Response()
        valoApiSkins._content = b'{"data": []}'
        valoApiSkins.status_code = 200

    set_loading_step("startup", "loading current season content", log)
    gameContent = content.get_content()
    set_loading_step("startup", "resolving season and previous season IDs", log)
    seasonID = content.get_latest_season_id(gameContent)
    previousSeasonID = content.get_previous_season_id(gameContent)
    clear_loading_status()
    if dashboard_status_line:
        print(dashboard_status_line)
    print("[startup] initial data ready. Waiting for game state updates...")
    time.sleep(3)
    os.system("cls" if os.name == "nt" else "clear")
    lastGameState = ""

    # Cache rank+stats per player for the current match so PREGAME data can be reused in INGAME
    match_player_cache = {
        "match_id": None,
        "players": {},  # puuid -> {"playerRank", "previousPlayerRank", "ppstats", "ts"}
    }
    MATCH_PLAYER_CACHE_TTL_SECONDS = 300  # safety TTL

    def reset_match_player_cache(match_id=None):
        match_player_cache["match_id"] = match_id
        match_player_cache["players"] = {}

    def ensure_match_player_cache(match_id):
        if not match_id:
            return

        # New match => reset cache
        if match_player_cache["match_id"] != match_id:
            reset_match_player_cache(match_id)
            return

        # TTL cleanup (safety)
        now = time.time()
        expired = []
        for puuid, cached in match_player_cache["players"].items():
            ts = cached.get("ts", now)
            if (now - ts) > MATCH_PLAYER_CACHE_TTL_SECONDS:
                expired.append(puuid)

        for puuid in expired:
            del match_player_cache["players"][puuid]

    def get_or_fetch_rank_and_stats(player_subject, current_match_id):
        if current_match_id:
            ensure_match_player_cache(current_match_id)
            cached = match_player_cache["players"].get(player_subject)
            if cached is not None:
                return (
                    cached["playerRank"],
                    cached["previousPlayerRank"],
                    cached["ppstats"],
                )

        # Cache miss -> fetch
        playerRank = rank.get_rank(player_subject, seasonID)
        previousPlayerRank = rank.get_rank(player_subject, previousSeasonID)
        ppstats = pstats.get_stats(player_subject)

        if current_match_id and match_player_cache["match_id"] == current_match_id:
            match_player_cache["players"][player_subject] = {
                "playerRank": dict(playerRank) if isinstance(playerRank, dict) else playerRank,
                "previousPlayerRank": dict(previousPlayerRank) if isinstance(previousPlayerRank, dict) else previousPlayerRank,
                "ppstats": dict(ppstats) if isinstance(ppstats, dict) else ppstats,
                "ts": time.time(),
            }

        return playerRank, previousPlayerRank, ppstats

    # Cache recent streak computations to avoid hammering PD endpoints every loop.
    player_streak_cache = {}  # puuid -> {"data": {type,count,sample}, "ts": float}
    PLAYER_STREAK_CACHE_TTL_SECONDS = 60
    STREAK_SAMPLE_GAMES = 20

    def _extract_outcome_from_comp_update(match_entry):
        if not isinstance(match_entry, dict):
            return None

        for key in ("IsWin", "isWin", "Won", "won", "Win", "win"):
            value = match_entry.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)

        # Competitive updates always include RR movement; this is the most reliable signal.
        rr_earned = match_entry.get("RankedRatingEarned")
        try:
            rr_delta = int(rr_earned)
            if rr_delta > 0:
                return True
            if rr_delta < 0:
                return False
        except (TypeError, ValueError):
            pass

        # Fallback to tier movement if RR is unavailable.
        before_tier = match_entry.get("TierBeforeUpdate")
        after_tier = match_entry.get("TierAfterUpdate")
        try:
            before_tier = int(before_tier)
            after_tier = int(after_tier)
            if after_tier > before_tier:
                return True
            if after_tier < before_tier:
                return False
        except (TypeError, ValueError):
            pass

        return None

    def get_recent_streak_for_player(puuid, max_games=STREAK_SAMPLE_GAMES):
        now = time.time()
        cached = player_streak_cache.get(str(puuid))
        if cached and (now - cached.get("ts", now)) <= PLAYER_STREAK_CACHE_TTL_SECONDS:
            return cached.get("data", {"type": "none", "count": 0, "sample": 0, "wins": 0, "losses": 0, "recent": []})

        streak_data = {"type": "none", "count": 0, "sample": 0, "wins": 0, "losses": 0, "recent": []}
        try:
            comp_response = Requests.fetch(
                "pd",
                f"/mmr/v1/players/{puuid}/competitiveupdates?startIndex=0&endIndex={max_games}&queue=competitive",
                "get",
                rate_limit_seconds=1,
            )
            if hasattr(comp_response, "status_code") and comp_response.status_code == 404:
                player_streak_cache[str(puuid)] = {"data": streak_data, "ts": now}
                return streak_data

            comp_json = comp_response.json() if hasattr(comp_response, "json") else {}
            entries = comp_json.get("Matches", []) if isinstance(comp_json, dict) else []
            outcomes = []

            for entry in entries:
                outcome = _extract_outcome_from_comp_update(entry)
                if outcome is None:
                    continue

                outcomes.append(bool(outcome))
                if len(outcomes) >= max_games:
                    break

            if outcomes:
                latest_outcome = outcomes[0]
                streak_count = 0
                for result in outcomes:
                    if result == latest_outcome:
                        streak_count += 1
                    else:
                        break

                streak_data = {
                    "type": "win" if latest_outcome else "loss",
                    "count": streak_count,
                    "sample": len(outcomes),
                    "wins": sum(1 for result in outcomes if result),
                    "losses": sum(1 for result in outcomes if not result),
                    "recent": ["W" if result else "L" for result in outcomes[:10]],
                }
        except Exception as ex:
            log(f"streak competitive updates fetch failed for {puuid}: {ex}")

        player_streak_cache[str(puuid)] = {"data": streak_data, "ts": now}
        return streak_data

    richConsole = RichConsole()

    firstTime = True
    firstPrint = True
    lastFeedSignature = None
    while True:
        table.clear()
        table.set_default_field_names()
        table.reset_runtime_col_flags()

        # check if short ranks should be used
        if cfg.get_feature_flag("short_ranks"):
            Ranks = SHORT_NUMBERTORANKS
        else:
            Ranks = NUMBERTORANKS

        try:

            # loop = asyncio.get_event_loop()
            # loop.run_until_complete(Wss.conntect_to_websocket())
            # if firstTime:
            #     loop = asyncio.new_event_loop()
            #     asyncio.set_event_loop(loop)
            #     game_state = loop.run_until_complete(Wss.conntect_to_websocket(game_state))
            if firstTime:
                run = True
                while run:
                    presence = presences.get_presence()
                    private_presence = presences.get_private_presence(presence)
                    # wait until your own valorant presence is initialized
                    if private_presence is not None:
                        if cfg.get_feature_flag("discord_rpc"):
                            rpc.set_rpc(private_presence)
                        game_state = presences.get_game_state(presence)
                        if game_state is not None:
                            run = False
                    time.sleep(2)
                log(f"first game state: {game_state}")
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                previous_game_state = game_state
                game_state = loop.run_until_complete(
                    Wss.recconect_to_websocket(game_state)
                )
                # We invalidate the cached responses when going from any state to menus
                if previous_game_state != game_state and game_state == "MENUS":
                    rank.invalidate_cached_responses()
                    reset_match_player_cache()
                    if hasattr(pstats, "clear_runtime_cache"):
                        pstats.clear_runtime_cache()
                log(f"new game state: {game_state}")
                loop.close()
            firstTime = False
            # loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(loop)
            # loop.run_until_complete()
        except TypeError:
            game_state = "DISCONNECTED"
            reset_match_player_cache()
            if hasattr(pstats, "clear_runtime_cache"):
                pstats.clear_runtime_cache()
            lastFeedSignature = None

        if game_state == "DISCONNECTED":
            richConsole.print("[yellow]Disconnected from Valorant. Attempting to reconnect...[/yellow]")
            # Loop waits for the Valorant client to respond
            while True:
                # Rereads the lockfile
                Requests.lockfile = Requests.get_lockfile()

                if Requests.lockfile is None:
                    time.sleep(5)
                    continue

                presence_check = presences.get_presence()
                
                if presence_check is not None:
                    break 
                
                time.sleep(5)

            richConsole.print("[green]Reconnected successfully! Loading...[/green]")
            
            Requests.get_headers(refresh=True)

            Wss = Ws(Requests.lockfile, Requests, cfg, colors, hide_names, Server, rpc)

            firstTime = True 
            lastGameState = ""
            lastFeedSignature = None
            reset_match_player_cache()
            if hasattr(pstats, "clear_runtime_cache"):
                pstats.clear_runtime_cache()
            continue

        if True:
            log(f"getting new {game_state} scoreboard")
            previous_cli_state = lastGameState
            lastGameState = game_state
            game_state_dict = {
                "INGAME": color("In-Game", fore=(241, 39, 39)),
                "PREGAME": color("Agent Select", fore=(103, 237, 76)),
                "MENUS": color("In-Menus", fore=(238, 241, 54)),
            }

            if (not firstPrint) and cfg.get_feature_flag("pre_cls"):
                os.system("cls")
                if previous_cli_state == "PREGAME" and game_state == "INGAME":
                    set_loading_status("INGAME: match started, preparing player data...")

            is_leaderboard_needed = False
            
            # get new presence
            presence = presences.get_presence()
            priv_presence = presences.get_private_presence(presence)
            
            party_state = get_party_state(priv_presence, "")
            if not party_state:
                log("ERROR: Unknown presence API structure in 'main'.")
            
            if (
                priv_presence["provisioningFlow"] == "CustomGame"
                or party_state == "CUSTOM_GAME_SETUP"
            ):
                gamemode = "Custom Game"
            else:
                gamemode = gamemodes.get(priv_presence["queueId"])

            heartbeat_data = {
                "time": int(time.time()),
                "state": game_state,
                "mode": gamemode,
                "server_id": "",
                "match_id": "",
                "tracker_match_url": "",
                "puuid": Requests.puuid,
                "players": {},
            }

            if game_state == "INGAME":
                set_loading_status("INGAME: fetching core game stats...")
                coregame_stats = coregame.get_coregame_stats()
                if coregame_stats == None:
                    continue
                coregame_match_id = (
                    coregame_stats.get("MatchID")
                    or getattr(coregame, "match_id", None)
                    or coregame.get_coregame_match_id()
                )
                heartbeat_data["match_id"] = coregame_match_id
                heartbeat_data["tracker_match_url"] = (
                    f"https://tracker.gg/valorant/match/{coregame_match_id}"
                    if coregame_match_id else ""
                )
                ensure_match_player_cache(coregame_match_id)
                Players = coregame_stats["Players"]
                # data for chat to function
                partyMembers = menu.get_party_members(Requests.puuid, presence)
                partyMembersList = [a["Subject"] for a in partyMembers]

                stats.save_match_id(coregame_match_id, Players)

                players_data = {}
                players_data.update({"ignore": partyMembersList})
                for player in Players:
                    if player["Subject"] == Requests.puuid:
                        if cfg.get_feature_flag("discord_rpc"):
                            rpc.set_data({"agent": player["CharacterID"]})
                    players_data.update(
                        {
                            player["Subject"]: {
                                "team": player["TeamID"],
                                "agent": player["CharacterID"],
                                "streamer_mode": player["PlayerIdentity"]["Incognito"],
                            }
                        }
                    )
                Wss.set_player_data(players_data)

                server = coregame_stats.get("GamePodID", "")
                if server:
                    server_parts = server.split('.')
                    heartbeat_data["server_id"] = '.'.join(server_parts[2:]) if len(server_parts) > 2 else server
                else:
                    heartbeat_data["server_id"] = ""

                set_loading_status("INGAME: resolving player names and presence...")
                presences.wait_for_presence(namesClass.get_players_puuid(Players))
                names = namesClass.get_names_from_puuids(Players)
                try:
                    set_loading_status("INGAME: loading player cosmetics...")
                    loadouts_arr = loadoutsClass.get_match_loadouts(
                        coregame_match_id,
                        Players,
                        cfg.weapon,
                        valoApiSkins,
                        names,
                        state="game",
                    )
                    if not loadouts_arr or len(loadouts_arr) < 2:
                        raise ValueError("invalid loadout response")
                    loadouts = loadouts_arr[0]
                    loadouts_data = loadouts_arr[1]
                except Exception as ex:
                    log(f"loadout fetch failed in INGAME; continuing without loadouts: {ex}")
                    loadouts = {}
                    loadouts_data = {"Players": {}}
                # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                isRange = False
                playersLoaded = 1

                heartbeat_data["map"] = (map_urls[coregame_stats["MapID"].lower()],)
                clear_loading_status()
                with richConsole.status("Loading Players...") as status:
                    partyOBJ = menu.get_party_json(
                        namesClass.get_players_puuid(Players), presence
                    )
                    # log(f"retrieved names dict: {names}")
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    Players.sort(key=lambda Players: Players["TeamID"], reverse=True)
                    partyCount = 0
                    partyNum = 0
                    partyIcons = {}
                    lastTeamBoolean = False
                    lastTeam = "Red"

                    already_played_with = []
                    stats_data = stats.read_data()

                    for p in Players:
                        if p["Subject"] == Requests.puuid:
                            allyTeam = p["TeamID"]
                    for player in Players:
                        loading_name = names.get(player["Subject"], "Unknown").split("#", 1)[0]
                        loading_agent = agent_dict.get(player.get("CharacterID", "").lower(), "Unknown")
                        current_index = playersLoaded
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "reading history and party data",
                        )
                        playersLoaded += 1
                        history_started = time.perf_counter()

                        played_with_count = 0
                        last_played_seconds_ago = None
                        last_played_agent = ""
                        last_played_team = ""

                        if player["Subject"] in stats_data.keys():
                            curr_player_stat = stats_data[player["Subject"]][-1]
                            i = 1
                            while (
                                curr_player_stat["match_id"] == coregame.match_id
                                and len(stats_data[player["Subject"]]) > i
                            ):
                                i += 1
                                # if curr_player_stat["match_id"] == coregame.match_id and len(stats_data[player["Subject"]]) > 1:
                                curr_player_stat = stats_data[player["Subject"]][-i]
                            if curr_player_stat["match_id"] != coregame.match_id:
                                # checking for party memebers and self players
                                times = 0
                                m_set = ()
                                for m in stats_data[player["Subject"]]:
                                    if (
                                        m["match_id"] != coregame.match_id
                                        and m["match_id"] not in m_set
                                    ):
                                        times += 1
                                        m_set += (m["match_id"],)
                                played_with_count = times
                                last_played_agent = curr_player_stat.get("agent", "")
                                last_played_team = curr_player_stat.get("team", "")
                                last_played_seconds_ago = int(
                                    time.time() - curr_player_stat["epoch"]
                                )
                                if (
                                    player["Subject"] != Requests.puuid
                                    and player["Subject"] not in partyMembersList
                                ):
                                    if player["PlayerIdentity"]["Incognito"] == False:
                                        already_played_with.append(
                                            {
                                                "times": times,
                                                "name": curr_player_stat["name"],
                                                "agent": curr_player_stat["agent"],
                                                "time_diff": time.time()
                                                - curr_player_stat["epoch"],
                                            }
                                        )
                                    else:
                                        if player["TeamID"] == allyTeam:
                                            team_string = "your"
                                        else:
                                            team_string = "enemy"
                                        already_played_with.append(
                                            {
                                                "times": times,
                                                "name": agent_dict.get(
                                                    player["CharacterID"].lower(), "Unknown"
                                                )
                                                + " on "
                                                + team_string
                                                + " team",
                                                "agent": curr_player_stat["agent"],
                                                "time_diff": time.time()
                                                - curr_player_stat["epoch"],
                                            }
                                        )

                        party_icon = ""
                        # set party premade icon
                        for party in partyOBJ:
                            if player["Subject"] in partyOBJ[party]:
                                if party not in partyIcons:
                                    partyIcons.update(
                                        {party: PARTYICONLIST[partyCount]}
                                    )
                                    # PARTY_ICON
                                    party_icon = PARTYICONLIST[partyCount]
                                    partyNum = partyCount + 1
                                    partyCount += 1
                                else:
                                    # PARTY_ICON
                                    party_icon = partyIcons[party]
                        history_elapsed_ms = (time.perf_counter() - history_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "fetching rank + performance",
                            history_elapsed_ms,
                        )
                        rank_started = time.perf_counter()
                        playerRank, previousPlayerRank, ppstats = get_or_fetch_rank_and_stats(
                            player["Subject"], coregame_match_id
                        )

                        if player["Subject"] == Requests.puuid:
                            if cfg.get_feature_flag("discord_rpc"):
                                rpc.set_data(
                                    {
                                        "rank": playerRank["rank"],
                                        "rank_name": colors.escape_ansi(
                                            NUMBERTORANKS[playerRank["rank"]]
                                        )
                                        + " | "
                                        + str(playerRank["rr"])
                                        + "rr",
                                    }
                                )
                        # rankStatus = playerRank[1]
                        # useless code since rate limit is handled in the requestsV
                        # while not rankStatus:
                        #     print("You have been rate limited, 😞 waiting 10 seconds!")
                        #     time.sleep(10)
                        #     playerRank = rank.get_rank(player["Subject"], seasonID)
                        #     rankStatus = playerRank[1]

                        hs = ppstats["hs"]
                        kd = ppstats["kd"]

                        rr_numeric_value = ppstats["RankedRatingEarned"]
                        afk_penalty = ppstats["AFKPenalty"]
                        ranked_rating_earned = colors.get_rr_gradient(
                            rr_numeric_value, afk_penalty
                        )

                        player_level = player["PlayerIdentity"].get("AccountLevel")

                        if player["PlayerIdentity"]["Incognito"]:
                            Namecolor = colors.get_color_from_team(
                                player["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                agent=player["CharacterID"],
                                party_members=partyMembersList,
                            )
                        else:
                            Namecolor = colors.get_color_from_team(
                                player["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                party_members=partyMembersList,
                            )
                        if lastTeam != player["TeamID"]:
                            if lastTeamBoolean:
                                table.add_empty_row()
                        lastTeam = player["TeamID"]
                        lastTeamBoolean = True
                        if player["PlayerIdentity"]["HideAccountLevel"]:
                            if (
                                player["Subject"] == Requests.puuid
                                or player["Subject"] in partyMembersList
                                or hide_levels == False
                            ):
                                PLcolor = colors.level_to_color(player_level)
                            else:
                                PLcolor = ""
                        else:
                            PLcolor = colors.level_to_color(player_level)
                        # AGENT
                        # agent = str(agent_dict.get(player["CharacterID"].lower()))
                        agent = colors.get_agent_from_uuid(
                            player["CharacterID"].lower()
                        )
                        if agent == "" and len(Players) == 1:
                            isRange = True

                        # NAME
                        name = Namecolor

                        # VIEWS
                        # views = get_views(names[player["Subject"]])

                        # skin
                        skin = loadouts.get(player["Subject"], "")

                        # RANK
                        rankName = Ranks[playerRank["rank"]]
                        if cfg.get_feature_flag("aggregate_rank_rr") and cfg.table.get(
                            "rr"
                        ):
                            rankName += f" ({playerRank['rr']})"

                        # RANK RATING
                        rr = playerRank["rr"]
                        rr_display = colors.get_current_rr_gradient(rr)

                        # short peak rank string
                        has_letter = any(
                            c.isalpha() for c in str(playerRank["peakrankep"])
                        )
                        peakRankAct = (
                            f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            if has_letter
                            else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                        )
                        if not cfg.get_feature_flag("peak_rank_act"):
                            peakRankAct = ""

                        # PEAK RANK
                        peakRank = Ranks[playerRank["peakrank"]] + peakRankAct

                        # PREVIOUS RANK
                        previousRank = Ranks[previousPlayerRank["rank"]]

                        # LEADERBOARD
                        leaderboard = playerRank["leaderboard"]

                        hs = colors.get_hs_gradient(hs)
                        wr = (
                            colors.get_wr_gradient(playerRank["wr"])
                            + f" ({playerRank['numberofgames']})"
                        )

                        if int(leaderboard) > 0:
                            is_leaderboard_needed = True

                        # LEVEL
                        level = PLcolor
                        table.add_row_table(
                            [
                                party_icon,
                                agent,
                                name,
                                # views,
                                skin,
                                rankName,
                                rr_display,
                                peakRank,
                                previousRank,
                                leaderboard,
                                hs,
                                wr,
                                kd,
                                level,
                                ranked_rating_earned,
                            ]
                        )

                        loadout_entry = loadouts_data.get("Players", {}).get(player["Subject"], {})
                        skin_summary = []
                        for weapon_key, weapon_data in loadout_entry.get("Weapons", {}).items():
                            skin_name = weapon_data.get("skinDisplayName")
                            if skin_name:
                                skin_summary.append({
                                    "name": skin_name,
                                    "icon": weapon_data.get("skinDisplayIcon"),
                                    "weapon": weapon_data.get("weapon"),
                                    "tierUuid": weapon_data.get("contentTierUuid"),
                                    "tierColor": weapon_data.get("contentTierColor"),
                                })

                        player_name, player_tag = (names[player["Subject"]].split("#", 1) + [""])[0:2]
                        rank_display = colors.escape_ansi(
                            Ranks[playerRank["rank"]]
                        )
                        peak_rank_display = colors.escape_ansi(
                            Ranks[playerRank["peakrank"]] + peakRankAct
                        )
                        rr_change_value = ppstats.get("RankedRatingEarned", "N/A")
                        try:
                            rr_change_display = f"{int(rr_change_value):+d}"
                        except (TypeError, ValueError):
                            rr_change_display = str(rr_change_value)
                        rank_elapsed_ms = (time.perf_counter() - rank_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "computing recent competitive streak",
                            rank_elapsed_ms,
                        )
                        streak_started = time.perf_counter()
                        streak_info = get_recent_streak_for_player(player["Subject"], max_games=STREAK_SAMPLE_GAMES)
                        agent_uuid = str(player.get("CharacterID", "")).lower()
                        streak_elapsed_ms = (time.perf_counter() - streak_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "finalizing dashboard row",
                            streak_elapsed_ms,
                        )
                        finalize_started = time.perf_counter()
                        heartbeat_data["players"][player["Subject"]] = {
                            "puuid": player["Subject"],
                            "isSelf": player["Subject"] == Requests.puuid,
                            "name": names[player["Subject"]],
                            "playerName": player_name,
                            "playerTag": player_tag,
                            "partyNumber": partyNum if party_icon != "" else 0,
                            "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                            "currentRank": playerRank["rank"],
                            "rankName": rank_display,
                            "peakRank": playerRank["peakrank"],
                            "peakRankName": peak_rank_display,
                            "peakRankAct": peakRankAct,
                            "rr": rr,
                            "rrDelta": rr_change_display,
                            "rrPenalty": ppstats.get("AFKPenalty", "N/A"),
                            "kd": ppstats["kd"],
                            "kda": ppstats.get("kda", "N/A"),
                            "kills": ppstats.get("kills", "N/A"),
                            "deaths": ppstats.get("deaths", "N/A"),
                            "assists": ppstats.get("assists", "N/A"),
                            "headshotPercentage": ppstats["hs"],
                            "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                            "level": player_level,
                            "accountLevel": player_level,
                            "agentImgLink": loadout_entry.get("Agent") or agent_icon_dict.get(agent_uuid),
                            "team": player.get("TeamID", loadout_entry.get("Team", None)),
                            "sprays": loadout_entry.get("Sprays", None),
                            "title": loadout_entry.get("Title", None),
                            "playerCard": loadout_entry.get("PlayerCard", None),
                            "weapons": loadout_entry.get("Weapons", None),
                            "skinNames": [item["name"] for item in skin_summary],
                            "skinIcons": [item["icon"] for item in skin_summary],
                            "skinSummary": skin_summary,
                            "playedWithBefore": played_with_count > 0,
                            "playedWithCount": played_with_count,
                            "lastPlayedAgent": last_played_agent,
                            "lastPlayedTeam": last_played_team,
                            "lastPlayedSecondsAgo": last_played_seconds_ago,
                            "recentStreakType": streak_info.get("type", "none"),
                            "recentStreakCount": streak_info.get("count", 0),
                            "recentStreakSample": streak_info.get("sample", 0),
                            "recentStreakWins": streak_info.get("wins", 0),
                            "recentStreakLosses": streak_info.get("losses", 0),
                            "recentStreakOutcomes": streak_info.get("recent", []),
                            "playerMatches": [
                                m for m in stats.get_matches_for_player(player["Subject"])
                                if str(m.get("match_id")) != str(coregame_match_id)
                            ],
                        }
                        finalize_elapsed_ms = (time.perf_counter() - finalize_started) * 1000
                        total_elapsed_ms = history_elapsed_ms + rank_elapsed_ms + streak_elapsed_ms + finalize_elapsed_ms
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "done",
                            total_elapsed_ms,
                        )

                        stats.save_data(
                            {
                                player["Subject"]: {
                                    "name": names[player["Subject"]],
                                    "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                    "map": current_map,
                                    "rank": playerRank["rank"],
                                    "rr": rr,
                                    "team": player.get("TeamID", ""),
                                    "match_id": coregame_match_id,
                                    "epoch": time.time(),
                                }
                            }
                        )
                        # bar()

                feed_signature = (
                    game_state,
                    str(heartbeat_data.get("match_id", "")),
                    str(heartbeat_data.get("server_id", "")),
                )
                if feed_signature != lastFeedSignature:
                    Server.send_payload("feed", heartbeat_data)
                    lastFeedSignature = feed_signature
            elif game_state == "PREGAME":
                already_played_with = []
                pregame_stats = pregame.get_pregame_stats()
                if pregame_stats == None:
                    continue
                server = pregame_stats.get("GamePodID", "")
                if server:
                    server_parts = server.split('.')
                    heartbeat_data["server_id"] = '.'.join(server_parts[2:]) if len(server_parts) > 2 else server
                else:
                    heartbeat_data["server_id"] = ""
                Players = pregame_stats["AllyTeam"]["Players"]
                presences.wait_for_presence(namesClass.get_players_puuid(Players))
                names = namesClass.get_names_from_puuids(Players)
                pregame_match_id = pregame_stats.get("ID")
                heartbeat_data["match_id"] = pregame_match_id
                heartbeat_data["tracker_match_url"] = (
                    f"https://tracker.gg/valorant/match/{pregame_match_id}"
                    if pregame_match_id else ""
                )
                stats.save_match_id(pregame_match_id, Players)
                ensure_match_player_cache(pregame_match_id)
                # Pregame loadout fetch is intentionally skipped here to keep
                # agent-select flow stable across API shape differences.
                playersLoaded = 1
                clear_loading_status()
                with richConsole.status("Loading Players...") as status:
                    # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                    presence = presences.get_presence()
                    partyOBJ = menu.get_party_json(
                        namesClass.get_players_puuid(Players), presence
                    )
                    partyMembers = menu.get_party_members(Requests.puuid, presence)
                    partyMembersList = [a["Subject"] for a in partyMembers]
                    stats_data = stats.read_data()
                    # log(f"retrieved names dict: {names}")
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    partyCount = 0
                    partyIcons = {}
                    for player in Players:
                        loading_name = names.get(player["Subject"], "Unknown").split("#", 1)[0]
                        loading_agent = agent_dict.get(player.get("CharacterID", "").lower(), "Unknown")
                        current_index = playersLoaded
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "reading history and party data",
                        )
                        playersLoaded += 1
                        history_started = time.perf_counter()

                        played_with_count = 0
                        last_played_seconds_ago = None
                        last_played_agent = ""
                        last_played_team = ""
                        if player["Subject"] in stats_data:
                            player_history = stats_data[player["Subject"]]
                            if len(player_history) > 0:
                                unique_matches = {
                                    m.get("match_id")
                                    for m in player_history
                                    if m.get("match_id")
                                }
                                played_with_count = len(unique_matches)
                                latest_entry = player_history[-1]
                                last_played_agent = latest_entry.get("agent", "")
                                last_played_team = latest_entry.get("team", "")
                                latest_epoch = latest_entry.get("epoch")
                                if latest_epoch:
                                    last_played_seconds_ago = int(time.time() - latest_epoch)

                        party_icon = ""

                        # set party premade icon
                        for party in partyOBJ:
                            if player["Subject"] in partyOBJ[party]:
                                if party not in partyIcons:
                                    partyIcons.update(
                                        {party: PARTYICONLIST[partyCount]}
                                    )
                                    # PARTY_ICON
                                    party_icon = PARTYICONLIST[partyCount]
                                    partyNum = partyCount + 1
                                else:
                                    # PARTY_ICON
                                    party_icon = partyIcons[party]
                                partyCount += 1
                        history_elapsed_ms = (time.perf_counter() - history_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "fetching rank + performance",
                            history_elapsed_ms,
                        )
                        rank_started = time.perf_counter()
                        playerRank, previousPlayerRank, ppstats = get_or_fetch_rank_and_stats(
                            player["Subject"], pregame_match_id
                        )

                        if player["Subject"] == Requests.puuid:
                            if cfg.get_feature_flag("discord_rpc"):
                                rpc.set_data(
                                    {
                                        "rank": playerRank["rank"],
                                        "rank_name": colors.escape_ansi(
                                            NUMBERTORANKS[playerRank["rank"]]
                                        )
                                        + " | "
                                        + str(playerRank["rr"])
                                        + "rr",
                                    }
                                )
                        # rankStatus = playerRank[1]
                        # useless code since rate limit is handled in the requestsV
                        # while not rankStatus:
                        #     print("You have been rate limited, 😞 waiting 10 seconds!")
                        #     time.sleep(10)
                        #     playerRank = rank.get_rank(player["Subject"], seasonID)
                        #     rankStatus = playerRank[1]
                        # playerRank = playerRank[0]

                        hs = ppstats["hs"]
                        kd = ppstats["kd"]

                        rr_numeric_value = ppstats["RankedRatingEarned"]
                        afk_penalty = ppstats["AFKPenalty"]
                        ranked_rating_earned = colors.get_rr_gradient(
                            rr_numeric_value, afk_penalty
                        )

                        player_level = player["PlayerIdentity"].get("AccountLevel")
                        if player["PlayerIdentity"]["Incognito"]:
                            NameColor = colors.get_color_from_team(
                                pregame_stats["Teams"][0]["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                agent=player["CharacterID"],
                                party_members=partyMembersList,
                            )
                        else:
                            NameColor = colors.get_color_from_team(
                                pregame_stats["Teams"][0]["TeamID"],
                                names[player["Subject"]],
                                player["Subject"],
                                Requests.puuid,
                                party_members=partyMembersList,
                            )

                        if player["PlayerIdentity"]["HideAccountLevel"]:
                            if (
                                player["Subject"] == Requests.puuid
                                or player["Subject"] in partyMembersList
                                or hide_levels == False
                            ):
                                PLcolor = colors.level_to_color(player_level)
                            else:
                                PLcolor = ""
                        else:
                            PLcolor = colors.level_to_color(player_level)
                        if player["CharacterSelectionState"] == "locked":
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(255, 255, 255),
                            )
                        elif player["CharacterSelectionState"] == "selected":
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(128, 128, 128),
                            )
                        else:
                            agent_color = color(
                                agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                                fore=(54, 53, 51),
                            )

                        # AGENT
                        agent = agent_color

                        # NAME
                        name = NameColor

                        # VIEWS
                        # views = get_views(names[player["Subject"]])

                        # Pregame skin info is not shown in CLI table.

                        # RANK
                        rankName = Ranks[playerRank["rank"]]
                        if cfg.get_feature_flag("aggregate_rank_rr") and cfg.table.get(
                            "rr"
                        ):
                            rankName += f" ({playerRank['rr']})"

                        # RANK RATING
                        rr = playerRank["rr"]
                        rr_display = colors.get_current_rr_gradient(rr)

                        # short peak rank string
                        has_letter = any(
                            c.isalpha() for c in str(playerRank["peakrankep"])
                        )
                        peakRankAct = (
                            f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            if has_letter
                            else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                        )
                        if not cfg.get_feature_flag("peak_rank_act"):
                            peakRankAct = ""
                        # PEAK RANK
                        peakRank = Ranks[playerRank["peakrank"]] + peakRankAct

                        # PREVIOUS RANK
                        previousRank = Ranks[previousPlayerRank["rank"]]

                        # LEADERBOARD
                        leaderboard = playerRank["leaderboard"]

                        hs = colors.get_hs_gradient(hs)
                        wr = (
                            colors.get_wr_gradient(playerRank["wr"])
                            + f" ({playerRank['numberofgames']})"
                        )

                        if int(leaderboard) > 0:
                            is_leaderboard_needed = True

                        # LEVEL
                        level = PLcolor

                        table.add_row_table(
                            [
                                party_icon,
                                agent,
                                name,
                                # views,
                                "",
                                rankName,
                                rr_display,
                                peakRank,
                                previousRank,
                                leaderboard,
                                hs,
                                wr,
                                kd,
                                level,
                                ranked_rating_earned,
                            ]
                        )

                        player_name, player_tag = (names[player["Subject"]].split("#", 1) + [""])[0:2]
                        rank_display = colors.escape_ansi(
                            Ranks[playerRank["rank"]]
                        )
                        peak_rank_display = colors.escape_ansi(
                            Ranks[playerRank["peakrank"]] + peakRankAct
                        )
                        rr_change_value = ppstats.get("RankedRatingEarned", "N/A")
                        try:
                            rr_change_display = f"{int(rr_change_value):+d}"
                        except (TypeError, ValueError):
                            rr_change_display = str(rr_change_value)
                        rank_elapsed_ms = (time.perf_counter() - rank_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "computing recent competitive streak",
                            rank_elapsed_ms,
                        )
                        streak_started = time.perf_counter()
                        streak_info = get_recent_streak_for_player(player["Subject"], max_games=STREAK_SAMPLE_GAMES)
                        streak_elapsed_ms = (time.perf_counter() - streak_started) * 1000
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "finalizing dashboard row",
                            streak_elapsed_ms,
                        )
                        finalize_started = time.perf_counter()
                        heartbeat_data["players"][player["Subject"]] = {
                            "puuid": player["Subject"],
                            "isSelf": player["Subject"] == Requests.puuid,
                            "name": names[player["Subject"]],
                            "playerName": player_name,
                            "playerTag": player_tag,
                            "partyNumber": partyNum if party_icon != "" else 0,
                            "agent": agent_dict.get(player["CharacterID"].lower(), "Unknown"),
                            "currentRank": playerRank["rank"],
                            "rankName": rank_display,
                            "peakRank": playerRank["peakrank"],
                            "peakRankName": peak_rank_display,
                            "peakRankAct": peakRankAct,
                            "level": player_level,
                            "accountLevel": player_level,
                            "rr": rr,
                            "rrDelta": rr_change_display,
                            "rrPenalty": ppstats.get("AFKPenalty", "N/A"),
                            "kd": ppstats["kd"],
                            "kda": ppstats.get("kda", "N/A"),
                            "kills": ppstats.get("kills", "N/A"),
                            "deaths": ppstats.get("deaths", "N/A"),
                            "assists": ppstats.get("assists", "N/A"),
                            "headshotPercentage": ppstats["hs"],
                            "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                            "team": player.get("TeamID", None),
                            "skinNames": [],
                            "skinIcons": [],
                            "skinSummary": [],
                            "playedWithBefore": played_with_count > 0,
                            "playedWithCount": played_with_count,
                            "lastPlayedAgent": last_played_agent,
                            "lastPlayedTeam": last_played_team,
                            "lastPlayedSecondsAgo": last_played_seconds_ago,
                            "recentStreakType": streak_info.get("type", "none"),
                            "recentStreakCount": streak_info.get("count", 0),
                            "recentStreakSample": streak_info.get("sample", 0),
                            "recentStreakWins": streak_info.get("wins", 0),
                            "recentStreakLosses": streak_info.get("losses", 0),
                            "recentStreakOutcomes": streak_info.get("recent", []),
                            "playerMatches": [
                                m for m in stats.get_matches_for_player(player["Subject"])
                                if str(m.get("match_id")) != str(pregame_match_id)
                            ],
                        }
                        finalize_elapsed_ms = (time.perf_counter() - finalize_started) * 1000
                        total_elapsed_ms = history_elapsed_ms + rank_elapsed_ms + streak_elapsed_ms + finalize_elapsed_ms
                        update_player_loading_status(
                            status,
                            current_index,
                            len(Players),
                            loading_name,
                            loading_agent,
                            "done",
                            total_elapsed_ms,
                        )

                        # bar()

                feed_signature = (
                    game_state,
                    str(heartbeat_data.get("match_id", "")),
                    str(heartbeat_data.get("server_id", "")),
                )
                if feed_signature != lastFeedSignature:
                    Server.send_payload("feed", heartbeat_data)
                    lastFeedSignature = feed_signature
            if game_state == "MENUS":
                reset_match_player_cache()
                if hasattr(pstats, "clear_runtime_cache"):
                    pstats.clear_runtime_cache()

                server = ""
                heartbeat_data["server_id"] = server
                heartbeat_data["match_id"] = ""
                heartbeat_data["tracker_match_url"] = ""
                already_played_with = []
                Players = menu.get_party_members(Requests.puuid, presence)
                names = namesClass.get_names_from_puuids(Players)
                playersLoaded = 1
                clear_loading_status()
                with richConsole.status("Loading Players...") as status:
                    # with alive_bar(total=len(Players), title='Fetching Players', bar='classic2') as bar:
                    # log(f"retrieved names dict: {names}")
                    stats_data = stats.read_data()
                    Players.sort(
                        key=lambda Players: Players["PlayerIdentity"].get(
                            "AccountLevel"
                        ),
                        reverse=True,
                    )
                    seen = []
                    for player in Players:

                        if player not in seen:
                            loading_name = names.get(player["Subject"], "Unknown").split("#", 1)[0]
                            loading_agent = "Menu"
                            current_index = playersLoaded
                            update_player_loading_status(
                                status,
                                current_index,
                                len(Players),
                                loading_name,
                                loading_agent,
                                "reading history",
                            )
                            playersLoaded += 1
                            history_started = time.perf_counter()
                            played_with_count = 0
                            last_played_seconds_ago = None
                            last_played_agent = ""
                            last_played_team = ""
                            if player["Subject"] in stats_data:
                                player_history = stats_data[player["Subject"]]
                                if len(player_history) > 0:
                                    unique_matches = {
                                        m.get("match_id")
                                        for m in player_history
                                        if m.get("match_id")
                                    }
                                    played_with_count = len(unique_matches)
                                    latest_entry = player_history[-1]
                                    last_played_agent = latest_entry.get("agent", "")
                                    last_played_team = latest_entry.get("team", "")
                                    latest_epoch = latest_entry.get("epoch")
                                    if latest_epoch:
                                        last_played_seconds_ago = int(time.time() - latest_epoch)

                            party_icon = PARTYICONLIST[0]
                            history_elapsed_ms = (time.perf_counter() - history_started) * 1000
                            update_player_loading_status(
                                status,
                                current_index,
                                len(Players),
                                loading_name,
                                loading_agent,
                                "fetching rank + performance",
                                history_elapsed_ms,
                            )
                            rank_started = time.perf_counter()
                            playerRank = rank.get_rank(player["Subject"], seasonID)
                            previousPlayerRank = rank.get_rank(
                                player["Subject"], previousSeasonID
                            )
                            if player["Subject"] == Requests.puuid:
                                if cfg.get_feature_flag("discord_rpc"):
                                    rpc.set_data(
                                        {
                                            "rank": playerRank["rank"],
                                            "rank_name": colors.escape_ansi(
                                                NUMBERTORANKS[playerRank["rank"]]
                                            )
                                            + " | "
                                            + str(playerRank["rr"])
                                            + "rr",
                                        }
                                    )

                            # rankStatus = playerRank[1]
                            # useless code since rate limit is handled in the requestsV
                            # while not rankStatus:
                            #     print("You have been rate limited, 😞 waiting 10 seconds!")
                            #     time.sleep(10)
                            #     playerRank = rank.get_rank(player["Subject"], seasonID)
                            #     rankStatus = playerRank[1]
                            # playerRank = playerRank["rank"]

                            ppstats = pstats.get_stats(player["Subject"])
                            hs = ppstats["hs"]
                            kd = ppstats["kd"]

                            rr_numeric_value = ppstats["RankedRatingEarned"]
                            afk_penalty = ppstats["AFKPenalty"]
                            ranked_rating_earned = colors.get_rr_gradient(
                                rr_numeric_value, afk_penalty
                            )

                            player_level = player["PlayerIdentity"].get("AccountLevel")
                            PLcolor = colors.level_to_color(player_level)

                            # AGENT
                            agent = ""

                            # NAME
                            name = color(names[player["Subject"]], fore=(76, 151, 237))

                            # RANK
                            rankName = Ranks[playerRank["rank"]]
                            if cfg.get_feature_flag(
                                "aggregate_rank_rr"
                            ) and cfg.table.get("rr"):
                                rankName += f" ({playerRank['rr']})"

                            # RANK RATING
                            rr = playerRank["rr"]
                            rr_display = colors.get_current_rr_gradient(rr)

                            # short peak rank string
                            has_letter = any(
                                c.isalpha() for c in str(playerRank["peakrankep"])
                            )
                            peakRankAct = (
                                f" ({playerRank['peakrankep']}a{playerRank['peakrankact']})"
                                if has_letter
                                else f" (e{playerRank['peakrankep']}a{playerRank['peakrankact']})"
                            )
                            if not cfg.get_feature_flag("peak_rank_act"):
                                peakRankAct = ""

                            # PEAK RANK
                            peakRank = (
                                Ranks[playerRank["peakrank"]] + peakRankAct
                            )

                            # PREVIOUS RANK
                            previousRank = Ranks[previousPlayerRank["rank"]]

                            # LEADERBOARD
                            leaderboard = playerRank["leaderboard"]

                            hs = colors.get_hs_gradient(hs)
                            wr = (
                                colors.get_wr_gradient(playerRank["wr"])
                                + f" ({playerRank['numberofgames']})"
                            )

                            if int(leaderboard) > 0:
                                is_leaderboard_needed = True

                            # LEVEL
                            level = PLcolor

                            table.add_row_table(
                                [
                                    party_icon,
                                    agent,
                                    name,
                                    "",
                                    rankName,
                                    rr_display,
                                    peakRank,
                                    previousRank,
                                    leaderboard,
                                    hs,
                                    wr,
                                    kd,
                                    level,
                                    ranked_rating_earned,
                                ]
                            )

                            rank_display = colors.escape_ansi(
                                Ranks[playerRank["rank"]]
                            )
                            peak_rank_display = colors.escape_ansi(
                                Ranks[playerRank["peakrank"]] + peakRankAct
                            )
                            rr_change_value = ppstats.get("RankedRatingEarned", "N/A")
                            try:
                                rr_change_display = f"{int(rr_change_value):+d}"
                            except (TypeError, ValueError):
                                rr_change_display = str(rr_change_value)
                            rank_elapsed_ms = (time.perf_counter() - rank_started) * 1000
                            update_player_loading_status(
                                status,
                                current_index,
                                len(Players),
                                loading_name,
                                loading_agent,
                                "computing recent competitive streak",
                                rank_elapsed_ms,
                            )
                            streak_started = time.perf_counter()
                            streak_info = get_recent_streak_for_player(player["Subject"], max_games=STREAK_SAMPLE_GAMES)
                            streak_elapsed_ms = (time.perf_counter() - streak_started) * 1000
                            update_player_loading_status(
                                status,
                                current_index,
                                len(Players),
                                loading_name,
                                loading_agent,
                                "finalizing dashboard row",
                                streak_elapsed_ms,
                            )
                            finalize_started = time.perf_counter()
                            heartbeat_data["players"][player["Subject"]] = {
                                "puuid": player["Subject"],
                                "isSelf": player["Subject"] == Requests.puuid,
                                "name": names[player["Subject"]],
                                "playerName": names[player["Subject"]],
                                "playerTag": "",
                                "rank": playerRank["rank"],
                                "rankName": rank_display,
                                "peakRank": playerRank["peakrank"],
                                "peakRankName": peak_rank_display,
                                "peakRankAct": peakRankAct,
                                "level": player_level,
                                "accountLevel": player_level,
                                "rr": rr,
                                "rrDelta": rr_change_display,
                                "rrPenalty": ppstats.get("AFKPenalty", "N/A"),
                                "kd": ppstats["kd"],
                                "kda": ppstats.get("kda", "N/A"),
                                "kills": ppstats.get("kills", "N/A"),
                                "deaths": ppstats.get("deaths", "N/A"),
                                "assists": ppstats.get("assists", "N/A"),
                                "headshotPercentage": ppstats["hs"],
                                "winPercentage": f"{playerRank['wr']} ({playerRank['numberofgames']})",
                                "team": player.get("TeamID", None),
                                "skinNames": [],
                                "skinIcons": [],
                                "skinSummary": [],
                                "playedWithBefore": played_with_count > 0,
                                "playedWithCount": played_with_count,
                                "lastPlayedAgent": last_played_agent,
                                "lastPlayedTeam": last_played_team,
                                "lastPlayedSecondsAgo": last_played_seconds_ago,
                                "recentStreakType": streak_info.get("type", "none"),
                                "recentStreakCount": streak_info.get("count", 0),
                                "recentStreakSample": streak_info.get("sample", 0),
                                "recentStreakWins": streak_info.get("wins", 0),
                                "recentStreakLosses": streak_info.get("losses", 0),
                                "recentStreakOutcomes": streak_info.get("recent", []),
                            }
                            finalize_elapsed_ms = (time.perf_counter() - finalize_started) * 1000
                            total_elapsed_ms = history_elapsed_ms + rank_elapsed_ms + streak_elapsed_ms + finalize_elapsed_ms
                            update_player_loading_status(
                                status,
                                current_index,
                                len(Players),
                                loading_name,
                                loading_agent,
                                "done",
                                total_elapsed_ms,
                            )

                            # bar()
                    seen.append(player["Subject"])

                # Web UI listens to feed payloads; send MENUS data so lobby players render.
                feed_signature = (
                    game_state,
                    str(heartbeat_data.get("match_id", "")),
                    str(heartbeat_data.get("server_id", "")),
                )
                if feed_signature != lastFeedSignature:
                    Server.send_payload("feed", heartbeat_data)
                    lastFeedSignature = feed_signature
            if (title := game_state_dict.get(game_state)) is None:
                # program_exit(1)
                time.sleep(9)
            
            title_parts = [f"VALORANT status: {title}"]

            if cfg.get_feature_flag("server_id") and server != "":
                parts = server.split('.')
                if len(parts) > 2:
                    short_serverID = '.'.join(parts[2:])
                else:
                    short_serverID = server
                title_parts.append(f" {colr('- ' + short_serverID, fore=(200, 200, 200))}")
            
            table.set_title(''.join(title_parts))
            
            if title is not None:
                if cfg.get_feature_flag("auto_hide_leaderboard") and (
                    not is_leaderboard_needed
                ):
                    table.set_runtime_col_flag("Pos.", False)

                if game_state == "MENUS":
                    table.set_runtime_col_flag("Party", False)
                    table.set_runtime_col_flag("Agent", False)
                    table.set_runtime_col_flag(cfg.weapon.capitalize(), False)

                if game_state == "INGAME":
                    if isRange:
                        table.set_runtime_col_flag("Party", False)
                        table.set_runtime_col_flag("Agent", False)

                # We don't to show the RR column if the "aggregate_rank_rr" feature flag is True.
                table.set_runtime_col_flag(
                    "RR",
                    cfg.table.get("rr")
                    and not cfg.get_feature_flag("aggregate_rank_rr"),
                )

                table.set_caption(STARTUP_BANNER)
                Server.send_payload("heartbeat", heartbeat_data)
                table.display()
                firstPrint = False

                # print(f"VALORANT rank yoinker v{version}")
                if cfg.get_feature_flag("last_played"):
                    if len(already_played_with) > 0:
                        print("\n")
                        for played in already_played_with:
                            print(
                                f"Already played with {played['name']} (last {played['agent']}) {stats.convert_time(played['time_diff'])} ago. (Total played {played['times']} times)"
                            )
                already_played_with = []
        if cfg.cooldown == 0:
            input("Press enter to fetch again...")
        else:
            time.sleep(10)
except KeyboardInterrupt:
    # lame implementation of fast ctrl+c exit
    os._exit(0)
except:
    log(traceback.format_exc())
    print(
        color(
            "The program has encountered an error. If the problem persists, please reach support"
            f" with the logs found in {os.getcwd()}\\logs",
            fore=(255, 0, 0),
        )
    )
    input("press enter to exit...\n")
    os._exit(1)