import time
import requests
from colr import color
from src.constants import sockets, hide_names, tierDict
import json
import hashlib
import os
import queue
import threading
from pathlib import Path
from urllib.parse import urlparse


class Loadouts:
    def __init__(self, Requests, log, colors, Server, current_map):

        self.Requests = Requests
        self.log = log
        self.colors = colors
        self.Server = Server
        self.current_map = current_map
        self._api_cache = {}
        self._loadout_cache = {}
        self._image_url_cache = {}
        self._image_download_queue = queue.Queue()
        self._image_download_pending = set()
        self._image_download_lock = threading.Lock()
        self._image_manifest_dirty = False
        self._api_cache_ttl_seconds = 3600
        self._loadout_cache_ttl_seconds = 20

        self._load_image_cache_manifest()

        # Cache fills in the background so feed rendering does not block on network IO.
        self._image_download_worker = threading.Thread(
            target=self._image_cache_download_worker,
            daemon=True,
            name="vry-image-cache-worker",
        )
        self._image_download_worker.start()

    def _image_cache_dir(self):
        base_dir = Path(os.getenv("APPDATA") or ".") / "vry" / "image_cache"
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            self.log(f"failed to initialize image cache directory: {ex}")
        return base_dir

    def _image_manifest_path(self):
        return self._image_cache_dir() / "manifest.json"

    def _load_image_cache_manifest(self):
        path = self._image_manifest_path()
        try:
            if not path.exists() or not path.is_file():
                return

            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)

            if not isinstance(payload, dict):
                return

            for remote_url, local_path in payload.items():
                if not isinstance(remote_url, str) or not isinstance(local_path, str):
                    continue
                if not local_path.startswith("/cache/"):
                    continue
                rel = local_path[len("/cache/"):]
                cache_file = (self._image_cache_dir() / rel).resolve()
                cache_root = self._image_cache_dir().resolve()
                if str(cache_file).startswith(str(cache_root)) and cache_file.exists() and cache_file.is_file():
                    self._image_url_cache[remote_url] = local_path
        except Exception as ex:
            self.log(f"failed to load image cache manifest: {ex}")

    def _save_image_cache_manifest(self):
        if not self._image_manifest_dirty:
            return
        path = self._image_manifest_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._image_url_cache, fh)
            self._image_manifest_dirty = False
        except Exception as ex:
            self.log(f"failed to save image cache manifest: {ex}")

    def _content_type_to_extension(self, content_type, fallback_ext=".png"):
        if not isinstance(content_type, str):
            return fallback_ext
        ct = content_type.lower()
        if "image/png" in ct:
            return ".png"
        if "image/jpeg" in ct or "image/jpg" in ct:
            return ".jpg"
        if "image/webp" in ct:
            return ".webp"
        if "image/gif" in ct:
            return ".gif"
        if "image/svg" in ct:
            return ".svg"
        return fallback_ext

    def _url_extension(self, url):
        try:
            parsed = urlparse(str(url))
            ext = Path(parsed.path).suffix.lower()
            if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
                return ".jpg" if ext == ".jpeg" else ext
        except Exception:
            pass
        return ".png"

    def _cache_remote_image(self, image_url, namespace="skins"):
        url = str(image_url or "").strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return url

        cached_local = self._image_url_cache.get(url)
        if cached_local:
            return cached_local

        # Keep first render as fast as old behavior; downloading happens in a deferred batch.
        return url

    def _queue_images_for_cache(self, urls, namespace="skins"):
        if not isinstance(urls, (set, list, tuple)):
            return

        for image_url in urls:
            url = str(image_url or "").strip()
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                continue
            if url in self._image_url_cache:
                continue

            hashed_name = hashlib.sha1(url.encode("utf-8")).hexdigest()
            fallback_ext = self._url_extension(url)

            with self._image_download_lock:
                pending_key = (url, namespace)
                if pending_key in self._image_download_pending:
                    continue
                self._image_download_pending.add(pending_key)

            self._image_download_queue.put(
                {
                    "url": url,
                    "namespace": namespace,
                    "hashed_name": hashed_name,
                    "fallback_ext": fallback_ext,
                }
            )

    def _image_cache_download_worker(self):
        while True:
            job = self._image_download_queue.get()
            url = str(job.get("url", "")).strip()
            namespace = str(job.get("namespace", "skins")).strip() or "skins"
            hashed_name = str(job.get("hashed_name", "")).strip()
            fallback_ext = str(job.get("fallback_ext", ".png")).strip() or ".png"

            try:
                cache_dir = self._image_cache_dir() / namespace
                cache_dir.mkdir(parents=True, exist_ok=True)

                existing_file = None
                for ext in (".png", ".jpg", ".webp", ".gif", ".svg"):
                    candidate = cache_dir / f"{hashed_name}{ext}"
                    if candidate.exists() and candidate.is_file():
                        existing_file = candidate
                        break

                if existing_file is not None:
                    self._image_url_cache[url] = f"/cache/{namespace}/{existing_file.name}"
                    self._image_manifest_dirty = True
                    self._save_image_cache_manifest()
                    continue

                response = requests.get(url, timeout=8)
                if not response.ok or not response.content:
                    continue

                ext = self._content_type_to_extension(response.headers.get("Content-Type", ""), fallback_ext)
                target_file = cache_dir / f"{hashed_name}{ext}"
                with open(target_file, "wb") as fh:
                    fh.write(response.content)

                self._image_url_cache[url] = f"/cache/{namespace}/{target_file.name}"
                self._image_manifest_dirty = True
                self._save_image_cache_manifest()
            except Exception as ex:
                self.log(f"failed to cache remote image '{url}': {ex}")
            finally:
                with self._image_download_lock:
                    self._image_download_pending.discard((url, namespace))
                self._image_download_queue.task_done()

    def _get_cached_api_data(self, cache_key, url, ttl_seconds=None):
        ttl = self._api_cache_ttl_seconds if ttl_seconds is None else ttl_seconds
        now = time.time()
        cached = self._api_cache.get(cache_key)
        if cached and (now - cached.get("ts", 0)) <= ttl:
            return cached.get("data", [])

        try:
            response = requests.get(url, timeout=8)
            payload = response.json() if hasattr(response, "json") else {}
            data = payload.get("data", []) if isinstance(payload, dict) else []
        except Exception as ex:
            self.log(f"failed to fetch {cache_key} metadata: {ex}")
            data = cached.get("data", []) if cached else []

        self._api_cache[cache_key] = {"ts": now, "data": data}
        return data

    def _get_cached_match_loadouts(self, cache_key, endpoint):
        now = time.time()
        cached = self._loadout_cache.get(cache_key)
        if cached and (now - cached.get("ts", 0)) <= self._loadout_cache_ttl_seconds:
            return cached.get("data", {})

        payload = self.Requests.fetch("glz", endpoint, "get")
        if not isinstance(payload, dict):
            self.log(f"loadouts response invalid type for endpoint {endpoint}")
            payload = cached.get("data", {}) if cached else {}

        if "Loadouts" not in payload or not isinstance(payload.get("Loadouts"), list):
            # Canonicalize shape so callers can safely iterate.
            payload = {"Loadouts": []}

        self._loadout_cache[cache_key] = {"ts": now, "data": payload}
        return payload

    def get_match_loadouts(self, match_id, players, weaponChoose, valoApiSkins, names, state="game"):
        playersBackup = players
        weaponLists = {}
        valApiWeapons = self._get_cached_api_data("weapons", "https://valorant-api.com/v1/weapons")
        weapon_choice = str(weaponChoose or "").lower().strip()
        selected_weapon = None
        for weapon in valApiWeapons:
            if str(weapon.get("displayName", "")).lower() == weapon_choice:
                selected_weapon = weapon
                break

        try:
            skins_payload = valoApiSkins.json() if hasattr(valoApiSkins, "json") else {}
        except Exception:
            skins_payload = {}

        skins_data = skins_payload.get("data", []) if isinstance(skins_payload, dict) else []
        skin_by_uuid = {
            str(skin.get("uuid", "")).lower(): skin
            for skin in skins_data
            if isinstance(skin, dict) and skin.get("uuid")
        }

        if state == "game":
            team_id = "Blue"
            loadout_endpoint = f"/core-game/v1/matches/{match_id}/loadouts"
            PlayerInventorys = self._get_cached_match_loadouts(("game", str(match_id)), loadout_endpoint)
        elif state == "pregame":
            pregame_stats = players
            players = players["AllyTeam"]["Players"]
            team_id = pregame_stats['Teams'][0]['TeamID']
            loadout_endpoint = f"/pregame/v1/matches/{match_id}/loadouts"
            PlayerInventorys = self._get_cached_match_loadouts(("pregame", str(match_id)), loadout_endpoint)

        # subject (player UUID) -> loadout lookup
        loadout_by_subject = {}
        loadouts_list = PlayerInventorys.get("Loadouts", []) if isinstance(PlayerInventorys, dict) else []
        for loadout_entry in loadouts_list:
            subj = loadout_entry.get("Subject", "").lower()
            # if player has an agent != spectator
            char_id = loadout_entry.get("CharacterID", "")
            if subj and char_id:
                loadout_by_subject[subj] = loadout_entry["Loadout"] if state == "game" else loadout_entry

        for player in players:
            subj = player.get("Subject", "").lower()
            inv = loadout_by_subject.get(subj)
            if inv is None:
                continue
            if not selected_weapon:
                continue
            try:
                skin_id = inv["Items"][selected_weapon["uuid"].lower()]["Sockets"]["bcef87d6-209b-46c6-8b19-fbe40bd95abc"]["Item"]["ID"]
            except Exception:
                continue

            skin = skin_by_uuid.get(str(skin_id).lower())
            if not skin:
                continue

            rgb_color = self.colors.get_rgb_color_from_skin(
                str(skin.get("uuid", "")).lower(), valoApiSkins)
            skin_display_name = str(skin.get("displayName", "")).replace(
                f" {selected_weapon.get('displayName', '')}", "")
            weaponLists.update({player["Subject"]: color(
                skin_display_name, fore=rgb_color)})
        final_json = self.convertLoadoutToJsonArray(
            PlayerInventorys, playersBackup, state, names)
        # self.log(f"json for website: {final_json}")
        self.Server.send_payload("matchLoadout", final_json)
        return [weaponLists, final_json]

    # this will convert valorant loadouts to json with player names
    def convertLoadoutToJsonArray(self, PlayerInventorys, players, state, names):
        # get agent dict from main in future
        # names = self.namesClass.get_names_from_puuids(players)
        sprays_data = self._get_cached_api_data("sprays", "https://valorant-api.com/v1/sprays")
        weapons_data = self._get_cached_api_data("weapons", "https://valorant-api.com/v1/weapons")
        weapon_skin_assets = self._get_cached_api_data("weapon_skins", "https://valorant-api.com/v1/weapons/skins")
        buddies_data = self._get_cached_api_data("buddies", "https://valorant-api.com/v1/buddies")
        agents_data = self._get_cached_api_data("agents", "https://valorant-api.com/v1/agents")
        titles_data = self._get_cached_api_data("titles", "https://valorant-api.com/v1/playertitles")
        player_cards_data = self._get_cached_api_data("player_cards", "https://valorant-api.com/v1/playercards")

        agent_by_uuid = {str(a.get("uuid", "")).lower(): a for a in agents_data if isinstance(a, dict)}
        title_by_uuid = {str(t.get("uuid", "")).lower(): t for t in titles_data if isinstance(t, dict)}
        card_by_uuid = {str(c.get("uuid", "")).lower(): c for c in player_cards_data if isinstance(c, dict)}
        spray_by_uuid = {str(s.get("uuid", "")).lower(): s for s in sprays_data if isinstance(s, dict)}
        buddy_by_uuid = {str(b.get("uuid", "")).lower(): b for b in buddies_data if isinstance(b, dict)}

        skin_asset_by_uuid = {
            str(asset.get("uuid", "")).lower(): asset
            for asset in weapon_skin_assets
            if isinstance(asset, dict) and asset.get("uuid")
        }
        weapon_by_uuid = {
            str(weapon.get("uuid", "")).lower(): weapon
            for weapon in weapons_data
            if isinstance(weapon, dict) and weapon.get("uuid")
        }
        final_final_json = {
            "Players": {},
            "time": int(time.time()),
            "map": self.current_map,
        }

        final_json = final_final_json["Players"]
        pending_skin_urls = set()
        if state == "game":
            if not isinstance(PlayerInventorys, dict):
                PlayerInventorys = {"Loadouts": []}
            PlayerInventorys = PlayerInventorys.get("Loadouts", [])

            # subject (player UUID) -> loadout lookup
            loadout_by_subject = {}
            for entry in PlayerInventorys:
                subj = entry.get("Subject", "").lower()
                # if player has an agent != spectator
                char_id = entry.get("CharacterID", "")
                if subj and char_id:
                    loadout_by_subject[subj] = entry["Loadout"]

            for player in players:
                subject = player["Subject"]
                subj = subject.lower()
                loadout_entry = loadout_by_subject.get(subj)

                final_json.update(
                    {
                        subject: {}
                    }
                )

                # skip if not found
                if loadout_entry is None:
                    continue

                PlayerInventory = loadout_entry

                # creates name field
                if hide_names:
                    agent_meta = agent_by_uuid.get(str(player.get("CharacterID", "")).lower())
                    if agent_meta:
                        final_json[subject].update({"Name": agent_meta.get("displayName", "Unknown")})
                else:
                    final_json[subject].update({"Name": names.get(subject, "Unknown")})

                # creates team field
                final_json[subject].update({"Team": player["TeamID"]})

                # create spray field
                final_json[subject].update({"Sprays": {}})
                # append sprays to field

                final_json[subject].update(
                    {"Level": player["PlayerIdentity"]["AccountLevel"]})

                title_meta = title_by_uuid.get(str(player["PlayerIdentity"].get("PlayerTitleID", "")).lower())
                if title_meta:
                    final_json[subject].update({"Title": title_meta.get("titleText")})

                card_meta = card_by_uuid.get(str(player["PlayerIdentity"].get("PlayerCardID", "")).lower())
                if card_meta:
                    final_json[subject].update({"PlayerCard": card_meta.get("largeArt")})

                agent_meta = agent_by_uuid.get(str(player.get("CharacterID", "")).lower())
                if agent_meta:
                    final_json[subject].update(
                        {"AgentArtworkName": agent_meta.get("displayName", "Unknown") + "Artwork"}
                    )
                    final_json[subject].update(
                        {"Agent": agent_meta.get("displayIcon")}
                    )

                spray_selections = [
                    s for s in PlayerInventory.get("Expressions", {}).get("AESSelections", [])
                    if s.get("TypeID") == "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475"
                ]
                for j, spray in enumerate(spray_selections):
                    final_json[subject]["Sprays"].update({j: {}})
                    spray_meta = spray_by_uuid.get(str(spray.get("AssetID", "")).lower())
                    if spray_meta:
                        final_json[subject]["Sprays"][j].update({
                            "displayName": spray_meta.get("displayName"),
                            "displayIcon": spray_meta.get("displayIcon"),
                            "fullTransparentIcon": spray_meta.get("fullTransparentIcon")
                        })

                # create weapons field
                final_json[subject].update({"Weapons": {}})

                for skin in PlayerInventory.get("Items", {}):
                    # create skin field
                    final_json[subject]["Weapons"].update({skin: {}})
                    item_data = PlayerInventory.get("Items", {}).get(skin, {})
                    sockets_data = item_data.get("Sockets", {}) if isinstance(item_data, dict) else {}

                    for socket in sockets_data:
                        # predefined sockets
                        for var_socket in sockets:
                            if socket == sockets[var_socket]:
                                socket_item_id = sockets_data.get(socket, {}).get("Item", {}).get("ID")
                                if not socket_item_id:
                                    continue
                                final_json[subject]["Weapons"][skin].update(
                                    {
                                        var_socket: socket_item_id
                                    }
                                )

                    # create buddy field
                    # self.log("predefined sockets")
                    # final_json[subject]["Weapons"].update({skin: {}})

                    # buddies
                    for socket in sockets_data:
                        if sockets["skin_buddy"] == socket:
                            buddy_id = sockets_data.get(socket, {}).get("Item", {}).get("ID")
                            if not buddy_id:
                                continue
                            buddy_meta = buddy_by_uuid.get(
                                str(buddy_id).lower()
                            )
                            if buddy_meta:
                                final_json[subject]["Weapons"][skin].update(
                                    {
                                        "buddy_displayIcon": buddy_meta.get("displayIcon")
                                    }
                                )

                    # append names to field
                    weapon = weapon_by_uuid.get(str(skin).lower())
                    if not weapon:
                        continue

                    final_json[subject]["Weapons"][skin].update(
                        {
                            "weapon": weapon.get("displayName")
                        }
                    )

                    selected_skin_id = sockets_data.get(sockets["skin"], {}).get("Item", {}).get("ID")
                    if not selected_skin_id:
                        continue

                    for skinValApi in weapon.get("skins", []):
                        if skinValApi.get("uuid") == selected_skin_id:
                            canonical_skin_asset = skin_asset_by_uuid.get(str(skinValApi.get("uuid", "")).lower(), {})
                            content_tier_uuid = skinValApi.get("contentTierUuid") or canonical_skin_asset.get("contentTierUuid")
                            final_json[subject]["Weapons"][skin].update(
                                {
                                    "skinDisplayName": skinValApi.get("displayName"),
                                    "contentTierUuid": content_tier_uuid,
                                    "contentTierColor": tierDict.get(content_tier_uuid),
                                }
                            )

                            selected_chroma_id = sockets_data.get(sockets["skin_chroma"], {}).get("Item", {}).get("ID")
                            for chroma in skinValApi.get("chromas", []):
                                if chroma.get("uuid") == selected_chroma_id:
                                    if chroma.get("displayIcon") is not None:
                                        remote_icon = chroma.get("displayIcon")
                                        pending_skin_urls.add(str(remote_icon or ""))
                                        final_json[subject]["Weapons"][skin].update(
                                            {
                                                "skinDisplayIcon": self._cache_remote_image(remote_icon, "skins")
                                            }
                                        )
                                    elif chroma.get("fullRender") is not None:
                                        remote_icon = chroma.get("fullRender")
                                        pending_skin_urls.add(str(remote_icon or ""))
                                        final_json[subject]["Weapons"][skin].update(
                                            {
                                                "skinDisplayIcon": self._cache_remote_image(remote_icon, "skins")
                                            }
                                        )
                                    elif skinValApi.get("displayIcon") is not None:
                                        remote_icon = skinValApi.get("displayIcon")
                                        pending_skin_urls.add(str(remote_icon or ""))
                                        final_json[subject]["Weapons"][skin].update(
                                            {
                                                "skinDisplayIcon": self._cache_remote_image(remote_icon, "skins")
                                            }
                                        )
                                    else:
                                        levels = skinValApi.get("levels", [])
                                        if levels and isinstance(levels[0], dict):
                                            remote_icon = levels[0].get("displayIcon")
                                            pending_skin_urls.add(str(remote_icon or ""))
                                            final_json[subject]["Weapons"][skin].update(
                                                {
                                                    "skinDisplayIcon": self._cache_remote_image(remote_icon, "skins")
                                                }
                                            )
                                    break

                            if str(skinValApi.get("displayName", "")).startswith("Standard") or str(skinValApi.get("displayName", "")).startswith("Melee"):
                                remote_icon = weapon.get("displayIcon")
                                pending_skin_urls.add(str(remote_icon or ""))
                                final_json[subject]["Weapons"][skin]["skinDisplayIcon"] = self._cache_remote_image(remote_icon, "skins")
                            break

        self._queue_images_for_cache(pending_skin_urls, "skins")

        return final_final_json
