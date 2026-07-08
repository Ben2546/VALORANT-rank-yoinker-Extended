from src.presences import get_party_size, get_party_id, get_account_level


class Menu:
    def __init__(self, Requests, log, presences):
        self.Requests = Requests
        self.log = log
        self.presences = presences

    def get_party_json(self, GamePlayersPuuid, presencesDICT):
        party_json = {}
        for presence in presencesDICT:
            if presence["puuid"] in GamePlayersPuuid:
                decodedPresence = self.presences.decode_presence(presence["private"])
                if decodedPresence["isValid"]:
                    party_size = get_party_size(decodedPresence, 0)
                    party_id = get_party_id(decodedPresence, "")
                    if not party_id:
                        self.log("ERROR: Unknown presence API structure in 'get_party_json'.")

                    if party_size > 1:
                        try:
                            party_json[party_id].append(presence["puuid"])
                        except KeyError:
                            party_json.update({party_id: [presence["puuid"]]})

        #remove non-in-game parties from with one player in game
        parties_to_delete = []
        for party in party_json:
            if len(party_json[party]) == 1:
                parties_to_delete.append(party)
        for party in parties_to_delete:
            del party_json[party]

        self.log(f"retrieved party json: {party_json}")
        return party_json

    def get_party_members(self, self_puuid, presencesDICT):
        res = []
        party_id = ""
        
        for presence in presencesDICT:
            if presence["puuid"] == self_puuid:
                decodedPresence = self.presences.decode_presence(presence["private"])
                if decodedPresence["isValid"]:
                    party_id = get_party_id(decodedPresence, "")
                    account_level = get_account_level(decodedPresence, 0)
                    if not party_id:
                        self.log("ERROR: Unknown presence API structure in 'get_party_members' (self).")
                        
                    res.append({"Subject": presence["puuid"], "PlayerIdentity": {"AccountLevel": account_level}})
        
        # Find other party members
        for presence in presencesDICT:
            if presence["puuid"] == self_puuid:
                continue # Skip self
                
            decodedPresence = self.presences.decode_presence(presence["private"])
            if decodedPresence["isValid"]:
                current_party_id = get_party_id(decodedPresence, "")
                account_level = get_account_level(decodedPresence, 0)
                if not current_party_id:
                    self.log("ERROR: Unknown presence API structure in 'get_party_members'.")

                if current_party_id == party_id:
                    res.append({"Subject": presence["puuid"], "PlayerIdentity": {"AccountLevel": account_level}})
                    
        self.log(f"retrieved party members: {res}")
        return res