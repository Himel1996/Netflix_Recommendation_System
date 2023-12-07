from itertools import chain
import pandas as pd

def extract_top_movies_per_user(file_path):
    # Reads the DataFrame from the path in input
    df = pd.read_csv(file_path)

    # Grouping by user_id, title, and genres to count the number of clicks for each movie for each user
    user_movie_counts = df.groupby(['user_id', 'title', 'genres']).size().reset_index(name='click_count')

    # Sorting based on the number of clicks for each user
    user_movie_counts.sort_values(by=['user_id', 'click_count'], ascending=[True, False], inplace=True)

    result = pd.DataFrame()

    # Iterates over each user_id and chooses only the top 10 clicked movies
    for _, group in user_movie_counts.groupby('user_id'):
        result = pd.concat([result, group.head(10)])

    # Sorting the result based on user_id and the number of clicks is sorted by user_id and click_count in descending order
    result.sort_values(by=['user_id', 'click_count'], ascending=[True, False], inplace=True)

    return result


def minhash_signature(user_genres, num_hashes, genre_dict, num_total_genres):

    # Extracting user genres from the list in input (which contanins 1 string with all the genres) to create the shingle matrix
    user_genres = user_genres[0].strip().split(', ')

    # Creating the shingle matrix using the genre dictionary and the user genres
    shingle_matrix = [0]*num_total_genres
    for genre in user_genres:
        # Putting 1 only the positions of the preferred genres
        shingle_matrix[genre_dict.get(genre)] = 1

    # Now let's calculate the MinHash signature, first we initialize the MinHash signature with positive infinity values
    minhash_signature = [float('inf')] * num_hashes  
    # We Iterate over the rows of the shingle matrix and if the genre is present in the user's preferences we calculate and modify the hash function 
    for i in range(num_total_genres):
        if shingle_matrix[i] == 1:
            for j in range(num_hashes):
                # Vary the seed to obtain different hash values
                hash_value = our_hash_function(i + j)
                
                # Update the MinHash signature in position j by taking the minimum hash value
                minhash_signature[j] = min(minhash_signature[j], hash_value)

    return minhash_signature

# Hash function created not using already implemented hash functions, as requested
def our_hash_function(x):
    hash_value = 17  # Arbitrary initial value

    while x:
        digit = x % 10
        hash_value = (hash_value * 31) + digit  # Multiplication by an arbitrary prime and addition with the digit
        x //= 10  # Removing the last digit

    return hash_value


def lsh(minhash_signatures, num_bands, band_size):

    # Final resulting dictionary where to put all the other buckets
    buckets = {}

    for band in range(num_bands):
        band_start = band * band_size
        band_end = (band + 1) * band_size

        # Creating a single bucket where to put the users
        band_buckets = {}

        # Iterating over users and creating band specific hash buckets
        for user_id, signature in minhash_signatures.items():
            band_slice = signature[band_start:band_end]
            band_hash = hash(tuple(band_slice))

            # Checking if the hash bucket already exists, and appending it or creating it accordingly
            if band_hash in band_buckets:
                band_buckets[band_hash].append(user_id)
            else:
                band_buckets[band_hash] = [user_id]

        # Merging band specific buckets into global buckets
        for bucket, users_in_bucket in band_buckets.items():
            if bucket in buckets:
                buckets[bucket].extend(users_in_bucket)
            else:
                buckets[bucket] = users_in_bucket

    return buckets

# Simple function that uses the Jaccard similarity formula to two sets to calculate similarity score
def jaccard_similarity(set1, set2):
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    if union > 0:
        result = intersection / union
    else:
        0

    return result

# Function to find the top 2 most similar users
def find_nearest_neighbors(target_user, minhash_signatures, bands, rows_per_band):
    
    # Apply LSH to divide users in buckets
    similar_users = lsh(minhash_signatures, bands, rows_per_band)

    # Find the bucket in which the target user is present
    target_bucket = None
    for _, users_in_bucket in similar_users.items():
        if target_user in users_in_bucket:
            target_bucket = users_in_bucket
            break

    if target_bucket is None:
        print(f"User {target_user} not found in buckets.")
        return []

    # Calculate exact Jaccard similarity for users in the same bucket
    jaccard_similarities = {}
    for user_id in target_bucket:
        if user_id != target_user:
            set1 = set(minhash_signatures[target_user])
            set2 = set(minhash_signatures[user_id])
            similarity = jaccard_similarity(set1, set2)
            jaccard_similarities[user_id] = similarity

    # And find the top 2 users with the highest similarity
    nearest_neighbors = sorted(jaccard_similarities.items(), key=lambda x: x[1], reverse=True)[:2]

    # Lastly, extract only the user IDs without similarity scores
    nearest_neighbors = [user_id for user_id, _ in nearest_neighbors]

    return nearest_neighbors


def recommend_movies(most_similar_users, top_movies_per_user):

    common_movies = set()
    user_movies_dict = {}
    recommended_movies = []

    # Finding the clicked movies for each neighbor
    for neighbor_id in most_similar_users:
        user_movies = set(top_movies_per_user[top_movies_per_user['user_id'] == neighbor_id]['title'])
        user_movies_dict[neighbor_id] = user_movies

    print(user_movies_dict)

    # Finding first the common movies among the neighbors and adding them if present, given the first condition to add movies
    common_movies = set.intersection(*user_movies_dict.values())

    if common_movies:
        common_movies_df = top_movies_per_user[top_movies_per_user['title'].isin(common_movies)]
        recommended_movies = common_movies_df.groupby('title')['click_count'].sum().sort_values(ascending=False).head(5).index.tolist()

    # If there are no more common movies and the recommended movies are less than 5, recommend the most clicked movies by the most similar neighbor first
    if len(recommended_movies) < 5:
        
        most_similar_neighbor = most_similar_users[0]
        most_similar_neighbor_movies = top_movies_per_user[top_movies_per_user['user_id'] == most_similar_neighbor].sort_values(by='click_count', ascending=False)['title'].tolist()
        # Deleting movies already present in recommended_movies
        most_similar_neighbor_movies = [movie for movie in most_similar_neighbor_movies if movie not in recommended_movies]
        remaining_recommendations = most_similar_neighbor_movies[:5 - len(recommended_movies)]
        recommended_movies += remaining_recommendations

        # If there are still less than 5 recommendations, add movies from the second neighbor based on clicks
        if len(recommended_movies) < 5:
            second_neighbor = most_similar_users[1]
            second_neighbor_movies = top_movies_per_user[top_movies_per_user['user_id'] == second_neighbor].sort_values(by='click_count', ascending=False)['title'].tolist()
            # Deleting movies already present in recommended_movies
            second_neighbor_movies = [movie for movie in second_neighbor_movies if movie not in recommended_movies]    
            remaining_recommendations = second_neighbor_movies[:5 - len(recommended_movies)]
            recommended_movies += remaining_recommendations



    return recommended_movies