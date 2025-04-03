import requests
import json
import time
import re
import os

# Define the range of User IDs to scan
START_USER_ID = 6246497384
END_USER_ID = 6246597384  # Reduced range for testing
BATCH_SIZE = 100  # Number of users per request

# Updated list of flagged words
bad_words = [
    "predator", "adult", "grooming", "inappropriate", "danger", "meet me", "private", 
    "cum", "sl0t", "fun", "rp", "studio rp", "geooan", "goon", "g00n", "go0n", "g0on", 
    "age", "13", "13yr", "furry", "fur", "inch", "tip", "slave", "master", "slut", 
    "mommy", "mummy", "mum", "dad", "daddy", "1yr", "2yr", "3yr", "4yr", "5yr", "bull", 
    "15yr", "yr", "czmdump", "czm"
]

OUTPUT_FILE = "suspicious_users.json"
SUSPICIOUS_PROFILES_FILE = "suspicious_profiles.txt"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total: 
        print()

def extract_user_id_from_url(url):
    match = re.search(r'roblox\.com/users/(\d+)', url)
    if match:
        return match.group(1)
    return None

def load_suspicious_profiles():
    profiles = []
    try:
        with open(SUSPICIOUS_PROFILES_FILE, "r") as file:
            for line in file:
                url = line.strip()
                url = re.sub(r' - \d+$', '', url)  # Remove " - X" suffix
                user_id = extract_user_id_from_url(url)
                if user_id:
                    profiles.append({"url": url, "user_id": user_id})
        return profiles
    except FileNotFoundError:
        with open(SUSPICIOUS_PROFILES_FILE, "w") as file:
            pass
        return []

def get_user_info(user_ids):
    url = "https://users.roblox.com/v1/users"
    params = {"userIds": user_ids}
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        try:
            response = requests.post(url, json=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", [])
            elif response.status_code == 429:
                print("\nRate limited! Waiting 15 seconds...")
                time.sleep(15)
                attempts += 1
            else:
                print(f"\nError getting user info: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"\nRequest error: {e}")
            time.sleep(5)
            attempts += 1
    
    return []

def get_user_friends(user_id):
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get("data", [])
            elif response.status_code == 429:
                print("\nRate limited! Waiting 30 seconds...")
                time.sleep(30)
                attempts += 1
            elif response.status_code == 404:
                return []
            else:
                return []
        except requests.exceptions.RequestException:
            time.sleep(5)
            attempts += 1
    
    return []

def main():
    print("=== Roblox User Scanner ===")
    print(f"Scanning user IDs from {START_USER_ID} to {END_USER_ID}")
    print(f"Looking for {len(bad_words)} flagged words")
    print("Press Ctrl+C to stop scanning at any time\n")
    
    suspicious_profiles = load_suspicious_profiles()
    suspicious_ids = [profile["user_id"] for profile in suspicious_profiles]
    
    try:
        with open(OUTPUT_FILE, "r") as file:
            suspicious_users = json.load(file)
            print(f"Loaded {len(suspicious_users)} previously flagged users")
    except (FileNotFoundError, json.JSONDecodeError):
        suspicious_users = []
        print("Starting new scan")
    
    total_batches = (END_USER_ID - START_USER_ID) // BATCH_SIZE
    processed_batches = 0
    total_flagged = len(suspicious_users)
    new_flagged = 0
    
    try:
        for user_id in range(START_USER_ID, END_USER_ID, BATCH_SIZE):
            processed_batches += 1
            batch_ids = list(range(user_id, min(user_id + BATCH_SIZE, END_USER_ID)))
            
            clear_screen()
            print("=== Roblox User Scanner ===")
            print_progress_bar(processed_batches, total_batches, prefix='Progress:', 
                              suffix=f'Batch {processed_batches}/{total_batches}', length=50)
            print(f"\nCurrent range: {batch_ids[0]} - {batch_ids[-1]}")
            print(f"Total flagged users: {total_flagged} ({new_flagged} new)")
            print("\nLast 5 flagged users:")
            
            for i in range(min(5, len(suspicious_users))):
                user = suspicious_users[-(i+1)]
                print(f"- {user['username']} (ID: {user['user_id']}): {', '.join(user.get('flagged_words', []))}")
            
            print("\nRequesting user data...")
            user_data = get_user_info(batch_ids)
            print(f"Processing {len(user_data)} users...")
            
            for user in user_data:
                user_id = user.get("id", "Unknown")
                username = user.get("name", "Unknown")
                description = user.get("description", "").lower()
                flagged = False
                flag_reasons = []
                suspicious_friends = []
                
                word_flags = [word for word in bad_words if word in description]
                if word_flags:
                    flagged = True
                    flag_reasons.append(f"Flagged words: {', '.join(word_flags)}")
                
                print(f"\nChecking {username} (ID: {user_id})...")
                friends = get_user_friends(user_id)
                if friends:
                    print(f"Found {len(friends)} friends...")
                
                for friend in friends:
                    friend_id = str(friend.get("id"))
                    if friend_id in suspicious_ids:
                        flagged = True
                        for profile in suspicious_profiles:
                            if profile["user_id"] == friend_id:
                                friend_url = profile["url"]
                                break
                        else:
                            friend_url = f"https://www.roblox.com/users/{friend_id}/profile"
                        suspicious_friends.append({"id": friend_id, "name": friend.get("name", "Unknown"), "profile_url": friend_url})
                
                if suspicious_friends:
                    flag_reasons.append(f"Connected to {len(suspicious_friends)} known suspicious users")
                
                if flagged:
                    user_profile_url = f"https://www.roblox.com/users/{user_id}/profile"
                    user_data = {
                        "user_id": user_id,
                        "username": username,
                        "profile_url": user_profile_url,
                        "flagged_words": word_flags,
                        "suspicious_friends": suspicious_friends
                    }
                    
                    if not any(str(existing_user.get("user_id")) == str(user_id) for existing_user in suspicious_users):
                        suspicious_users.append(user_data)
                        total_flagged += 1
                        new_flagged += 1
                        print(f"\n⚠️ FLAGGED USER: {username}")
                        print(f"Reason: {' | '.join(flag_reasons)}")
                
                # Short delay to avoid API rate limiting
                time.sleep(0.1)
            
            # Save progress after each batch
            with open(OUTPUT_FILE, "w") as file:
                json.dump(suspicious_users, file, indent=2)
    
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user!")
    
    finally:
        # Final save
        with open(OUTPUT_FILE, "w") as file:
            json.dump(suspicious_users, file, indent=2)
        
        print("\n=== Scan Summary ===")
        print(f"Processed {processed_batches} of {total_batches} batches")
        print(f"Total flagged users: {total_flagged}")
        print(f"New flagged users: {new_flagged}")
        print(f"Results saved to {OUTPUT_FILE}")
        print("\nPress Enter to exit...")
        input()

if __name__ == "__main__":
    main()
