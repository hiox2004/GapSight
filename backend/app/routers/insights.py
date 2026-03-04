from fastapi import APIRouter, Query
from app.database import get_supabase_client, retry_on_disconnect
from app.routers.competitors import get_gaps
import os
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])

groq_client = None
try:
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        groq_client = Groq(api_key=api_key)
except Exception as e:
    logger.warning(f"Groq client not initialized: {e}")


def build_summary(username: str = "my_brand"):
    supabase = get_supabase_client()
    user = supabase.table("users").select("id").eq("username", username).execute()
    if not user.data:
        return {}
    user_id = user.data[0]["id"]

    followers = supabase.table("follower_metrics") \
        .select("follower_count") \
        .eq("user_id", user_id) \
        .order("recorded_at", desc=True) \
        .limit(1).execute()
    my_followers = followers.data[0]["follower_count"] if followers.data else 0

    posts = supabase.table("posts").select("likes, comments, shares, content_type").eq("user_id", user_id).execute()
    post_data = posts.data or []
    total_eng = sum(p["likes"] + p["comments"] + p["shares"] for p in post_data)
    avg_eng = round(total_eng / len(post_data), 1) if post_data else 0
    engagement_rate = round((avg_eng / my_followers) * 100, 2) if my_followers else 0

    from collections import defaultdict
    counts = defaultdict(int)
    for p in post_data:
        counts[p["content_type"]] += 1
    top_content = max(counts, key=counts.get) if counts else "N/A"

    from datetime import datetime, timedelta
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent = supabase.table("posts").select("id").eq("user_id", user_id).gte("posted_at", week_ago).execute()
    posts_per_week = len(recent.data) if recent.data else 0

    competitors = supabase.table("competitors").select("username").eq("owner_id", user_id).execute()
    comp_followers_list = []
    comp_eng_list = []

    for c in (competitors.data or []):
        cname = c["username"]
        cid_res = supabase.table("users").select("id").eq("username", cname).execute()
        if not cid_res.data:
            continue
        cid = cid_res.data[0]["id"]

        c_followers = supabase.table("follower_metrics") \
            .select("follower_count") \
            .eq("user_id", cid) \
            .order("recorded_at", desc=True) \
            .limit(1).execute()
        if c_followers.data:
            comp_followers_list.append(c_followers.data[0]["follower_count"])

        c_posts = supabase.table("posts").select("likes, comments, shares").eq("user_id", cid).execute()
        if c_posts.data:
            total = sum(p["likes"] + p["comments"] + p["shares"] for p in c_posts.data)
            comp_eng_list.append(round(total / len(c_posts.data), 1))

    avg_comp_followers = round(sum(comp_followers_list) / len(comp_followers_list), 1) if comp_followers_list else 0
    avg_comp_eng = round(sum(comp_eng_list) / len(comp_eng_list), 1) if comp_eng_list else 0

    return {
        "username": username,
        "my_followers": my_followers,
        "my_engagement_rate": engagement_rate,
        "my_avg_engagement": avg_eng,
        "my_top_content": top_content,
        "my_posts_per_week": posts_per_week,
        "avg_competitor_followers": avg_comp_followers,
        "avg_competitor_engagement": avg_comp_eng,
    }


def _default_insights(summary: dict, gaps: list) -> dict:
    recs = []
    if summary.get("avg_competitor_engagement", 0) > summary.get("my_avg_engagement", 0):
        recs.append("Competitors have higher engagement — focus on more interactive content formats.")
    if gaps:
        top_gap = max(gaps, key=lambda g: g.get("gap_score", 0))
        recs.append(f"Biggest content gap is {top_gap['top_content_type']} — consider posting more of it.")
    if summary.get("my_posts_per_week", 0) < 3:
        recs.append("Posting frequency is low — aim for at least 3–5 posts per week.")
    while len(recs) < 3:
        recs.append("Keep monitoring competitor activity and adjust your content mix regularly.")

    return {
        "what_competitors_do_better": f"Competitors average {summary.get('avg_competitor_engagement', 0)} engagements vs your {summary.get('my_avg_engagement', 0)}.",
        "content_gaps": gaps[0]["recommendation"] if gaps else "No significant content gaps detected.",
        "best_time_to_post": "Insufficient data to determine best posting time.",
        "recommendations": recs[:3],
    }


def _normalize_insights(raw: dict, fallback: dict) -> dict:
    required = ["what_competitors_do_better", "content_gaps", "best_time_to_post", "recommendations"]
    result = {}
    for key in required:
        val = raw.get(key, fallback.get(key, ""))
        if key == "recommendations":
            if not isinstance(val, list) or len(val) < 1:
                val = fallback.get("recommendations", [])
            val = [str(r) for r in val[:3]]
            while len(val) < 3:
                val.append(fallback["recommendations"][0] if fallback.get("recommendations") else "Monitor and adjust your strategy.")
        else:
            val = str(val).strip() or str(fallback.get(key, ""))
        result[key] = val
    return result


@router.get("/")
def get_insights(username: str = Query(default="my_brand")):
    summary = build_summary(username=username)
    gaps = get_gaps(username=username)
    fallback = _default_insights(summary, gaps)

    if not groq_client:
        return {**fallback, "source": "rules"}

    try:
        prompt = f"""
You are a social media analytics assistant. Based ONLY on the data below, return a JSON object.

DATA:
{json.dumps(summary, indent=2)}

GAPS:
{json.dumps(gaps, indent=2)}

RULES:
- Every claim must map directly to a value in DATA or GAPS.
- If data is missing, say "insufficient data" — do not guess.
- Do not use external benchmarks.
- Return ONLY valid JSON with exactly these keys:
  - "what_competitors_do_better": string
  - "content_gaps": string
  - "best_time_to_post": string
  - "recommendations": array of exactly 3 short strings
"""
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()
        raw = json.loads(content)
        normalized = _normalize_insights(raw, fallback)
        return {**normalized, "source": "ai+rules"}
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return {**fallback, "source": "rules"}


@router.get("/workflows")
def get_workflows(username: str = Query(default="my_brand")):
    summary = build_summary(username=username)
    gaps = get_gaps(username=username)

    workflows = []

    if summary.get("my_posts_per_week", 0) < 3:
        workflows.append({
            "name": "Boost Posting Cadence",
            "trigger": f"Fewer than 3 posts per week detected for {username}.",
            "action": "Schedule at least 3–5 posts per week across your top content types."
        })

    if summary.get("my_engagement_rate", 0) < 2.0:
        workflows.append({
            "name": "Engagement Sprint",
            "trigger": f"Engagement rate below 2% for {username}.",
            "action": "Run a 60-minute engagement sprint after each post — reply to every comment within the first hour."
        })

    for gap in gaps[:2]:
        workflows.append({
            "name": f"Close {gap['top_content_type']} Gap",
            "trigger": f"Gap score of {gap['gap_score']} detected vs {gap['competitor']}.",
            "action": gap["recommendation"]
        })

    if not workflows:
        workflows.append({
            "name": "Maintain Winning Rhythm",
            "trigger": "All metrics are on track.",
            "action": "Keep your current posting schedule and monitor competitor activity weekly."
        })

    return workflows