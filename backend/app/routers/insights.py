from fastapi import APIRouter
from app.database import get_supabase_client, retry_on_disconnect
from app.routers.competitors import get_gaps
from collections import defaultdict
import os
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter(prefix="/insights", tags=["insights"])
_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        _groq_client = Groq(api_key=api_key)
    except Exception:
        _groq_client = None
    return _groq_client


def _default_insights(summary, gaps):
    my_engagement = summary.get("my_engagement_rate", 0)
    comp_engagement = summary.get("avg_competitor_engagement", 0)
    my_posts_per_week = summary.get("my_posts_per_week", 0)

    top_gap = gaps[0] if gaps else None
    top_types = [t for t in summary.get("competitor_top_contents", []) if t]
    top_types_text = ", ".join(top_types[:3]) if top_types else "mixed formats"

    if comp_engagement > my_engagement:
        better_line = (
            f"Competitors are averaging higher engagement ({comp_engagement}) than your current rate ({my_engagement}%). "
            f"They also show stronger consistency around {top_types_text}."
        )
    else:
        better_line = (
            "Your engagement is at or above competitor averages, but consistency and repeatable content systems still matter. "
            f"Top competitor formats currently include {top_types_text}."
        )

    if top_gap and top_gap.get("gap", 0) > 0:
        content_gaps = (
            f"The largest gap is in {top_gap.get('their_top_content', 'high-performing')} content. "
            f"You currently post it {top_gap.get('your_usage', 0)} times, and adding about {top_gap.get('gap', 0)} more posts can close the gap faster."
        )
    else:
        content_gaps = (
            "No severe format gap is detected right now. Focus on quality improvements and testing post hooks, captions, and CTAs."
        )

    if my_posts_per_week < 4:
        best_time_to_post = "Post at a fixed peak window 4 times/week and review 24-hour engagement before repeating the slot."
    else:
        best_time_to_post = "Keep your current posting cadence and prioritize the two highest-performing time windows each week."

    return {
        "what_competitors_do_better": better_line,
        "content_gaps": content_gaps,
        "best_time_to_post": best_time_to_post,
        "recommendations": [
            "Publish consistently each week and avoid long posting gaps.",
            "Increase output in the top competitor content formats.",
            "Review performance weekly and double down on top-performing formats.",
        ],
    }


def _normalize_insights(payload, fallback):
    if not isinstance(payload, dict):
        return fallback

    normalized = {
        "what_competitors_do_better": str(payload.get("what_competitors_do_better") or fallback["what_competitors_do_better"]),
        "content_gaps": str(payload.get("content_gaps") or fallback["content_gaps"]),
        "best_time_to_post": str(payload.get("best_time_to_post") or fallback["best_time_to_post"]),
        "recommendations": payload.get("recommendations") if isinstance(payload.get("recommendations"), list) else fallback["recommendations"],
    }

    cleaned_recs = [str(item).strip() for item in normalized["recommendations"] if str(item).strip()]
    if len(cleaned_recs) < 3:
        cleaned_recs = fallback["recommendations"]
    normalized["recommendations"] = cleaned_recs[:3]

    return normalized


def build_summary():
    @retry_on_disconnect()
    def _build():
        client = get_supabase_client()
        user = client.table("users").select("id").eq("username", "my_brand").execute()
        if not user.data:
            return {
                "my_followers": 0,
                "my_engagement_rate": 0,
                "my_top_content": "N/A",
                "my_posts_per_week": 0,
                "avg_competitor_followers": 0,
                "avg_competitor_engagement": 0,
                "competitor_top_contents": [],
            }
        user_id = user.data[0]["id"]

        # My latest followers
        my_followers = client.table("follower_metrics") \
            .select("follower_count").eq("user_id", user_id) \
            .order("recorded_at", desc=True).limit(1).execute()
        my_follower_count = my_followers.data[0].get("follower_count", 0) if my_followers.data else 0

        # My engagement + top content
        my_posts = client.table("posts") \
            .select("likes, comments, shares, content_type") \
            .eq("user_id", user_id).execute()

        content_counts = defaultdict(int)
        total_engagement = 0
        for p in my_posts.data:
            likes = p.get("likes") or 0
            comments = p.get("comments") or 0
            shares = p.get("shares") or 0
            content_type = p.get("content_type") or "Unknown"
            total_engagement += likes + comments + shares
            content_counts[content_type] += 1

        avg_engagement = round(total_engagement / len(my_posts.data), 1) if my_posts.data else 0
        engagement_rate = round((avg_engagement / my_follower_count) * 100, 2) if my_follower_count else 0
        top_content = max(content_counts, key=content_counts.get) if content_counts else "N/A"
        posts_per_week = round(len(my_posts.data) / 13, 1)

        # Competitor averages
        competitors = client.table("competitors").select("id, username") \
            .eq("owner_id", user_id).execute()

        comp_data = []
        for comp in competitors.data:
            metrics = client.table("competitor_metrics") \
                .select("follower_count, avg_likes, avg_comments, avg_shares, top_content_type") \
                .eq("competitor_id", comp["id"]) \
                .order("recorded_at", desc=True).limit(1).execute()
            if metrics.data:
                m = metrics.data[0]
                follower_count = m.get("follower_count") or 0
                avg_likes = m.get("avg_likes") or 0
                avg_comments = m.get("avg_comments") or 0
                avg_shares = m.get("avg_shares") or 0
                comp_data.append({
                    "name": comp["username"],
                    "followers": follower_count,
                    "avg_engagement": avg_likes + avg_comments + avg_shares,
                    "top_content": m.get("top_content_type") or "Unknown"
                })

        avg_comp_followers = round(sum(c["followers"] for c in comp_data) / len(comp_data)) if comp_data else 0
        avg_comp_engagement = round(sum(c["avg_engagement"] for c in comp_data) / len(comp_data), 1) if comp_data else 0
        comp_top_contents = [c["top_content"] for c in comp_data]

        return {
            "my_followers": my_follower_count,
            "my_engagement_rate": engagement_rate,
            "my_top_content": top_content,
            "my_posts_per_week": posts_per_week,
            "avg_competitor_followers": avg_comp_followers,
            "avg_competitor_engagement": avg_comp_engagement,
            "competitor_top_contents": comp_top_contents
        }
    
    return _build()


@router.get("/")
@retry_on_disconnect()
def get_insights():
    summary = build_summary()
    try:
        gaps = get_gaps()
    except Exception:
        gaps = []

    baseline = _default_insights(summary, gaps)

    prompt = f"""
You are a senior growth analyst creating high-precision social media insights.

Your objective:
Produce insights that are strictly evidence-based from the provided dataset and useful for immediate weekly execution.

DATA (single source of truth):
{{
    "my_stats": {{
        "followers": {summary["my_followers"]},
        "engagement_rate_pct": {summary["my_engagement_rate"]},
        "top_content_type": {json.dumps(summary["my_top_content"])},
        "posts_per_week": {summary["my_posts_per_week"]}
    }},
    "competitor_averages": {{
        "avg_followers": {summary["avg_competitor_followers"]},
        "avg_engagement": {summary["avg_competitor_engagement"]},
        "top_content_types": {json.dumps(summary["competitor_top_contents"])}
    }},
    "top_content_gaps": {json.dumps(gaps[:3])}
}}

Reasoning requirements:
1) Compare my engagement_rate_pct to competitor avg_engagement and explicitly quantify the difference.
2) Explain what competitors do better using only provided values (cadence, content mix, engagement).
3) For content gaps, prioritize only the highest-impact gaps from top_content_gaps.
4) If any metric is missing/zero/insufficient, say "insufficient data" for that specific claim instead of guessing.

Writing requirements:
- Be specific and concrete; avoid generic advice.
- Keep each sentence tightly tied to numbers or named fields in DATA.
- Do not use external benchmarks, assumptions, or invented timing windows.
- best_time_to_post must be framed as a data-limitation-aware recommendation (e.g., suggest an experiment plan if timing data is absent).

Output format:
Return valid JSON only with exactly these keys:
{{
    "what_competitors_do_better": "2-3 precise sentences",
    "content_gaps": "2-3 precise sentences",
    "best_time_to_post": "1-2 specific sentences",
    "recommendations": [
        "short action 1",
        "short action 2",
        "short action 3"
    ]
}}

Final quality check before answering:
- Every claim must map to an explicit value in DATA.
- No fluff, no repetition, no invented facts.
- recommendations must be exactly 3 and each must be directly executable this week.
"""

    groq_client = _get_groq_client()
    if not groq_client:
        baseline["source"] = "rules"
        return baseline

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        llm_payload = json.loads(response.choices[0].message.content)
        merged = _normalize_insights(llm_payload, baseline)
        merged["source"] = "ai+rules"
        return merged
    except Exception:
        baseline["source"] = "rules"
        return baseline


@router.get("/workflows")
@retry_on_disconnect()
def get_workflows():
    """Return simple automation-style weekly action workflows."""
    try:
        summary = build_summary()
        gaps = get_gaps()
    except Exception:
        return [{
            "name": "Weekly strategy review",
            "trigger": "Every Monday morning (before planning posts)",
            "action": "Review previous week performance and schedule next week content in advance.",
        }]

    workflows = []

    if summary.get("my_posts_per_week", 0) < 4:
        workflows.append({
            "name": "Posting cadence booster",
            "trigger": "At the start of each week (your first planning block)",
            "action": "Queue at least 4 posts in your content calendar and schedule them across the week.",
        })

    if summary.get("my_engagement_rate", 0) < 3:
        workflows.append({
            "name": "Engagement lift sprint",
            "trigger": "Within 60 minutes after each post goes live",
            "action": "Run a 60-minute response window for comments and shares to increase early engagement.",
        })

    top_gaps = [gap for gap in gaps if gap.get("gap", 0) > 0][:2]
    for gap in top_gaps:
        workflows.append({
            "name": f"Close {gap.get('their_top_content', 'content')} gap",
            "trigger": "During your weekly content planning session",
            "action": (
                f"Add {gap.get('gap', 0)} more {gap.get('their_top_content', 'content')} posts "
                f"to compete with {gap.get('competitor', 'top competitor')}."
            ),
        })

    if not workflows:
        workflows.append({
            "name": "Maintain winning rhythm",
            "trigger": "Once per week (same day each week)",
            "action": "Keep your current posting strategy and review competitor changes every Monday.",
        })

    return workflows
