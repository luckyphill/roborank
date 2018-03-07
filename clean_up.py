import csv
import sys
import copy
from scipy import log, cosh, tanh, exp, floor
from scipy.optimize import fsolve
import datetime as dt

games_list = []

with open("march.csv", 'rU') as csvfile:
	games_reader = csv.reader(csvfile, dialect='excel')
	for game in games_reader:
		if game[0]!='':
			raw_date = game[0]
			raw_split = raw_date.split("/")
			day = raw_split[1]
			if len(day)!= 2:
				day = "0" + raw_split[1]
			month = raw_split[0]
			if len(month) != 2:
				month = "0" + raw_split[0]
			year = raw_split[2]
			if len(year) != 4:
				year = "20" + raw_split[2]
			clean_date = year + month + day
			game_data = [clean_date, game[2],game[3],game[4],game[5]]
			print game_data
			games_list.append(game_data)

clean_game_list = []

for game in games_list:
	swapped = [game[0], game[3],game[4], game[1],game[2]]
	if game not in clean_game_list and swapped not in clean_game_list:
		clean_game_list.append(game)


with open('march_clean.csv', 'wb') as csvfile:
	game_writer = csv.writer(csvfile, delimiter=',')
	for game in clean_game_list:
		game_writer.writerow(game)