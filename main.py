from api_key import API_KEY
from requests import get

# Combined dictionary for both Summoner API server and Match History region
REGION_DATA = {
    "NA": ("na1", "americas"),
    "BR": ("br1", "americas"),
    "LAN": ("la1", "americas"),
    "LAS": ("la2", "americas"),
    "EUW": ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "TR": ("tr1", "europe"),
    "RU": ("ru", "europe"),
    "KR": ("kr", "asia"),
    "JP": ("jp1", "asia"),
    "OCE": ("oc1", "sea"),
}


def get_puuid(game_name, tag_line):
    """Fetch PUUID using Riot ID (game name + tag)"""
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}

    response = get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data["puuid"], data["gameName"], data["tagLine"]
    print(f"Error {response.status_code}: {response.text}")
    return None, None, None


def get_summoner_region(puuid):
    """Fetch Summoner Info using PUUID to determine the correct region"""
    for server, match_region in REGION_DATA.values():
        url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        headers = {"X-Riot-Token": API_KEY}

        response = get(url, headers=headers)
        if response.status_code == 200:
            print(f"Found summoner in region: {server.upper()}")
            return server, match_region  # Returns both summoner server and match region

    print("Could not determine summoner's region.")
    return None, None


def get_match_history(puuid, region, start=0, count=20):
    """Fetch recent match history using PUUID"""
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    headers = {"X-Riot-Token": API_KEY}

    response = get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    print(f"Error {response.status_code}: {response.text}")
    return None


def get_match_details(match_id, region):
    """Fetch match details, check if it's an Arena game, and extract all 8 teams with their players."""
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}

    response = get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        game_mode = data.get("info", {}).get("gameMode")

        # Check if the game mode is Arena (internally called "CHERRY")
        if game_mode != "CHERRY":
            return False, None

        participants = data.get("info", {}).get("participants", [])
        teams = {}  # {team_name: [player1, player2]}

        # Mapping subteam IDs to names
        TEAM_NAMES = {
            1: "Poro",
            2: "Minion",
            3: "Scuttle",
            4: "Krug",
            5: "Raptor",
            6: "Sentinel",
            7: "Wolf",
            8: "Gromp",
        }

        for player in participants:
            summoner_name = (
                player.get("riotIdGameName", "Unknown")
                + "#"
                + player.get("riotIdTagline", "0000")
            )
            subteam_id = player.get("playerSubteamId", 0)  # Get the subteam ID

            team_name = TEAM_NAMES.get(
                subteam_id, f"Unknown Team {subteam_id}"
            )  # Map to team name

            if team_name not in teams:
                teams[team_name] = []

            teams[team_name].append(summoner_name)

        return True, teams

    print(f"Error {response.status_code}: {response.text}")
    return False, None


def main():
    # User input
    game_name = input("Enter your Riot Game Name (without #tag): ").strip()
    tag_line = input("Enter your Riot Tagline (after #): ").strip()

    # Get PUUID
    puuid, actual_game_name, actual_tag_line = get_puuid(game_name, tag_line)

    if puuid:
        print(f"\nFound Account: {actual_game_name}#{actual_tag_line}")
        print(f"PUUID: {puuid}")

        # Determine the summoner's actual region
        summoner_region, match_region = get_summoner_region(puuid)

        if summoner_region and match_region:
            # Get Match History
            match_ids = get_match_history(puuid, match_region)

            if match_ids:
                print("\nLast 20 Matches:")
                arena_matches = []

                for idx, match_id in enumerate(match_ids, start=1):
                    is_arena, _ = get_match_details(match_id, match_region)
                    if is_arena:
                        print(f"{idx}. {match_id} (Arena)")
                        arena_matches.append(match_id)
                    else:
                        print(f"{idx}. {match_id} (Not Arena)")

                if arena_matches:
                    # Get details of the most recent Arena match
                    last_arena_match = arena_matches[0]
                    print(f"\nRecent Arena Matches with Players:\n")
                    print(f"Last Arena Match ID: {last_arena_match}\n")

                    _, teams = get_match_details(last_arena_match, match_region)
                    if teams:
                        for team_name, players in teams.items():
                            print(f"Team {team_name}:")
                            for player in players:
                                print(f"- {player}")
                            print("")  # Extra line for readability
                    else:
                        print("Could not retrieve team details.")
                else:
                    print("No recent Arena matches found.")
            else:
                print("Could not retrieve match history.")
        else:
            print("Could not determine the correct region.")
    else:
        print("Could not find PUUID. Check your game name and tagline.")


if __name__ == "__main__":
    main()
