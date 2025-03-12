from flask import Flask, render_template
from api_key import API_KEY
from requests import get

app = Flask(__name__)

REGION_DATA = {
    "KR": ("kr", "asia"),
    "EUW": ("euw1", "europe"),
    "VN": ("vn", "asia"),
    "EUNE": ("eun1", "europe"),
    "BR": ("br1", "americas"),
    "NA": ("na1", "americas"),
    "LAN": ("la1", "americas"),
    "TR": ("tr1", "europe"),
    "LAS": ("la2", "americas"),
    "PH": ("ph", "sea"),
    "OCE": ("oc1", "sea"),
    "JP": ("jp1", "asia"),
}

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


def get_puuid(game_name, tag_line):
    """Fetch PUUID using Riot ID (game name + tag)"""
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["puuid"]
    
    print(f"Error retrieving PUUID: {response.status_code} - {response.text}")
    return None


def get_summoner_region(puuid):
    """Determine the summoner's region by checking all possible servers"""
    for (server, match_region) in REGION_DATA.values():
        if fetch_summoner_info(server, puuid):
            print(f"Found summoner in {server.upper()} (Match Region: {match_region})")
            return server, match_region
    
    print("Could not determine summoner's region.")
    return None, None


def fetch_summoner_info(server, puuid):
    """Helper function to check if summoner exists in a specific server"""
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)

    if response.status_code == 200:
        return response.json()

    print(f"Error fetching from {server.upper()}: {response.status_code} - {response.text}")
    return None


def get_match_history(puuid, region, count=5):
    """Fetch recent match history using PUUID"""
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    match_ids = response.json()
    print(f"Match IDs Retrieved: {match_ids}")
    
    return match_ids if match_ids else None


def get_match_details(match_id, region):
    """Fetch match details and process only Arena (CHERRY) matches"""
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()
    if data.get("info", {}).get("gameMode") != "CHERRY":
        return None
    
    return process_participants(data["info"]["participants"])


def process_participants(participants):
    """Process participants into structured team data, sorted by placement."""
    teams = {}
    team_kills = {}
    team_placement = {}

    # Collect total kills & placements for each team
    for player in participants:
        team_id = player["playerSubteamId"]
        team_name = TEAM_NAMES.get(team_id, f"Unknown Team {team_id}")

        if team_name not in team_kills:
            team_kills[team_name] = 0
        team_kills[team_name] += player["kills"]

        if team_name not in team_placement:
            team_placement[team_name] = player["placement"]  # Store team placement

    # Organize players into teams
    for player in participants:
        team_id = player["playerSubteamId"]
        team_name = TEAM_NAMES.get(team_id, f"Unknown Team {team_id}")

        player_info = format_player_info(player, team_kills.get(team_name, 1))

        if team_name not in teams:
            teams[team_name] = {
                "placement": team_placement[team_name],  # Include placement
                "players": []
            }
        teams[team_name]["players"].append(player_info)

    # Sort teams by placement (lower placement = higher rank)
    return dict(sorted(teams.items(), key=lambda x: x[1]["placement"]))


def format_player_info(player, team_total_kills):
    kills = player["kills"]
    deaths = player["deaths"]
    assists = player["assists"]

    kda_ratio = f"{(kills + assists) / max(1, deaths):.2f}:1"
    kill_participation = f"{((kills + assists) / max(1, team_total_kills)) * 100:.2f}%"

    # Get Augments (only non-empty ones)
    augments = [str(player.get(f"playerAugment{i}", "N/A")) for i in range(6)]
    augments = [a for a in augments if a != "N/A"]
    augments_str = ", ".join(augments) if augments else "None"

    # Get Item IDs (only non-zero values)
    items = [str(player.get(f"item{i}", 0)) for i in range(7)]  # Fetch item slots
    items = [i for i in items if i != "0"]  # Filter out empty slots
    items_str = ", ".join(items) if items else "None"

    return {
        "summoner_name": f"{player.get('riotIdGameName', 'Unknown')}#{player.get('riotIdTagline', '0000')}",
        "level": player["champLevel"],
        "champion": player["championName"],
        "kda": f"{kills}/{deaths}/{assists}",
        "kda_ratio": kda_ratio,
        "kill_participation": kill_participation,
        "total_damage": player["totalDamageDealtToChampions"],
        "total_damage_taken": player["totalDamageTaken"],
        "gold_earned": player["goldEarned"],
        "augments": augments_str,
        "items_inv": items_str
    }


@app.route("/")
def home():
    """Main Flask route to fetch and display Arena match history"""
    game_name, tag_line = "wybo", "plstn"

    # Get PUUID
    puuid = get_puuid(game_name, tag_line)
    if not puuid:
        return "Error retrieving player data."

    # Determine the correct region
    summoner_region, match_region = get_summoner_region(puuid)
    if not summoner_region or not match_region:
        return "Error: Could not determine the correct region."

    # Get match history
    match_ids = get_match_history(puuid, match_region)
    if not match_ids:
        return "No match history available."

    # Process matches
    matches = []
    for match_id in match_ids:
        teams = get_match_details(match_id, match_region)
        if teams:
            matches.append({"match_id": match_id, "teams": teams})

    return render_template("arena_matches.html", arena_matches=matches)


if __name__ == "__main__":
    app.run(debug=True)
