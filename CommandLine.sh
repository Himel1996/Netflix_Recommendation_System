#!/bin/bash

# Create a temporary database
sqlite3 netflix.db <<EOF
.mode csv
.import vodclickstream_uk_movies_03.csv clicks
EOF

## TOP-10 most watched films
# sqlite3 netlix.db 'SELECT title, COUNT(*) as num_views FROM clicks WHERE CAST(duration as INT) > 0 GROUP BY movie_id ORDER BY num_views DESC LIMIT 10'

## Most watched film
most_watched_film=$(sqlite3 netflix.db 'SELECT title FROM (SELECT title, COUNT(*) as num_views FROM clicks WHERE CAST(duration as INT) > 0 GROUP BY movie_id ORDER BY num_views DESC LIMIT 1)')
echo "The most watched film on Netlix is:   \"$most_watched_film\""

#------------------------------------------------------------

# Add a column 'datetime_int' to the table
sqlite3 netflix.db 'ALTER TABLE clicks ADD COLUMN datetime_int INT;'
# Convert datetime string to seconds and store it in the datetime_int column
sqlite3 netflix.db "UPDATE clicks SET datetime_int = CAST(strftime('%s', datetime) AS INT);"

# Create a new table (with only user_id and datetime_int) ordered by datetime_int in ascending order, since we want clicks to be subsequent
# We also create a column that contains the previous datetime_int, so that we can then evaluate easily the difference between subsequent clicks
sqlite3 netflix.db 'CREATE TABLE clicks_ordered AS SELECT user_id, datetime_int FROM clicks ORDER BY datetime_int ASC;' 
sqlite3 netflix.db 'ALTER TABLE clicks_ordered ADD COLUMN previous_datetime_int INT;'
sqlite3 netflix.db 'UPDATE clicks_ordered SET previous_datetime_int = datetime_int;' 
sqlite3 netflix.db 'UPDATE clicks_ordered SET previous_datetime_int = (SELECT datetime_int FROM clicks_ordered AS c WHERE c.rowid = clicks_ordered.rowid - 1);'

# Delete first row that has previous_datetime_int empty
sqlite3 netflix.db 'DELETE FROM clicks_ordered WHERE rowid = (SELECT MIN(rowid) FROM clicks_ordered);'

# Add a column to store the differences  
sqlite3 netflix.db 'ALTER TABLE clicks_ordered ADD COLUMN difference INT;' 
sqlite3 netflix.db 'UPDATE clicks_ordered SET difference = datetime_int - previous_datetime_int;'

# Evaluate the subsequent clicks average
average_time=$(sqlite3 netflix.db 'SELECT AVG(difference) FROM clicks_ordered')
echo "The average time between subsequent clicks on Netflix is:   $average_time s"



#------------------------------------------------------------

## TOP-10 users by time spent on Netlix
# sqlite3 netlix.db 'SELECT user_id, SUM(duration) as total_time FROM clicks GROUP BY user_id ORDER BY total_time DESC LIMIT 10'

# User-ID of the user that has spent the most time on Netflix
user_ID=$(sqlite3 netflix.db 'SELECT user_id FROM (SELECT user_id, SUM(duration) as total_time FROM clicks GROUP BY user_id ORDER BY total_time DESC LIMIT 1)')
echo "The ID of the user that has spent the most time on Netflix is:   $user_ID"

rm netflix.db

