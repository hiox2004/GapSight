from fastapi import APIRouter, Query, Body, HTTPException, BackgroundTasks
from collections import defaultdict
from app.database import get_supabase_client, retry_on_disconnect
from app.routers.sync import run_apify_historical

router = APIRouter(prefix="/competitors", tags=["competitors"])


def _get_user_id(supabase, username: str):
    """Return user_id for a username, or None."""
    res = supabase.table("users").select("id").eq("username", username).execute()
    return res.data[0]["id"] if res.data else None


@router.get("/list")
@retry_on_disconnect()
def get_competitors(username: str = Query(default="my_brand")):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, username)
    if not owner_id:
        return []
    # competitors.username holds the competitor's username as a plain string
    result = supabase.table("competitors").select("*").eq("owner_id", owner_id).execute()
    rows = result.data or []
    for row in rows:
        row["competitor_username"] = row.get("username", "")
    return rows


@router.get("/compare")
@retry_on_disconnect()
def compare_competitors(username: str = Query(default="my_brand")):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, username)
    if not owner_id:
        return []

    followers = supabase.table("follower_metrics") \
        .select("follower_count") \
        .eq("user_id", owner_id) \
        .order("recorded_at", desc=True) \
        .limit(1).execute()
    my_followers = followers.data[0]["follower_count"] if followers.data else 0

    posts = supabase.table("posts").select("likes, comments, shares").eq("user_id", owner_id).execute()
    if posts.data:
        total_eng = sum(p["likes"] + p["comments"] + p["shares"] for p in posts.data)
        my_avg_eng = round(total_eng / len(posts.data), 1)
    else:
        my_avg_eng = 0

    result = [{"name": username, "followers": my_followers, "avg_engagement": my_avg_eng}]

    competitors = supabase.table("competitors").select("username").eq("owner_id", owner_id).execute()
    for c in (competitors.data or []):
        cname = c["username"]
        cid = _get_user_id(supabase, cname)
        if not cid:
            result.append({"name": cname, "followers": 0, "avg_engagement": 0})
            continue

        c_followers = supabase.table("follower_metrics") \
            .select("follower_count") \
            .eq("user_id", cid) \
            .order("recorded_at", desc=True) \
            .limit(1).execute()
        c_follower_count = c_followers.data[0]["follower_count"] if c_followers.data else 0

        c_posts = supabase.table("posts").select("likes, comments, shares").eq("user_id", cid).execute()
        if c_posts.data:
            c_total = sum(p["likes"] + p["comments"] + p["shares"] for p in c_posts.data)
            c_avg_eng = round(c_total / len(c_posts.data), 1)
        else:
            c_avg_eng = 0

        result.append({"name": cname, "followers": c_follower_count, "avg_engagement": c_avg_eng})

    return result


@router.get("/growth")
@retry_on_disconnect()
def competitor_growth(username: str = Query(default="my_brand")):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, username)
    if not owner_id:
        return []

    my_metrics = supabase.table("follower_metrics") \
        .select("follower_count, recorded_at") \
        .eq("user_id", owner_id) \
        .order("recorded_at", desc=False).execute()
    my_series = [{"date": r["recorded_at"][:10], "followers": r["follower_count"]} for r in (my_metrics.data or [])[::7]]
    all_series = [{"name": username, "data": my_series}]

    competitors = supabase.table("competitors").select("username").eq("owner_id", owner_id).execute()
    for c in (competitors.data or []):
        cname = c["username"]
        cid = _get_user_id(supabase, cname)
        if not cid:
            all_series.append({"name": cname, "data": []})
            continue
        metrics = supabase.table("follower_metrics") \
            .select("follower_count, recorded_at") \
            .eq("user_id", cid) \
            .order("recorded_at", desc=False).execute()
        series = [{"date": r["recorded_at"][:10], "followers": r["follower_count"]} for r in (metrics.data or [])[::7]]
        all_series.append({"name": cname, "data": series})

    return all_series


@router.get("/gaps")
@retry_on_disconnect()
def get_gaps(username: str = Query(default="my_brand")):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, username)
    if not owner_id:
        return []

    posts = supabase.table("posts").select("content_type, likes, comments, shares").eq("user_id", owner_id).execute()
    counts = defaultdict(int)
    total_eng = 0
    for p in (posts.data or []):
        counts[p["content_type"]] += 1
        total_eng += p["likes"] + p["comments"] + p["shares"]
    total_posts = len(posts.data) if posts.data else 1
    my_avg_eng = total_eng / total_posts
    num_types = len(counts) or 1
    baseline = total_posts / num_types

    gaps = []
    competitors = supabase.table("competitors").select("username").eq("owner_id", owner_id).execute()
    for c in (competitors.data or []):
        cname = c["username"]
        cid = _get_user_id(supabase, cname)
        if not cid:
            continue

        c_posts = supabase.table("posts") \
            .select("content_type, likes, comments, shares") \
            .eq("user_id", cid).execute()
        if not c_posts.data:
            continue

        type_metrics = defaultdict(lambda: {"count": 0, "total_eng": 0})
        for p in c_posts.data:
            ct = p["content_type"]
            type_metrics[ct]["count"] += 1
            type_metrics[ct]["total_eng"] += p["likes"] + p["comments"] + p["shares"]

        top_type = max(
            type_metrics,
            key=lambda t: type_metrics[t]["total_eng"] / max(type_metrics[t]["count"], 1)
        )

        # Competitor's avg engagement specifically for their top content type
        comp_type_posts = [p for p in c_posts.data if p["content_type"] == top_type]
        comp_type_eng = (
            sum(p["likes"] + p["comments"] + p["shares"] for p in comp_type_posts) / len(comp_type_posts)
            if comp_type_posts else 0
        )

        # Your avg engagement for that same content type
        my_type_posts = [p for p in (posts.data or []) if p["content_type"] == top_type]
        my_type_eng = (
            sum(p["likes"] + p["comments"] + p["shares"] for p in my_type_posts) / len(my_type_posts)
            if my_type_posts else 0
        )

        # Gap score = how much % more engagement competitor gets in that type vs you
        # 100 means you don't post it at all; negative means you actually outperform them
        if my_type_eng > 0:
            gap_score = round(((comp_type_eng - my_type_eng) / my_type_eng) * 100, 1)
        else:
            gap_score = 100.0

        my_usage = counts.get(top_type, 0)
        gaps.append({
            "competitor": cname,
            "top_content_type": top_type,
            "my_usage": my_usage,
            "gap_score": gap_score,
            "recommendation": (
                f"{cname} gets {gap_score}% more engagement per {top_type} post than you. "
                f"Consider posting more {top_type} content."
                if gap_score > 0 else
                f"You outperform {cname} on {top_type} content — keep it up."
            )
        })

    return gaps


@router.post("/")
@retry_on_disconnect()
def add_competitor(
    background_tasks: BackgroundTasks,
    owner_username: str = Body(...),
    competitor_username: str = Body(...),
    platform: str = Body(default="instagram")
):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, owner_username)
    if not owner_id:
        raise HTTPException(status_code=400, detail="Owner user not found")

    # Check duplicate
    already = supabase.table("competitors").select("id") \
        .eq("owner_id", owner_id).eq("username", competitor_username).execute()
    if already.data:
        raise HTTPException(status_code=400, detail="Competitor already added")

    # Ensure competitor has a user row so /sync and analytics lookups work
    comp_id = _get_user_id(supabase, competitor_username)
    if not comp_id:
        new_user = supabase.table("users").insert({"username": competitor_username, "platform": platform}).execute()
        comp_id = new_user.data[0]["id"] if new_user.data else None

    result = supabase.table("competitors").insert({
        "owner_id": owner_id,
        "username": competitor_username,
        "platform": platform,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to add competitor")

    # Kick off Apify history fetch for this competitor in the background
    if comp_id:
        background_tasks.add_task(run_apify_historical, comp_id, competitor_username)

    return result.data[0]


@router.delete("/{competitor_username}")
@retry_on_disconnect()
def remove_competitor(competitor_username: str, owner_username: str = Query(...)):
    supabase = get_supabase_client()
    owner_id = _get_user_id(supabase, owner_username)
    if not owner_id:
        raise HTTPException(status_code=400, detail="Owner user not found")

    supabase.table("competitors") \
        .delete() \
        .eq("owner_id", owner_id) \
        .eq("username", competitor_username) \
        .execute()
    return {"success": True}