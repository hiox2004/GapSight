from fastapi import APIRouter, Query, Body
from app.database import supabase, retry_on_disconnect
from collections import defaultdict
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
@retry_on_disconnect()
def get_summary(username: str = Query(default="my_brand")):
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return {}
    user_id = user.data[0]["id"]

    followers = supabase.table("follower_metrics") \
        .select("follower_count, recorded_at") \
        .eq("user_id", user_id) \
        .order("recorded_at", desc=True) \
        .limit(1).execute()
    if not followers.data:
        return {}
    total_followers = followers.data[0]["follower_count"]

    all_followers = supabase.table("follower_metrics") \
        .select("follower_count") \
        .eq("user_id", user_id) \
        .order("recorded_at", desc=False).execute()
    older_count = all_followers.data[0]["follower_count"] if all_followers.data else total_followers
    growth_pct = round(((total_followers - older_count) / older_count) * 100, 1) if older_count > 0 else 0

    posts = supabase.table("posts").select("*").eq("user_id", user_id).execute()
    post_data = posts.data

    total_engagement = sum(p["likes"] + p["comments"] + p["shares"] for p in post_data)
    avg_engagement = round(total_engagement / len(post_data), 1) if post_data else 0
    engagement_rate = round((avg_engagement / total_followers) * 100, 2) if total_followers else 0

    content_counts = defaultdict(int)
    for p in post_data:
        content_counts[p["content_type"]] += 1
    top_content = max(content_counts, key=content_counts.get) if content_counts else "N/A"

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent_posts = supabase.table("posts").select("id") \
        .eq("user_id", user_id) \
        .gte("posted_at", week_ago).execute()
    posts_this_week = len(recent_posts.data)

    return {
        "follower_count": total_followers,
        "follower_growth_pct": growth_pct,
        "avg_engagement": avg_engagement,
        "top_content_type": top_content,
        "posts_per_week": posts_this_week
    }


@router.get("/followers")
@retry_on_disconnect()
def get_follower_growth(username: str = Query(default="my_brand")):
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    result = supabase.table("follower_metrics") \
        .select("follower_count, recorded_at") \
        .eq("user_id", user_id) \
        .order("recorded_at", desc=False).execute()

    data = result.data[::7] if result.data else []
    return [{"date": r["recorded_at"][:10], "followers": r["follower_count"]} for r in data]


@router.get("/content-types")
@retry_on_disconnect()
def get_content_types(username: str = Query(default="my_brand")):
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    posts = supabase.table("posts").select("content_type, likes, comments, shares") \
        .eq("user_id", user_id).execute()

    counts = defaultdict(lambda: {"count": 0, "total_engagement": 0})
    for p in posts.data:
        ct = p["content_type"]
        counts[ct]["count"] += 1
        counts[ct]["total_engagement"] += p["likes"] + p["comments"] + p["shares"]

    return [
        {
            "content_type": ct,
            "count": v["count"],
            "avg_engagement": round(v["total_engagement"] / v["count"], 1)
        }
        for ct, v in counts.items()
    ]


@router.get("/frequency-correlation")
@retry_on_disconnect()
def get_frequency_correlation(username: str = Query(default="my_brand")):
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    posts = supabase.table("posts").select("posted_at, likes, comments, shares") \
        .eq("user_id", user_id).execute()

    weekly = defaultdict(lambda: {"posts": 0, "total_engagement": 0})
    for p in posts.data:
        week = p["posted_at"][:7]
        weekly[week]["posts"] += 1
        weekly[week]["total_engagement"] += p["likes"] + p["comments"] + p["shares"]

    return [
        {
            "week": week,
            "post_count": v["posts"],
            "avg_engagement": round(v["total_engagement"] / v["posts"], 1)
        }
        for week, v in sorted(weekly.items())
    ]


@router.get("/post-performance")
@retry_on_disconnect()
def get_post_performance(username: str = Query(default="my_brand")):
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return []
    user_id = user.data[0]["id"]

    posts = supabase.table("posts").select(
        "posted_at, likes, comments, shares, content_type"
    ).eq("user_id", user_id).order("posted_at", desc=False).execute()

    items = []
    for p in posts.data:
        total_engagement = p["likes"] + p["comments"] + p["shares"]
        items.append(
            {
                "date": p["posted_at"][:10],
                "engagement": total_engagement,
                "content_type": p["content_type"],
            }
        )

    return items


@router.get("/trend-prediction")
@retry_on_disconnect()
def get_trend_prediction(username: str = Query(default="my_brand")):
    """Forecast follower trend for the next 4 weeks using linear regression."""
    history = get_follower_growth(username=username)
    if len(history) < 2:
        return history

    x_values = list(range(len(history)))
    y_values = [point["followers"] for point in history]

    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(y_values) / len(y_values)

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denominator = sum((x - mean_x) ** 2 for x in x_values)
    slope = (numerator / denominator) if denominator else 0
    intercept = mean_y - (slope * mean_x)

    points = [
        {"date": point["date"], "followers": point["followers"], "type": "actual"}
        for point in history
    ]

    last_date = datetime.fromisoformat(history[-1]["date"])
    start_index = len(history)
    for step in range(1, 5):
        idx = start_index + step - 1
        prediction = max(0, round(intercept + slope * idx))
        points.append(
            {
                "date": (last_date + timedelta(days=7 * step)).strftime("%Y-%m-%d"),
                "followers": prediction,
                "type": "predicted",
            }
        )

    return points

@router.get("/users")
@retry_on_disconnect()
def get_users():
    result = supabase.table("users").select("id, username, platform").execute()
    return result.data if result.data else []

from fastapi import Body

@router.post("/users")
@retry_on_disconnect()
def create_user(username: str = Body(...), platform: str = Body(default="instagram")):
    existing = supabase.table("users").select("id").eq("username", username).execute()
    if existing.data:
        return {"error": "Username already exists"}
    result = supabase.table("users").insert({"username": username, "platform": platform}).execute()
    return result.data[0] if result.data else {"error": "Failed to create user"}