from api_key import API_KEY
from requests import get

# Combined dictionary for both Summoner API server and Match History region
REGION_DATA = {
    "NA":   ("na1", "americas"),
    "BR":   ("br1", "americas"),
    "LAN":  ("la1", "americas"),
    "LAS":  ("la2", "americas"),
    "EUW":  ("euw1", "europe"),
    "EUNE": ("eun1", "europe"),
    "TR":   ("tr1", "europe"),
    "RU":   ("ru", "europe"),
    "KR":   ("kr", "asia"),
    "JP":   ("jp1", "asia"),
    "OCE":  ("oc1", "sea"),
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
    for (server, match_region) in REGION_DATA.values():
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
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={start}&count={count}&api_key={API_KEY}"
    headers = {"X-Riot-Token": API_KEY}

    response = get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    print(f"Error {response.status_code}: {response.text}")
    return None


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
                for idx, match_id in enumerate(match_ids, start=1):
                    print(f"{idx}. {match_id}")
            else:
                print("Could not retrieve match history.")
        else:
            print("Could not determine the correct region.")
    else:
        print("Could not find PUUID. Check your game name and tagline.")


if __name__ == "__main__":
    main()
