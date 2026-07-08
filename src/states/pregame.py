
import time




class Pregame:
    def __init__(self, Requests, log):
        self.log = log

        self.Requests = Requests

        self.response = ""
        self._cache_ttl_seconds = 2
        self._match_id_cache = {"value": 0, "ts": 0.0}
        self._stats_cache = {"match_id": None, "data": None, "ts": 0.0}



    def get_pregame_match_id(self, force_refresh=False):
        now = time.time()
        if not force_refresh and (now - self._match_id_cache["ts"]) <= self._cache_ttl_seconds:
            return self._match_id_cache["value"]

        response = {}
        try:
            response = self.Requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.Requests.puuid}", method="get")
            if not isinstance(response, dict):
                self.log("pregame match id response had unexpected type")
                self._match_id_cache = {"value": 0, "ts": time.time()}
                return 0
            if response.get("errorCode") == "RESOURCE_NOT_FOUND":
                self._match_id_cache = {"value": 0, "ts": time.time()}
                return 0
            match_id = response['MatchID']
            self._match_id_cache = {"value": match_id, "ts": time.time()}
            self.log(f"retrieved pregame match id: '{match_id}'")
            return match_id
        except (KeyError, TypeError):
            self.log(f"cannot find pregame match id: {response}")
            # print(f"No match id found. {response}")
            try:
                self.response = self.Requests.fetch(url_type="glz", endpoint=f"/pregame/v1/players/{self.Requests.puuid}", method="get")
                match_id = self.response['MatchID']
                self._match_id_cache = {"value": match_id, "ts": time.time()}
                self.log(f"retrieved pregame match id: '{match_id}'")
                return match_id
            except (KeyError, TypeError):
                self.log(f"cannot find pregame match id: ")
                print(f"No match id found. {self.response}")
            self._match_id_cache = {"value": 0, "ts": time.time()}
            return 0

    def get_pregame_stats(self, force_refresh=False):
        now = time.time()
        cached_data = self._stats_cache.get("data")
        if (
            not force_refresh
            and cached_data is not None
            and (now - self._stats_cache.get("ts", 0.0)) <= self._cache_ttl_seconds
        ):
            return cached_data

        match_id = self.get_pregame_match_id(force_refresh=force_refresh)
        if match_id != 0:
            data = self.Requests.fetch("glz", f"/pregame/v1/matches/{match_id}", "get")
            self._stats_cache = {
                "match_id": match_id,
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