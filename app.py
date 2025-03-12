from flask import Flask, render_template, request
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
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["puuid"]
    return None


def get_summoner_region(puuid):
    for (server, match_region) in REGION_DATA.values():
        if fetch_summoner_info(server, puuid):
            return server, match_region
    return None, None


def fetch_summoner_info(server, puuid):
    url = f"https://{server}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)
    return response.json() if response.status_code == 200 else None


def get_match_history(puuid, region, count=5):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)
    return response.json() if response.status_code == 200 else None


def get_match_details(match_id, region):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    response = get(url, headers=headers)
    if response.status_code != 200:
        return None
    data = response.json()
    return process_participants(data["info"]["participants"]) if data.get("info", {}).get("gameMode") == "CHERRY" else None


def process_participants(participants):
    teams = {}
    team_kills = {}
    team_placement = {}
    for player in participants:
        team_id = player["playerSubteamId"]
        team_name = TEAM_NAMES.get(team_id, f"Unknown Team {team_id}")
        if team_name not in team_kills:
            team_kills[team_name] = 0
        team_kills[team_name] += player["kills"]
        if team_name not in team_placement:
            team_placement[team_name] = player["placement"]

    for player in participants:
        team_id = player["playerSubteamId"]
        team_name = TEAM_NAMES.get(team_id, f"Unknown Team {team_id}")
        player_info = format_player_info(player, team_kills.get(team_name, 1))
        if team_name not in teams:
            teams[team_name] = {"placement": team_placement[team_name], "players": []}
        teams[team_name]["players"].append(player_info)

    return dict(sorted(teams.items(), key=lambda x: x[1]["placement"]))


def format_player_info(player, team_total_kills):
    kills, deaths, assists = player["kills"], player["deaths"], player["assists"]
    kda_ratio = f"{(kills + assists) / max(1, deaths):.2f}:1"
    kill_participation = f"{((kills + assists) / max(1, team_total_kills)) * 100:.2f}%"
    augments = [player.get(f"playerAugment{i}", "N/A") for i in range(6)]
    items = [player.get(f"item{i}", 0) for i in range(7)]
    return {
        "summoner_name": f"{player.get('riotIdGameName', 'Unknown')}#{player.get('riotIdTagline', '0000')}",
        "champion": player["championName"],
        "kda": f"{kills}/{deaths}/{assists}",
        "kda_ratio": kda_ratio,
        "kill_participation": kill_participation,
        "total_damage": player["totalDamageDealtToChampions"],
        "total_damage_taken": player["totalDamageTaken"],
        "gold_earned": player["goldEarned"],
        "augments": ", ".join([str(a) for a in augments if a != "N/A"]),
        "items_inv": ", ".join([str(i) for i in items if i != 0])
    }


@app.route("/", methods=["GET"])
def home():
    return render_template("search.html")


@app.route("/search", methods=["POST"])
def search():
    game_name = request.form.get("game_name")
    tag_line = request.form.get("tag_line")
    if not game_name or not tag_line:
        return "Error: Missing game name or tag line."

    puuid = get_puuid(game_name, tag_line)
    if not puuid:
        return "Error retrieving player data."

    summoner_region, match_region = get_summoner_region(puuid)
    if not summoner_region or not match_region:
        return "Error: Could not determine the correct region."

    match_ids = get_match_history(puuid, match_region)
    if not match_ids:
        return "No match history available."

    matches = []
    for match_id in match_ids:
        teams = get_match_details(match_id, match_region)
        if teams:
            matches.append({"match_id": match_id, "teams": teams})

    return render_template("arena_matches.html", arena_matches=matches)


if __name__ == "__main__":
    app.run(debug=True)
