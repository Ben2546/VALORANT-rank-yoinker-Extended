import time


class Coregame:
    def __init__(self, Requests, log):
        self.log = log

        self.Requests = Requests

        self.response = ""
        self._cache_ttl_seconds = 2
        self._match_id_cache = {"value": 0, "ts": 0.0}
        self._stats_cache = {"match_id": None, "data": None, "ts": 0.0}

    def get_coregame_match_id(self, force_refresh=False):
        now = time.time()
        if not force_refresh and (now - self._match_id_cache["ts"]) <= self._cache_ttl_seconds:
            return self._match_id_cache["value"]

        try:
            self.response = self.Requests.fetch(url_type="glz",
                                                endpoint=f"/core-game/v1/players/{self.Requests.puuid}",
                                                method="get")
            if self.response.get("errorCode") == "RESOURCE_NOT_FOUND":
                self._match_id_cache = {"value": 0, "ts": time.time()}
                return 0
            match_id = self.response['MatchID']
            self._match_id_cache = {"value": match_id, "ts": time.time()}
            self.log(f"retrieved coregame match id: '{match_id}'")
            return match_id
        except (KeyError, TypeError):
            self.log(f"cannot find coregame match id: ")
            # print(f"No match id found. {self.response}")
            time.sleep(5)
            try:
                self.response = self.Requests.fetch(url_type="glz",
                                                    endpoint=f"/core-game/v1/players/{self.Requests.puuid}",
                                                    method="get")
                match_id = self.response['MatchID']
                self._match_id_cache = {"value": match_id, "ts": time.time()}
                self.log(f"retrieved coregame match id: '{match_id}'")
                return match_id
            except (KeyError, TypeError):
                self.log(f"cannot find coregame match id: ")
                print(f"No match id found. {self.response}")
            self._match_id_cache = {"value": 0, "ts": time.time()}
            return 0

    def get_coregame_stats(self, force_refresh=False):
        now = time.time()
        cached_match_id = self._stats_cache.get("match_id")
        cached_data = self._stats_cache.get("data")
        if (
            not force_refresh
            and cached_data is not None
            and (now - self._stats_cache.get("ts", 0.0)) <= self._cache_ttl_seconds
        ):
            self.match_id = cached_match_id
            return cached_data

        self.match_id = self.get_coregame_match_id(force_refresh=force_refresh)
        if self.match_id != 0:
            data = self.Requests.fetch(url_type="glz",
                                       endpoint=f"/core-game/v1/matches/{self.match_id}",
                                       method="get")
            self._stats_cache = {
                "match_id": self.match_id,
                "data": data,
                "ts": time.time(),
            }
            return data
        else:
            self._stats_cache = {
                "match_id": 0,
                "data": None,
                "ts": time.time(),
            }
            return None

    def get_current_map(self, map_urls, map_splashes) -> dict:
        """
        Abstracts get_coregame_stats() to get the current map name and splash.
        :return: Dictionary of appropriate name and splash.
        """
        coregame_stats = self.get_coregame_stats()

        if coregame_stats is None:
            return 'N/A'

        map_id = str(coregame_stats.get('MapID', '')).lower()
        current_map = map_urls.get(map_id)
        if not current_map:
            return {'name': 'N/A', 'splash': None}
        return {'name': current_map, 'splash': map_splashes.get(current_map)}
