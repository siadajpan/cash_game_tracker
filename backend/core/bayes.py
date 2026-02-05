import math
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models.game import Game
from backend.db.models.buy_in import BuyIn
from backend.db.models.add_on import AddOn
from backend.db.models.cash_out import CashOut
from backend.db.models.player_request_status import PlayerRequestStatus

def get_bayes_predictions(game_id: int, db: Session):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        return []

    team_id = game.team_id
    players = game.players
    num_players = len(players)
    if num_players == 0:
        return []
    
    # 1. Get all team games to calculate team-wide priors
    all_team_games = db.query(Game.id, Game.start_time, Game.finish_time).filter(Game.team_id == team_id).all()
    team_game_ids = [g.id for g in all_team_games]
    
    # 2. Get all historical transactions for the team to calculate per-player per-game stats
    all_bis = db.query(BuyIn.user_id, BuyIn.game_id, BuyIn.amount).filter(BuyIn.game_id.in_(team_game_ids)).all()
    all_aos = db.query(AddOn.user_id, AddOn.game_id, AddOn.amount).filter(AddOn.game_id.in_(team_game_ids), AddOn.status == PlayerRequestStatus.APPROVED).all()
    all_cos = db.query(CashOut.user_id, CashOut.game_id, CashOut.amount).filter(CashOut.game_id.in_(team_game_ids)).all()
    
    player_game_net = defaultdict(lambda: defaultdict(float))
    for u, g, a in all_bis: player_game_net[u][g] -= a
    for u, g, a in all_aos: player_game_net[u][g] -= a
    for u, g, a in all_cos: player_game_net[u][g] += a
    
    # 3. Calculate metrics for all players in the team
    team_metrics = []
    player_stats = {}
    
    for uid, g_map in player_game_net.items():
        bals = list(g_map.values())
        if not bals: continue
        
        n = len(bals)
        avg = sum(bals) / n
        var = sum((b - avg)**2 for b in bals) / n if n > 1 else 0
        sd = math.sqrt(var)
        
        player_stats[uid] = {
            "avg": avg,
            "sd": sd,
            "n": n
        }
        if n >= 3: # Lower threshold for prior to include more context
            team_metrics.append({"avg": avg, "sd": sd})
            
    # Fallback priors
    prior_mean = sum(m["avg"] for m in team_metrics) / len(team_metrics) if team_metrics else 0
    avg_team_sd = sum(m["sd"] for m in team_metrics) / len(team_metrics) if team_metrics else 100
    
    intermediate_results = []
    total_post_mean = 0
    
    # 4. First pass: Calculate independent Bayesian posteriors
    for p in players:
        stats = player_stats.get(p.id, {"avg": 0, "sd": 0, "n": 0})
        
        n_games = stats["n"]

        # Likelihood
        lik_mean = stats["avg"]
        # Use population variance if sample size is too small to estimate player variance reliably
        # This prevents "unknown" players from having tiny curves just because their few games were similar
        if n_games < 10 or stats["sd"] <= 0:
            lik_sigma = avg_team_sd if avg_team_sd > 0 else 100
        else:
            lik_sigma = stats["sd"]
        
        # Bayesian Update
        p_sigma = avg_team_sd if avg_team_sd > 0 else 100
        p_mean = prior_mean
        
        if p_sigma > 0 and lik_sigma > 0:
            p_var = p_sigma**2
            l_var = lik_sigma**2
            post_var = 1 / ((1/p_var) + (n_games/l_var))
            post_mean = post_var * ((p_mean/p_var) + (n_games*lik_mean/l_var))
            post_sigma = math.sqrt(post_var)
        else:
            post_mean = lik_mean
            post_sigma = lik_sigma
            
        pred_sigma = math.sqrt(post_sigma**2 + lik_sigma**2)
        total_post_mean += post_mean
        
        intermediate_results.append({
            "player": p,
            "mu_raw": post_mean,
            "sigma": pred_sigma,
            "n_games": n_games
        })

    # 5. Second pass: Adjust for Zero-Sum (Competitive Adjustment)
    # Poker is zero-sum. If 3 winners play together, they can't all win on average.
    # We subtract the "table bias" from each player's expectation.
    table_bias = total_post_mean / num_players
    
    results = []
    for ir in intermediate_results:
        # Adjusted mean for this specific pod
        mu_adj = ir["mu_raw"] - table_bias
        sigma = ir["sigma"]
        
        if sigma > 0:
            z = (0 - mu_adj) / sigma
            win_prob = 0.5 * (1 - math.erf(z / math.sqrt(2)))
        else:
            win_prob = 1.0 if mu_adj > 0 else (0.5 if mu_adj == 0 else 0.0)
            
        if ir["n_games"] < 5:
            reliability = "Low (Need more games)"
        elif ir["n_games"] < 15:
            reliability = "Moderate"
        else:
            reliability = "High"

        results.append({
            "player": ir["player"],
            "win_prob": win_prob * 100,
            "mu": mu_adj,
            "sigma": sigma,
            "n_games": ir["n_games"],
            "reliability": reliability
        })
        
    # 6. Normalize for Heads-Up (2 players)
    # In a zero-sum 2-player game, the probabilities of finishing positive should be complementary.
    # We normalize them to sum to 100% to match user intuition (avg 50%).
    if num_players == 2:
        total_p = sum(r["win_prob"] for r in results)
        if total_p > 0:
            for r in results:
                r["win_prob"] = (r["win_prob"] / total_p) * 100.0
        
    return results
