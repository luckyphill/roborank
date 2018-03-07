import csv
import sys
import copy
from scipy import log, cosh, tanh, exp, floor
from scipy.optimize import fsolve
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
#from future import print_function

day = dt.timedelta(1)

def str2dt(date_as_string):
	#expects date in the form YYYYMMDD
	#returns a datetime object
	date_as_int = int(date_as_string)
	year = date_as_int//10000
	month = (date_as_int - year*10000)//100
	day = date_as_int - year*10000 - month*100

	return dt.date(year, month, day)

def weight(game_date,window_start, window_end):
	#now contained within the Game object
	diff = window_end - game_date
	months_ago = floor(12*diff.days/365)

	#return (12-months_ago)/12 #linearly decay, month by month
	#games within las 6 months are weighted 1, linear decay between 6 and 12 months, after 12 months weight is zero
	if months_ago<6:
		return 1
	elif 6<=months_ago<=12:
		return float(12 - months_ago)/6
	else:
		return 0

class Team:
	def __init__(self, name):
		self.name = name
		self.power = None
		self.num_games = 0
		self.num_wins = 0
		self.is_new = False # a team will be considered new if it did not play last season
		self.min_games_required = 5
		self.min_unique_opponents = 3
		self.opponents = [] # a list of the teams they have played to track min requirements
		self.is_connected = False
		self.data_for_initial_power = []
		self.hiatus = False
		self.disbanded = False
		self.games = []

	def increment_games(self):
		self.num_games += 1

	def increment_wins(self):
		self.num_wins +=1

	def is_active(self):
		#checks if minimum activity requirements have been met
		if (self.num_games >= self.min_games_required) and (len(self.opponents) >= self.min_unique_opponents):
			return True
		else:
			return False

	def add_opponent(self, opponent):
		if (opponent not in self.opponents) and (opponent != self.name):
			self.opponents.append(opponent)

	def add_game(self, game):
		if game not in self.games:
			self.games.append(game)

	def print_team(self):
		#prints useful information about a team
		print "=" * len(self.name)
		print self.name
		print "=" * len(self.name)
		if self.power is not None:
			print "Power: %5.1f" %(self.power)

		print "Unique opponents:"
		for opponent in self.opponents:
			print "%s,"%(opponent),
		print "\nGames:"
		for game in self.games:
			print game

	def __str__(self):
		return self.name

	def __deepcopy__(self, memo):
		copy_team = Team(self.name)
		copy_team.power = copy.deepcopy(self.power)
		copy_team.num_games = copy.deepcopy(self.num_games)
		copy_team.num_wins = copy.deepcopy(self.num_wins)
		copy_team.is_new = copy.deepcopy(self.is_new)
		copy_team.min_games_required = copy.deepcopy(self.min_games_required)
		copy_team.min_unique_opponents = copy.deepcopy(self.min_unique_opponents)
		copy_team.opponents = copy.deepcopy(self.opponents)
		copy_team.is_connected = copy.deepcopy(self.is_connected)
		copy_team.data_for_initial_power = copy.deepcopy(self.data_for_initial_power)
		copy_team.hiatus = copy.deepcopy(self.hiatus)
		copy_team.disbanded = copy.deepcopy(self.disbanded)
		copy_team.games = copy.deepcopy(self.games)
		return copy_team

class Game:
	def __init__(self, game_data):
		#This class expects data directly from file so datetime conversion is needed
		self.date = str2dt(game_data[0])
		self.home_team = game_data[1]
		self.home_score = int(game_data[2])
		self.away_team = game_data[3]
		self.away_score = int(game_data[4])
		self.DOS = float(self.home_score - self.away_score)/float(self.home_score + self.away_score)

	def __str__(self):
		return "%s  %s  %3d  || %s  %3d  %.3f" %(self.date, self.home_team.ljust(33), self.home_score, self.away_team.ljust(33), self.away_score, self.DOS)

	def weight(self,window_start, window_end):
		diff = window_end - self.date
		months_ago = floor(12*diff.days/365)

		#return (12-months_ago)/12 #linearly decay, month by month
		#games within las 6 months are weighted 1, linear decay between 6 and 12 months, after 12 months weight is zero
		if months_ago<6:
			return 1
		elif 6<=months_ago<=12:
			return float(12 - months_ago)/6
		else:
			return 0

class Week:
	#This class is only used internally and so dates will already be in datetime format
	#games are stored week by week purely to make printing the list of games clearer
	def __init__(self, start_date, end_date):
		self.start = start_date
		self.end = end_date
		self.games = []

	def add_game(self, game):
		self.games.append(game)

	def print_week(self):
		if self.games:
			#only prints the week if there are games in it
			print "\nWeek %s - %s" %(self.start, self.end)
			print "- "*48
			for game in self.games:
				print game

	def __str__(self):
		return "%s - %s\n" %(self.start, self.end)

class Ranking:
	def __init__(self, start_date, end_date, games_file, hiatus_file = None, disbanded_file = None):
		self.start = str2dt(start_date)
		self.end = str2dt(end_date)
		self.weeks = []
		self._make_weeks()
		self.games = []
		self.teams = {}
		self.region_list = []
		self.fixed_order = []
		self.disbanded = []
		self.hiatus = []
		self.load_games(games_file)
		self.load_teams()
		self.ranked_list = [] #a dictionary converted to a list of tuples. first item in tuple is team name, second item in tuple is the team object
		self.notes = "None"
		if hiatus_file is not None:
			self.load_hiatus_teams(hiatus_file)
		if disbanded_file is not None:
			self.load_disbanded_teams(disbanded_file)

	def _make_weeks(self):
		#weeks go from Thursday to Wednesday to make sure tournaments are captured in a single week
		wednesday = 2 #to match numerical weekday number in datetime
		num_days = (wednesday - self.start.weekday()) % 7
		last_day = self.start + num_days*day
		
		self.weeks.append(Week(self.start, last_day))
		last_day += 7*day
		while last_day <= self.end:
			self.weeks.append(Week(last_day - 6*day, last_day))
			last_day += 7*day

		if last_day != self.end:
			self.weeks.append(Week(last_day -6*day, self.end))

	def load_games(self, games_file):
		#game must be listed in format:
		#YYYYMMDD,Team 1 Name,XXX,Team 2 name,YYY
		#date is expected in format like 20160731, XXX and YYY are scores
		#there are no spaces between commas
		with open(games_file, 'rU') as csvfile:
			games_reader = csv.reader(csvfile, dialect='excel')
			for game in games_reader:
				if self.start <= str2dt(game[0]) <= self.end:
					self.games.append(Game(game))

		for game in self.games:
			for week in self.weeks:
				if week.start <= game.date <= week.end:
					week.add_game(game)

	def load_teams(self):
		#loads teams from given ranking period and fills in some key data
		for game in self.games:
			home = game.home_team
			away = game.away_team
			# add teams if they don't already exist.
			# set initial power arbitrarily as 700
			# fixed_order is to force teams into a fixed order for later calculation, since dictionaries are not fixed
			if home not in self.teams:
				self.teams[home] = Team(home)
				self.fixed_order.append(home)
				self.teams[home].power = 700

			if away not in self.teams:
				self.teams[away] = Team(away)
				self.fixed_order.append(away)
				self.teams[away].power = 700

			self.teams[home].increment_games()
			self.teams[away].increment_games()
			self.teams[home].add_opponent(away)
			self.teams[away].add_opponent(home)
			self.teams[home].add_game(game)
			self.teams[away].add_game(game)

			if game.home_score > game.away_score:
				self.teams[home].increment_wins()
			else:
				self.teams[away].increment_wins()
		#most appropriate to do this here after games and teams have been loaded
		self.determine_regions()
		
	def print_games_by_week(self):
		for week in self.weeks:
			week.print_week()

	def print_rankings(self, only_active_teams=False):
		print "\nRankings for period %s to %s" %(self.start, self.end)
		if only_active_teams:
			print "Only teams active this period are shown"
		print "Rank   Power  Games   Team"

		counter = 1

		no_games = []
		inactive = []

		for team in self.ranked_list:
			if only_active_teams:
				if team.is_active() and not team.hiatus and not team.disbanded:
					print "%3d   %6.1f    %2d    %s" %(counter, team.power, team.num_games, team.name)
					counter += 1
				else:
					if team.num_games == 0:
						no_games.append(team.name)
					elif not team.hiatus and not team.disbanded:
						inactive.append(team.name)
			elif not team.hiatus and not team.disbanded:
				print "%3d   %6.1f    %2d    %s" %(counter, team.power, team.num_games, team.name)
				counter += 1

		if inactive:
			print "\nThe following teams played games, but did not meet minimum activity requirements:"
			for team in inactive:
				print team

		if no_games:
			print "\nThe following teams played no games in the given period:"
			for team in no_games:
				print team

		if self.hiatus:
			print "\nThe following teams are not ranked because they are on hiatus:"
			for team in self.hiatus:
				if team in self.teams:
					print team

		if self.disbanded:
			print "\nThe following teams have disbanded, but their game results are used where required:"
			for team in self.disbanded:
				if team in self.teams:
					print team

	def determine_regions(self):
		# used to determine regions
		# creates a list for each isolated group of teams as a sublist in self.region_list
		for team in self.teams.values():
			if not self._in_a_region(team.name, self.region_list):
				self.region_list.append([team.name])
				self._recursive_regions(team,self.region_list[-1])

	def _recursive_regions(self, team, region):
		for opponent in team.opponents:
			if not self._in_a_region(opponent, self.region_list):
				region.append(opponent)
				self._recursive_regions(self.teams[opponent],region)

	def _in_a_region(self,test_item, mainlist):
		#determines if the test_item is contained in any sublist of main_list
		for sublist in mainlist:
			for item in sublist:
				if item == test_item:
					return True

		return False

	def _make_regression_function(self):
		def reg_func(x):
			# y is a vector of derivatives. the goal is solve y = 0
			num_teams = len(self.fixed_order)
			y = [0] * num_teams
			# the loop assembles the sum of squares derivative for each team
			for team, i in zip(self.fixed_order, xrange(num_teams)):
				for game in self.teams[team].games:
					# derivative is slightly differenct if the team is home or away
					if game.home_team == self.teams[team].name:
						j = self.fixed_order.index(game.away_team)
						y[i] += -(game.DOS + tanh((x[j]-x[i])/200))/(100*cosh((x[j]-x[i])/200)**2)*game.weight(self.start, self.end)
					else:
						j = self.fixed_order.index(game.home_team)
						y[i] += (game.DOS + tanh((x[i]-x[j])/200))/(100*cosh((x[i]-x[j])/200)**2)*game.weight(self.start, self.end)

			return y
		return reg_func

	def regression_ranking(self):
		#this uses least squares regression to find the most appropriate power rating for each team
		#it solves power ratings simulatenously and then uses them to rank the teams
		#to solve, we minimise the sum of least squares by taking a derivative and forcing it to zero
		#this cannot be solved analytically, so a numerical method for nonlinear systems is used (fsolve)
		regression = self._make_regression_function()
		reg_input = [700] * len(self.fixed_order) #initial guess power
		reg_result = fsolve(regression, reg_input) #magic happens here
		#order the teams by power
		#at this stage the powers have yet to be normalised to an appropriate range
		for team,i in zip(self.fixed_order,xrange(len(reg_result))):
			self.teams[team].power  = copy.deepcopy(reg_result[i])

		#sort the dictionary, then use list comprehension to only return the team object
		self.ranked_list = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]

	def anchor_regions(self, only_active_teams=False):
		#if there are disconnected regions in the network of games
		#this provides a means for giving the smaller regions a way to be subjectively anchored in
		#the largest region. it uses the highest ranked team in the smaller region as the anchor
		#and all of the other teams keep their relative power difference
		self.determine_regions()
		ranked_regions = []
		#orders regions by size
		self.region_list = sorted(self.region_list, key=len, reverse = True)

		#normalises the powers so the strongest team in the biggest region has power 1000
		max_power = None
		for team in self.region_list[0]:
			if self.teams[team].power > max_power:
				max_power = self.teams[team].power
		adjustment = max_power - 1000
		for team in self.teams.values():
			team.power -= adjustment

		if len(self.region_list)>1:
			for sublist,region_number in zip(self.region_list,xrange(len(self.region_list))):
				ranked_regions.append([])
				if region_number >0: #python indexes from 0, therefore Region 1 is 0
					#this normalises the other regions so the strongest team has power = 0
					#setting it to zero shows how the the other teams will fall relative to the strongest
					max_power = None
					for team in sublist:
						if self.teams[team].power > max_power:
							max_power = self.teams[team].power
					adjustment = max_power
				print "\nRegion %d" %(region_number+1)#because python indexes from 0
				print "========"
				if region_number>0:
					print "These powers only show how this region structured. They do not reflect global power"
					print "A subjective rating for this region is required."
				for team in self.ranked_list:
					if team.name in sublist:
						if region_number>0:
							self.teams[team.name].power -= adjustment
						print "%7.1f    %2d    %s" %(team.power, team.num_games, team.name)
						ranked_regions[region_number].append(team.name)

			satisfied = False
			adjust_to = []

			while not satisfied:
				for i in xrange(1,len(self.region_list)):
					print "\nPlease choose the power rating %s should have in Region 1" %(ranked_regions[i][0])
					adjust_to.append(raw_input("Power = "))
				#adjust powers and print full rankings
				for i in xrange(1,len(self.region_list)):
					adjustment = float(adjust_to[i-1]) - self.teams[ranked_regions[i][0]].power
					for team in ranked_regions[i]:
						self.teams[team].power += adjustment

				self.ranked_list = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]
				self.print_rankings()


				print "\nAre you happy with these rankings?"
				response = raw_input("y or n: ")
				if response == "y":
					satisfied = True
				else:
					adjust_to = []
		
			#prints the final result
		#self.print_rankings(only_active_teams)

	def load_hiatus_teams(self, hiatus_file):
		#determine hiatus teams
		with open(hiatus_file, 'rU') as csvfile:
			team_reader = csv.reader(csvfile, dialect='excel')
			for team in team_reader:
				self.hiatus.append(team[0])
				if team[0] in self.teams:
					self.teams[team[0]].hiatus = True
		
	def load_disbanded_teams(self,disbanded_file):
		#determine disbanded
		with open(disbanded_file, 'rU') as csvfile:
			team_reader = csv.reader(csvfile, dialect='excel')
			for team in team_reader:
				self.disbanded.append(team[0])
				if team[0] in self.teams:
					self.teams[team[0]].disbanded = True
	
	def add_new_game(self, game_data):
		new_game = Game(game_data)
		print "Adding the game:"
		print new_game
		self.games.append(new_game)
		self.teams[new_game.home_team].add_game(new_game)
		self.teams[new_game.away_team].add_game(new_game)

	def expected_result(self, home_team, away_team):
		#uses logistic regression to predict the DOS outcome for a matchup
		scaling_factor = 100
		home = self.teams[home_team]
		away = self.teams[away_team]
		e_DOS = -1 + 2/(1 + exp((away.power - home.power)/scaling_factor))
		ratio = (1 - e_DOS)/(e_DOS + 1) #away_score = home_score * ratio
		if ratio > 1: #away is expected to win
			print "%s is predicted to beat %s by a factor of %.1f with as DOS of %.3f" %(away_team,home_team, ratio, abs(e_DOS))
		elif ratio <1:
			print "%s is predicted to beat %s by a factor of %.1f with as DOS of %.3f" %(home_team, away_team, 1/ratio, abs(e_DOS))
		elif ratio == 1:
			print "WTF? there are no draws in Derby!"

		if abs(away.power - home.power)<40:
			print "The data says this should be a close game!"

		if abs(away.power - home.power)>150:
			print "The data says this might be a bit lop-sided..."

	def compare_rankings(self, previous_ranking):
		#takes in a ranking object and shows how the teams have moved
		#the ranking passed in as argument is expected to be older than the ranking object that is running the function
		print "\nChanges in ranking between"
		print self
		print "and"
		print previous_ranking

		print "\nchg | rank | chg | power |games| team"
		curr_rank = 1 #holds the rank position
		r_change = 0 #rank change
		p_change = 0.0 #power change
		for team in self.ranked_list:
			prev_rank = 1
			for team_pr in previous_ranking.ranked_list:
				if team.name == team_pr.name:
					r_change = prev_rank - curr_rank
					p_change = team.power - team_pr.power
				prev_rank +=1
			if r_change == 0:
				print " - ",
			else:
				print "%3d" %(r_change),
			print "%4d  %6.1f  %6.1f    %2d    %s" %(curr_rank, p_change, team.power, team.num_games, team.name)
			curr_rank += 1

	def add_note(self, note):
		self.notes = note

	def plot_team(self, team):
		opponent_powers = []
		game_DOS = []
		game_list = self.teams[team].games
		for game in game_list:
			if self.teams[team].name == game.home_team:
				opponent_powers.append(self.teams[game.away_team].power)
				game_DOS.append(game.DOS)
			else:
				opponent_powers.append(self.teams[game.home_team].power)
				game_DOS.append(-game.DOS)

		def f(t):
			return tanh((self.teams[team].power - t)/200)
		powers = np.arange(300, 1200, 1)
		title = team + " predicted DOS with actual game data\nStrength = %.1f" %(self.teams[team].power)
		plt.title(title)
		plt.plot(opponent_powers,game_DOS,'r*', powers, f(powers), 'b')
		plt.show()

		

	def __str__(self):
		#number of teams includes inactive, disbanded and hiatus teams that are in the teams list
		return "Ranking period: %s - %s\n%d games\n%d teams\nNotes: %s" %(str(self.start), str(self.end),len(self.games), len(self.teams),self.notes)








