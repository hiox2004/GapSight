import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faker import Faker
from datetime import datetime, timedelta
import random
from app.database import supabase

fake = Faker()

CONTENT_TYPES = ["Reel", "Post", "Carousel", "Story"]
PLATFORMS = ["Instagram"]

def seed():
    print("Seeding database...")

    # Create main user
    user = supabase.table("users").insert({
        "username": "my_brand",
        "platform": "Instagram"
    }).execute()
    user_id = user.data[0]["id"]
    print(f"Created user: {user_id}")

    # Generate 90 days of follower metrics
    base_followers = 20000
    for i in range(90):
        date = datetime.now() - timedelta(days=90 - i)
        base_followers += random.randint(50, 300)
        supabase.table("follower_metrics").insert({
            "user_id": user_id,
            "follower_count": base_followers,
            "recorded_at": date.isoformat()
        }).execute()

    print("Follower metrics seeded")

    # Generate 90 days of posts
    for i in range(90):
        date = datetime.now() - timedelta(days=90 - i)
        num_posts = random.randint(0, 3)
        for _ in range(num_posts):
            content_type = random.choice(CONTENT_TYPES)
            multiplier = 1.5 if content_type == "Reel" else 1.0
            supabase.table("posts").insert({
                "user_id": user_id,
                "content_type": content_type,
                "likes": int(random.randint(200, 1500) * multiplier),
                "comments": int(random.randint(10, 200) * multiplier),
                "shares": int(random.randint(5, 100) * multiplier),
                "posted_at": date.isoformat()
            }).execute()

    print("Posts seeded")

    # Create 3 competitors
    competitor_names = ["brand_alpha", "brand_beta", "brand_gamma"]
    for name in competitor_names:
        comp = supabase.table("competitors").insert({
            "owner_id": user_id,
            "username": name,
            "platform": "Instagram"
        }).execute()
        comp_id = comp.data[0]["id"]

        base_comp_followers = random.randint(18000, 35000)
        for i in range(90):
            date = datetime.now() - timedelta(days=90 - i)
            base_comp_followers += random.randint(30, 400)
            supabase.table("competitor_metrics").insert({
                "competitor_id": comp_id,
                "follower_count": base_comp_followers,
                "avg_likes": random.randint(150, 2000),
                "avg_comments": random.randint(10, 300),
                "avg_shares": random.randint(5, 150),
                "top_content_type": random.choice(CONTENT_TYPES),
                "recorded_at": date.isoformat()
            }).execute()

    print("Competitors seeded")
    print("Done...")

if __name__ == "__main__":
    seed()
