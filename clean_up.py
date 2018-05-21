import csv
import sys
import copy
from scipy import log, cosh, tanh, exp, floor
from scipy.optimize import fsolve
import datetime as dt

games_list = []

if len(sys.argv) >1:
	raw_file = str(sys.argv[1])
	normal_date = bool(sys.argv[2])
else:
	raw_file = "march.csv"

with open(raw_file, 'rU') as csvfile:
	games_reader = csv.reader(csvfile, dialect='excel')
	for game in games_reader:
		if game[0]!='':
			raw_date = game[0]
			raw_split = raw_date.split("/")
			
			# Need to account for normal or US date format
			if normal_date:
				day = raw_split[0]
				if len(day)!= 2:
					day = "0" + day
				month = raw_split[1]
				if len(month) != 2:
					month = "0" + month
				year = raw_split[2]
				if len(year) != 4:
					year = "20" + year
			else:
				day = raw_split[1]
				if len(day)!= 2:
					day = "0" + day
				month = raw_split[0]
				if len(month) != 2:
					month = "0" + month
				year = raw_split[2]
				if len(year) != 4:
					year = "20" + year

			clean_date = year + month + day
			game_data = [clean_date, game[2],game[3],game[4],game[5]]
			print game_data
			games_list.append(game_data)

clean_game_list = []

for game in games_list:
	swapped = [game[0], game[3],game[4], game[1],game[2]]
	if game not in clean_game_list and swapped not in clean_game_list:
		clean_game_list.append(game)


clean_file = 'clean_' + raw_file
with open(clean_file, 'wb') as csvfile:
	game_writer = csv.writer(csvfile, delimiter=',')
	for game in clean_game_list:
		game_writer.writerow(game)