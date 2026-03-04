from fastapi import APIRouter, BackgroundTasks
from datetime import datetime, timezone, timedelta
import httpx
import os
import time
import logging

from app.database import get_supabase_client, retry_on_disconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

RAPIDAPI_HOST = "instagram-scraper-stable-api.p.rapidapi.com"
RAPIDAPI_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST,
}

MEDIA_TYPE_MAP = {
    1: "Post",
    2: "Reel",
    8: "Carousel",
}


# ---------------------------------------------------------------------------
# Background task: Apify historical follower data (first sync only)
# ---------------------------------------------------------------------------

def run_apify_historical(user_id: str, username: str):
    supabase = get_supabase_client()

    try:
        run_url = f"https://api.apify.com/v2/acts/radeance~socialblade-api/runs?token={APIFY_API_TOKEN}"
        payload = {
            "creators": [username],
            "platform": "instagram",
            "proxySettings": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "US"
            }
        }

        logger.info(f"[Apify] Starting historical fetch for {username}")
        with httpx.Client(timeout=30) as client:
            run_resp = client.post(run_url, json=payload)
            run_resp.raise_for_status()
            run_id = run_resp.json()["data"]["id"]
        logger.info(f"[Apify] Run started: {run_id}")

        # Poll until finished (max 5 minutes)
        status_resp = None
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_API_TOKEN}"
        for attempt in range(60):
            time.sleep(5)
            with httpx.Client(timeout=15) as client:
                status_resp = client.get(status_url)
                status_resp.raise_for_status()
                status = status_resp.json()["data"]["status"]
            logger.info(f"[Apify] Poll {attempt+1}/60 — status: {status}")
            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.error(f"[Apify] Run ended with status: {status}")
                return
        else:
            logger.error("[Apify] Polling timed out after 5 minutes")
            return

        # Fetch dataset items
        dataset_id = status_resp.json()["data"]["defaultDatasetId"]
        dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_API_TOKEN}"
        with httpx.Client(timeout=30) as client:
            data_resp = client.get(dataset_url)
            data_resp.raise_for_status()
            items = data_resp.json()
        logger.info(f"[Apify] Fetched {len(items)} items for {username}")
        if items:
            logger.info(f"[Apify] Sample item keys: {list(items[0].keys())}")

        # The actor returns one item per creator.
        # Daily history is nested in daily_growth: [{date, subscribers}, ...]
        rows = []
        for item in items:
            daily = item.get("daily_growth") or []
            if not daily:
                logger.warning(f"[Apify] No daily_growth in item for {username}")
                logger.info(f"[Apify] Item keys available: {list(item.keys())}")
                continue
            logger.info(f"[Apify] Found {len(daily)} daily_growth entries for {username}")
            if daily:
                logger.info(f"[Apify] Sample daily entry: {daily[0]}")
            for entry in daily:
                date_str = entry.get("date") or entry.get("day") or entry.get("Date")
                followers = (
                    entry.get("subscribers") or entry.get("followers")
                    or entry.get("followerCount") or entry.get("followed_by")
                )
                if not date_str or followers is None:
                    continue
                date_str = str(date_str)[:10]
                rows.append({"user_id": user_id, "follower_count": int(followers), "recorded_at": date_str})

        if not rows:
            logger.warning(f"[Apify] No usable rows parsed for {username}")
            return

        # Fetch which dates already exist so we don't duplicate
        existing = supabase.table("follower_metrics") \
            .select("recorded_at") \
            .eq("user_id", user_id).execute()
        existing_dates = {r["recorded_at"][:10] for r in (existing.data or [])}

        new_rows = [r for r in rows if r["recorded_at"] not in existing_dates]
        logger.info(f"[Apify] Inserting {len(new_rows)} new rows ({len(rows) - len(new_rows)} already exist)")

        if new_rows:
            supabase.table("follower_metrics").insert(new_rows).execute()
            logger.info(f"[Apify] Done — inserted {len(new_rows)} rows for {username}")

    except Exception as e:
        logger.error(f"[Apify] Failed for {username}: {e}")


# ---------------------------------------------------------------------------
# Main sync endpoint
# ---------------------------------------------------------------------------

FAKE_PROFILE = {
    "follower_count": 99999,
    "pk": "000000000",
}
FAKE_POSTS = [
    {"pk": "111111111111111111", "media_type": 1, "taken_at": 1740000000, "like_count": 500, "comment_count": 42},
    {"pk": "222222222222222222", "media_type": 2, "taken_at": 1740100000, "like_count": 1200, "comment_count": 88},
    {"pk": "333333333333333333", "media_type": 8, "taken_at": 1740200000, "like_count": 300, "comment_count": 15},
]


@router.post("/{username}")
@retry_on_disconnect()
def sync_user(username: str, background_tasks: BackgroundTasks, dry_run: bool = False, fetch_history: bool = False):
    supabase = get_supabase_client()

    # -----------------------------------------------------------------------
    # STEP 1 — Find or create user
    # -----------------------------------------------------------------------
    user_resp = (
        supabase.table("users")
        .select("id, instagram_id, last_synced_at")
        .eq("username", username)
        .execute()
    )
    user = user_resp.data[0] if user_resp.data else None

    if not user:
        insert_resp = (
            supabase.table("users")
            .insert({"username": username, "platform": "Instagram"})
            .execute()
        )
        user = insert_resp.data[0]

    user_id = user["id"]
    is_first_sync = user.get("last_synced_at") is None

    # -----------------------------------------------------------------------
    # fetch_history=True — skip RapidAPI entirely, only run Apify for user + all competitors
    # -----------------------------------------------------------------------
    if fetch_history:
        background_tasks.add_task(run_apify_historical, user_id, username)
        return {
            "status": "success",
            "username": username,
            "apify_historical": "running in background",
        }

    # -----------------------------------------------------------------------
    # STEP 2 — RapidAPI: User About (follower count + instagram_id)
    # -----------------------------------------------------------------------
    if dry_run:
        about_data = FAKE_PROFILE
    else:
        try:
            with httpx.Client(timeout=20) as client:
                about_resp = client.get(
                    "https://instagram-scraper-stable-api.p.rapidapi.com/ig_get_fb_profile_hover.php",
                    headers=RAPIDAPI_HEADERS,
                    params={"username_or_url": username},
                )
                about_resp.raise_for_status()
            about_data = about_resp.json().get("user_data", {})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return {"status": "rate_limited", "username": username, "note": "RapidAPI rate limit hit — follower data not updated, try again later"}
            raise

    follower_count = about_data.get("follower_count", 0)
    instagram_id = str(about_data.get("pk", ""))

    # Save instagram_id to users table if not already stored
    if instagram_id and not user.get("instagram_id"):
        supabase.table("users").update({"instagram_id": instagram_id}).eq("id", user_id).execute()

    # Insert current follower snapshot
    supabase.table("follower_metrics").insert({
        "user_id": user_id,
        "follower_count": follower_count,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    # -----------------------------------------------------------------------
    # STEP 3 — RapidAPI: User Posts
    # -----------------------------------------------------------------------
    if dry_run:
        items = FAKE_POSTS
    else:
        try:
            with httpx.Client(timeout=20) as client:
                posts_resp = client.post(
                    "https://instagram-scraper-stable-api.p.rapidapi.com/get_ig_user_posts.php",
                    headers={**RAPIDAPI_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
                    data={"username_or_url": username},
                )
                posts_resp.raise_for_status()
            items = posts_resp.json().get("posts", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return {"status": "rate_limited", "username": username, "note": "RapidAPI rate limit hit — posts not updated, try again later"}
            raise

    upserted = 0
    for item in items:
        # Posts can be nested under "node" or flat
        node = item.get("node", item)

        # Use pk as platform_post_id
        platform_post_id = str(node.get("pk", ""))
        if not platform_post_id:
            continue

        media_type = node.get("media_type", 1)
        content_type = MEDIA_TYPE_MAP.get(media_type, "Post")

        taken_at = node.get("taken_at")
        posted_at = (
            datetime.fromtimestamp(taken_at, tz=timezone.utc).isoformat()
            if taken_at
            else datetime.now(timezone.utc).isoformat()
        )

        row = {
            "user_id": user_id,
            "platform_post_id": platform_post_id,
            "likes": node.get("like_count", 0),
            "comments": node.get("comment_count", 0),
            "shares": 0,
            "content_type": content_type,
            "posted_at": posted_at,
        }

        supabase.table("posts").upsert(
            row, on_conflict="platform_post_id"
        ).execute()
        upserted += 1

    # -----------------------------------------------------------------------
    # STEP 4 — Update last_synced_at
    # -----------------------------------------------------------------------
    supabase.table("users").update({
        "last_synced_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", user_id).execute()

    # -----------------------------------------------------------------------
    # STEP 5 — Kick off Apify historical data if first sync OR forced
    # -----------------------------------------------------------------------
    should_fetch_history = is_first_sync or fetch_history
    if should_fetch_history:
        background_tasks.add_task(run_apify_historical, user_id, username)

    return {
        "status": "success",
        "username": username,
        "follower_count": follower_count,
        "posts_upserted": upserted,
        "apify_historical": "running in background" if should_fetch_history else "skipped",
    }
