import os
import time
import json

class Stats:
    def __init__(self):
        pass

    def _data_dir(self):
        return os.path.join(os.getenv('APPDATA') or ".", "vry")

    def _ensure_data_dir(self):
        try:
            os.mkdir(self._data_dir())
        except FileExistsError:
            pass

    def save_data(self, data):
        # path = os.path.join(os.getenv('APPDATA'), R'vry\stats.json')
        self._ensure_data_dir()
        try:
            with open(os.path.join(self._data_dir(), "stats.json"), "r") as f:
                original_data = json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            original_data = {}

        updated_data = original_data.copy()
        for puuid in data.keys():
            if original_data.get(puuid) is None:
                updated_data.update({puuid: [data[puuid]]})
            else:
                updated_data[puuid].append(data[puuid])
        
        # updated_data.update(data)
        # print(updated_data)

        with open(os.path.join(self._data_dir(), "stats.json"), "w") as f:
            json.dump(updated_data, f)

    def save_match_id(self, match_id, players=None):
        if not match_id:
            return

        self._ensure_data_dir()
        path = os.path.join(self._data_dir(), "matches.json")

        try:
            with open(path, "r") as f:
                matches = json.load(f)
                if not isinstance(matches, list):
                    matches = []
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            matches = []

        # Extract player PUUIDs if provided
        player_puuids = []
        if players:
            if isinstance(players, dict):
                player_puuids = list(players.keys())
            elif isinstance(players, list):
                player_puuids = [p if isinstance(p, str) else str(p.get("Subject") or p.get("puuid", "")) for p in players]

        # If match already exists, enrich missing player list and return
        for entry in matches:
            if isinstance(entry, dict) and str(entry.get("match_id")) == str(match_id):
                existing_players = entry.get("players", [])
                if not isinstance(existing_players, list):
                    existing_players = []
                merged = list(dict.fromkeys([p for p in existing_players + player_puuids if p]))
                entry["players"] = merged
                if not entry.get("tracker_url"):
                    entry["tracker_url"] = f"https://tracker.gg/valorant/match/{match_id}"
                with open(path, "w") as f:
                    json.dump(matches, f)
                return

        matches.append({
            "match_id": str(match_id),
            "tracker_url": f"https://tracker.gg/valorant/match/{match_id}",
            "epoch": int(time.time()),
            "players": player_puuids,
        })

        with open(path, "w") as f:
            json.dump(matches, f)
    
    def get_matches_for_player(self, puuid):
        if not puuid:
            return []

        all_matches = self.read_matches()
        player_matches = [m for m in all_matches if puuid in m.get("players", [])]

        # Always merge in stats history so older records without players[] are still visible.
        by_match_id = {}
        for item in player_matches:
            if isinstance(item, dict) and item.get("match_id"):
                by_match_id[str(item.get("match_id"))] = dict(item)

        history = self.read_data().get(puuid, [])
        for item in history:
            if not isinstance(item, dict):
                continue
            match_id = item.get("match_id")
            if not match_id:
                continue
            match_id = str(match_id)
            existing = by_match_id.get(match_id)
            if existing is None:
                by_match_id[match_id] = {
                    "match_id": match_id,
                    "tracker_url": f"https://tracker.gg/valorant/match/{match_id}",
                    "epoch": int(item.get("epoch", 0) or 0),
                    "players": [puuid],
                }
            else:
                # Keep the latest known timestamp for ordering.
                existing_epoch = int(existing.get("epoch", 0) or 0)
                item_epoch = int(item.get("epoch", 0) or 0)
                if item_epoch > existing_epoch:
                    existing["epoch"] = item_epoch

        return sorted(by_match_id.values(), key=lambda x: x.get("epoch", 0), reverse=True)
    def read_data(self):
        try:
            with open(os.path.join(self._data_dir(), "stats.json"), "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return {}

    def read_matches(self):
        try:
            with open(os.path.join(self._data_dir(), "matches.json"), "r") as f:
                matches = json.load(f)
                if isinstance(matches, list):
                    return sorted(matches, key=lambda x: x.get("epoch", 0), reverse=True)
                return []
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return []

    def convert_time(self, s):
        s = int(s)
        if s < 60:
            if s == 1:
                return f"{s} second"
            else:
                return f"{s} seconds"
        elif s < 3600:
            if s // 60 == 1:
                return f"{s // 60} minute"
            else:
                return f"{s // 60} minutes"
        elif s < 86400:
            if s // 3600 == 1:
                return f"{s // 3600} hours"
            else:
                return f"{s // 3600} hours"
        else:
            if s // 86400 == 1:
                return f"{s // 86400} days"
            else:
                return f"{s // 86400} days"