import base64
import json
import time


def get_presence_value(payload, key, nested_section=None, default=None):
    if not isinstance(payload, dict):
        return default

    if nested_section:
        section = payload.get(nested_section)
        if isinstance(section, dict) and key in section:
            return section.get(key)

    if key in payload:
        return payload.get(key)

    return default


def get_session_loop_state(payload, default=None):
    return get_presence_value(payload, "sessionLoopState", "matchPresenceData", default)


def get_party_state(payload, default=None):
    return get_presence_value(payload, "partyState", "partyPresenceData", default)


def get_party_id(payload, default=""):
    return get_presence_value(payload, "partyId", "partyPresenceData", default)


def get_party_size(payload, default=0):
    return get_presence_value(payload, "partySize", "partyPresenceData", default)


def get_max_party_size(payload, default=0):
    return get_presence_value(payload, "maxPartySize", "partyPresenceData", default)


def get_party_accessibility(payload, default=""):
    return get_presence_value(payload, "partyAccessibility", "partyPresenceData", default)


def get_match_map(payload, default=""):
    return get_presence_value(payload, "matchMap", "matchPresenceData", default)


def get_account_level(payload, default=0):
    return get_presence_value(payload, "accountLevel", "playerPresenceData", default)

class Presences:
    def __init__(self, Requests, log):
        self.Requests = Requests
        self.log = log

    def get_presence(self):
        presences = self.Requests.fetch(url_type="local", endpoint="/chat/v4/presences", method="get")
        if presences is None:
            return None
        return presences['presences']

    def get_game_state(self, presences):
        private_presence = self.get_private_presence(presences)
        if private_presence:
            state = get_session_loop_state(private_presence)
            if state is None:
                self.log("ERROR: Unknown presence API structure in 'get_game_state'.")
            return state
        return None

    def get_private_presence(self, presences):
        for presence in presences:
            if presence['puuid'] == self.Requests.puuid:
                #preventing vry from crashing when lol is open
                # print(presence)
                # print(presence.get("championId"))
                if presence.get("championId") is not None or presence.get("product") == "league_of_legends":
                    return None
                else:
                    if presence['private'] == "": 
                        return None
                    decoded_private = json.loads(base64.b64decode(presence['private']))
                    # Debug
                    # self.log(f"DEBUG: Decoded Private Presence -> {decoded_private}")
                    return decoded_private
        return None

    def decode_presence(self, private):
        if "{" not in str(private) and private is not None and str(private) != "":
            decoded_party_presence = json.loads(base64.b64decode(str(private)).decode("utf-8"))
            if isinstance(decoded_party_presence, dict) and decoded_party_presence.get('isValid'):
                return decoded_party_presence
        return {
            "isValid": False,
            "partyId": 0,
            "partySize": 0,
            "partyVersion": 0,
        }

    def wait_for_presence(self, PlayersPuuids):
        while True:
            presence = self.get_presence()
            for puuid in PlayersPuuids:
                if puuid not in str(presence):
                    time.sleep(1)
                    continue
            break