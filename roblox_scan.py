import requests
import json
import time
import re

# Define the range of User IDs to scan
START_USER_ID = 610683544
END_USER_ID = 8065019393
BATCH_SIZE = 100  # Number of users per request

# Updated list of flagged words
bad_words = [
    "predator", "adult", "grooming", "inappropriate", "danger", "meet me", "private", 
    "cum", "sl0t", "fun", "rp", "studio rp", "geooan", "goon", "g00n", "go0n", "g0on", 
    "age", "13", "13yr", "furry", "fur", "inch", "tip", "slave", "master", "slut", 
    "mommy", "mummy", "mum", "dad", "daddy", "1yr", "2yr", "3yr", "4yr", "5yr", "bull", 
    "15yr", "yr", "czmdump", "czm"
]

# Output file for suspicious users
OUTPUT_FILE = "suspicious_users.json"
# File containing known suspicious profile URLs
SUSPICIOUS_PROFILES_FILE = "suspicious_profiles.txt"

# Function to extract user ID from Roblox profile URL
def extract_user_id_from_url(url):
    # Match patterns like https://www.roblox.com/users/123456789/profile or just 123456789
    patterns = [
        r'roblox\.com/users/(\d+)',  # Standard profile URL
        r'roblox\.com/profile/(\d+)',  # Alternative profile URL
        r'^(\d+)$'  # Just a numeric ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# Load known suspicious profiles from file
def load_suspicious_profiles():
    profiles = []
    try:
        with open(SUSPICIOUS_PROFILES_FILE, "r") as file:
            for line in file:
                url = line.strip()
                if url:
                    user_id = extract_user_id_from_url(url)
                    if user_id:
                        profiles.append({
                            "url": url,
                            "user_id": user_id
                        })
        print(f"📋 Loaded {len(profiles)} suspicious profiles")
        return profiles
    except FileNotFoundError:
        print(f"⚠️ Warning: {SUSPICIOUS_PROFILES_FILE} not found. Creating empty file.")
        with open(SUSPICIOUS_PROFILES_FILE, "w") as file:
            pass
        return []
    except Exception as e:
        print(f"❌ Error loading suspicious profiles: {e}")
        return []

# Function to get user info from Roblox API with error handling
def get_user_info(user_ids):
    url = "https://users.roblox.com/v1/users"
    params = {"userIds": user_ids}

    while True:  # Retry if rate-limited
        response = requests.post(url, json=params)

        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:  # Rate limit error
            print("⚠️ Rate limited! Waiting 30 seconds before retrying...")
            time.sleep(30)  # Wait longer to avoid getting blocked
        else:
            print(f"❌ Error fetching user info: {response.status_code}")
            return []

# Function to get a user's friends
def get_user_friends(user_id):
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
    
    while True:  # Retry if rate-limited
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:  # Rate limit error
            print("⚠️ Rate limited! Waiting 30 seconds before retrying...")
            time.sleep(30)
        elif response.status_code == 404:
            print(f"⚠️ User {user_id} not found or friends list is private")
            return []
        else:
            print(f"❌ Error fetching friends for user {user_id}: {response.status_code}")
            return []

# Load known suspicious profiles
suspicious_profiles = load_suspicious_profiles()
suspicious_ids = [profile["user_id"] for profile in suspicious_profiles]

# Load previous results if they exist
try:
    with open(OUTPUT_FILE, "r") as file:
        suspicious_users = json.load(file)
    print(f"📂 Loaded {len(suspicious_users)} previously flagged users")
except (FileNotFoundError, json.JSONDecodeError):
    suspicious_users = []
    print("📂 No previous results found, starting fresh")

# Start scanning users in batches
for user_id in range(START_USER_ID, END_USER_ID, BATCH_SIZE):
    batch_ids = list(range(user_id, min(user_id + BATCH_SIZE, END_USER_ID)))
    print(f"🔍 Scanning User IDs: {batch_ids[0]} to {batch_ids[-1]}")

    user_data = get_user_info(batch_ids)

    for user in user_data:
        user_id = user.get("id", "Unknown")
        username = user.get("name", "Unknown")
        description = user.get("description", "").lower()
        
        flagged = False
        flag_reasons = []
        suspicious_friends = []

        # Check for flagged words in user descriptions
        word_flags = [word for word in bad_words if word in description]
        if word_flags:
            flagged = True
            flag_reasons.append(f"Flagged words: {', '.join(word_flags)}")

        # Check friends list against known suspicious profiles
        print(f"👥 Checking friends for user: {username} (ID: {user_id})")
        friends = get_user_friends(user_id)
        
        for friend in friends:
            friend_id = str(friend.get("id"))
            if friend_id in suspicious_ids:
                flagged = True
                # Find the corresponding profile URL
                for profile in suspicious_profiles:
                    if profile["user_id"] == friend_id:
                        friend_url = profile["url"]
                        break
                else:
                    friend_url = f"https://www.roblox.com/users/{friend_id}/profile"
                
                suspicious_friends.append({
                    "id": friend_id,
                    "name": friend.get("name", "Unknown"),
                    "profile_url": friend_url
                })
        
        if suspicious_friends:
            flag_reasons.append(f"Connected to {len(suspicious_friends)} known suspicious users")

        # Save if flagged for any reason
        if flagged:
            print(f"⚠️ Flagged User: {username} (ID: {user_id})")
            for reason in flag_reasons:
                print(f"   - {reason}")
                
            # Create profile URL for the flagged user
            user_profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            
            user_data = {
                "user_id": user_id,
                "username": username,
                "profile_url": user_profile_url,
                "flagged_words": word_flags,
                "suspicious_friends": suspicious_friends
            }
            
            # Check if user is already in the list
            user_exists = False
            for i, existing_user in enumerate(suspicious_users):
                if str(existing_user.get("user_id")) == str(user_id):
                    suspicious_users[i] = user_data  # Update existing entry
                    user_exists = True
                    break
            
            if not user_exists:
                suspicious_users.append(user_data)

        # Add a small delay between friend checks to avoid rate limiting
        time.sleep(0.5)

    # Save results after each batch
    try:
        with open(OUTPUT_FILE, "w") as file:
            json.dump(suspicious_users, file, indent=2)
        print(f"✅ {len(suspicious_users)} suspicious users saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

print(f"✅ Scanning complete! Total flagged users: {len(suspicious_users)}")
print(f"📂 Open {OUTPUT_FILE} to see the results.")
