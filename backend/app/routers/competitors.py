from fastapi import APIRouter
from app.database import get_supabase_client, retry_on_disconnect
from collections import defaultdict

router = APIRouter(prefix="/competitors", tags=["competitors"])


@router.get("/list")
@retry_on_disconnect()
def get_competitors():
    client = get_supabase_client()

    user = client.table("users").select("id").eq("username", "my_brand").execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    result = client.table("competitors").select("*") \
        .eq("owner_id", user_id).execute()
    return result.data


@router.get("/compare")
@retry_on_disconnect()
def compare_competitors():
    client = get_supabase_client()

    user = client.table("users").select("id").eq("username", "my_brand").execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    # My latest followers + engagement
    my_followers = client.table("follower_metrics") \
        .select("follower_count").eq("user_id", user_id) \
        .order("recorded_at", desc=True).limit(1).execute()
    if not my_followers.data:
        my_follower_count = 0
    else:
        my_follower_count = my_followers.data[0]["follower_count"]

    my_posts = client.table("posts").select("likes, comments, shares") \
        .eq("user_id", user_id).execute()
    my_engagement = round(
        sum(p["likes"] + p["comments"] + p["shares"] for p in my_posts.data) / len(my_posts.data), 1
    ) if my_posts.data else 0

    result = [{"username": "my_brand", "follower_count": my_follower_count, "avg_engagement": my_engagement}]

    # Each competitor's latest metrics
    competitors = client.table("competitors").select("id, username") \
        .eq("owner_id", user_id).execute()

    for comp in competitors.data:
        metrics = client.table("competitor_metrics") \
            .select("follower_count, avg_likes, avg_comments, avg_shares") \
            .eq("competitor_id", comp["id"]) \
            .order("recorded_at", desc=True).limit(1).execute()

        if metrics.data:
            m = metrics.data[0]
            avg_eng = round(m["avg_likes"] + m["avg_comments"] + m["avg_shares"], 1)
            result.append({
                "username": comp["username"],
                "follower_count": m["follower_count"],
                "avg_engagement": avg_eng
            })

    return result


@router.get("/growth")
@retry_on_disconnect()
def competitor_growth():
    client = get_supabase_client()

    user = client.table("users").select("id").eq("username", "my_brand").execute()
    user_id = user.data[0]["id"]

    # My growth
    my_data = client.table("follower_metrics") \
        .select("follower_count, recorded_at") \
        .eq("user_id", user_id) \
        .order("recorded_at", desc=False).execute()
    my_sampled = my_data.data[::7]

    series = [{
        "name": "my_brand",
        "data": [{"date": r["recorded_at"][:10], "followers": r["follower_count"]} for r in my_sampled]
    }]

    # Competitor growth
    competitors = client.table("competitors").select("id, username") \
        .eq("owner_id", user_id).execute()

    for comp in competitors.data:
        comp_data = client.table("competitor_metrics") \
            .select("follower_count, recorded_at") \
            .eq("competitor_id", comp["id"]) \
            .order("recorded_at", desc=False).execute()
        sampled = comp_data.data[::7]
        series.append({
            "name": comp["username"],
            "data": [{"date": r["recorded_at"][:10], "followers": r["follower_count"]} for r in sampled]
        })

    return series


@router.get("/gaps")
@retry_on_disconnect()
def get_gaps():
    client = get_supabase_client()

    user = client.table("users").select("id").eq("username", "my_brand").execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    # Get all user's posts to calculate content type usage
    my_posts = client.table("posts").select("content_type, likes, comments, shares") \
        .eq("user_id", user_id).execute()
    
    # Calculate user's content type counts
    my_content_counts = defaultdict(int)
    my_engagement = 0
    for p in my_posts.data:
        my_content_counts[p["content_type"]] += 1
        my_engagement += p["likes"] + p["comments"] + p["shares"]
    
    my_engagement = round(my_engagement / len(my_posts.data), 1) if my_posts.data else 0
    total_posts = len(my_posts.data)
    distinct_content_types = max(len(my_content_counts), 1)
    baseline_target_usage = max(3, round(total_posts / distinct_content_types) + 1)

    competitors = client.table("competitors").select("id, username") \
        .eq("owner_id", user_id).execute()

    gaps = []
    for comp in competitors.data:
        metrics = client.table("competitor_metrics") \
            .select("follower_count, avg_likes, avg_comments, avg_shares, top_content_type") \
            .eq("competitor_id", comp["id"]) \
            .order("recorded_at", desc=True).limit(1).execute()

        if metrics.data:
            m = metrics.data[0]
            comp_engagement = round(m["avg_likes"] + m["avg_comments"] + m["avg_shares"], 1)
            
            # Get user's usage of this content type
            their_top_content = m["top_content_type"] or "N/A"
            your_usage_count = my_content_counts.get(their_top_content, 0)
            usage_gap = max(0, baseline_target_usage - your_usage_count)
            engagement_gap = max(0, round((comp_engagement - my_engagement) / 10))
            combined_gap = max(usage_gap, engagement_gap)
            
            gaps.append({
                "competitor": comp["username"],
                "their_top_content": their_top_content,
                "your_usage": your_usage_count,
                "gap": combined_gap,
                "why": (
                    "Increase this format to close both usage and engagement differences"
                    if combined_gap > 0
                    else "You are already matching this content pattern"
                )
            })

    return gaps
