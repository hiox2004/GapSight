from fastapi import APIRouter
from app.database import supabase, retry_on_disconnect
from collections import defaultdict
import os
from groq import Groq
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter(prefix="/insights", tags=["insights"])
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_summary():
    @retry_on_disconnect()
    def _build():
        user = supabase.table("users").select("id").eq("username", "my_brand").execute()
        user_id = user.data[0]["id"]

        # My latest followers
        my_followers = supabase.table("follower_metrics") \
            .select("follower_count").eq("user_id", user_id) \
            .order("recorded_at", desc=True).limit(1).execute()
        my_follower_count = my_followers.data[0]["follower_count"]

        # My engagement + top content
        my_posts = supabase.table("posts") \
            .select("likes, comments, shares, content_type") \
            .eq("user_id", user_id).execute()

        content_counts = defaultdict(int)
        total_engagement = 0
        for p in my_posts.data:
            total_engagement += p["likes"] + p["comments"] + p["shares"]
            content_counts[p["content_type"]] += 1

        avg_engagement = round(total_engagement / len(my_posts.data), 1) if my_posts.data else 0
        engagement_rate = round((avg_engagement / my_follower_count) * 100, 2)
        top_content = max(content_counts, key=content_counts.get) if content_counts else "N/A"
        posts_per_week = round(len(my_posts.data) / 13, 1)

        # Competitor averages
        competitors = supabase.table("competitors").select("id, username") \
            .eq("owner_id", user_id).execute()

        comp_data = []
        for comp in competitors.data:
            metrics = supabase.table("competitor_metrics") \
                .select("follower_count, avg_likes, avg_comments, avg_shares, top_content_type") \
                .eq("competitor_id", comp["id"]) \
                .order("recorded_at", desc=True).limit(1).execute()
            if metrics.data:
                m = metrics.data[0]
                comp_data.append({
                    "name": comp["username"],
                    "followers": m["follower_count"],
                    "avg_engagement": m["avg_likes"] + m["avg_comments"] + m["avg_shares"],
                    "top_content": m["top_content_type"]
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

    prompt = f"""
You are an expert social media analyst. Analyze this data and return actionable insights.

MY STATS:
- Followers: {summary["my_followers"]}
- Engagement rate: {summary["my_engagement_rate"]}%
- Top content type: {summary["my_top_content"]}
- Posts per week: {summary["my_posts_per_week"]}

COMPETITOR AVERAGES:
- Avg followers: {summary["avg_competitor_followers"]}
- Avg engagement: {summary["avg_competitor_engagement"]}
- Their top content types: {", ".join(summary["competitor_top_contents"])}

Return a JSON object with exactly these keys:
- "what_competitors_do_better": a string with 2-3 sentences
- "content_gaps": a string with 2-3 sentences  
- "best_time_to_post": a string with a specific recommendation
- "recommendations": an array of exactly 3 short actionable strings
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
