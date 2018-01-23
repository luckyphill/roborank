# roborank
MRDA Roborank
These python scripts contain a couple of versions of a rankings calculator I've been working on to rank teams in the MRDA.
Of the three approaches, my preferred is found in regression.py. It uses the DOS (Difference over sum) as a way to "score" a game result, which tells you the winning margin as a fraction of the total points in a game. It then uses a least squares regression to choose a power rating for each team that best explains their results throughout a season with. More precisely it tries to fit the game results to a  Logistic CDF type curve. 
