import csv
import sys
import copy
from scipy import log, cosh, tanh, exp, floor
from scipy.optimize import fsolve
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
#shuts up the warning when colour and point size are given to plot as vectors - this occurs because python and numpy can't agree on things

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
	#games within last 6 months are weighted 1, linear decay between 6 and 12 months, after 12 months weight is zero
	if months_ago<6:
		return 1
	elif 6<=months_ago<=12:
		return float(12 - months_ago)/6
	else:
		return 0

class Team:
	def __init__(self, name):
		self.name = name
		self.power = 0.0
		self.rank = None
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
		self.previous_powers = {}
		self.previous_ranks = {}

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
			self.increment_games()
			if game.home_team == self.name:
				self.add_opponent(game.away_team)
				if game.home_score > game.away_score:
					self.increment_wins()
			else:
				self.add_opponent(game.home_team)
				if game.away_score > game.home_score:
					self.increment_wins()


	def print_team(self):
		#prints useful information about a team
		print "\n"
		print "=" * len(self.name)
		print self.name
		print "=" * len(self.name)
		if self.power is not None:
			print "Power: %5.1f" %(self.power)

		print "Unique opponents: %d" %(len(self.opponents))
		print "Games: %d" %(self.num_games)
		for game in self.games:
			if game.home_team == self.name:
				opponent = game.away_team
				opponent_score = game.away_score
				self_score = game.home_score
			else:
				opponent = game.home_team
				opponent_score = game.home_score
				self_score = game.away_score

			if opponent_score < self_score:
				result = "Win "
				signed_DOS = abs(game.DOS)
			else:
				result = "Loss"
				signed_DOS = -abs(game.DOS)

			print "%s  %s  %3d  || %s  %3d  | %s  %4d  %6.3f" %(game.date, self.name.ljust(40), self_score, opponent.ljust(40), opponent_score, result, self_score - opponent_score, signed_DOS)

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
		months_ago = floor(12*diff.days/365) #hence 364 day difference rounds down to 11 months

		weight = 1.0
		weight_DOS = 1.0
		weight_age = 1.0

		age_out_month = 6
		# Experimental weight - higher DOS is penalised according to a decay function
		# This function is between 0 and 1.
		# For small x it is close to 1
		# As x increases it sigmoidally approaches 0
		# The steepness is controlled by the power
		# The inflection point is controlled by the coefficient in the power
		# With 1.25 as the coefficient, the inflection occurs at 1/1.25 = 0.8
		# weight_DOS = 1 / ( 1 + (1.5 * self.DOS)**6)

		#return (12-months_ago)/12 #linearly decay, month by month
		#games within las 6 months are weighted 1, linear decay between 6 and 12 months, after 12 months weight is zero
		if months_ago<age_out_month:
			weight_age = 1
		elif age_out_month<=months_ago<=12:
			weight_age = 0.01 #(float(12 - months_ago)/float(12 - age_out_month))
		else:
			weight_age = 0

		return weight_age * weight_DOS

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
	def __init__(self, start_date, end_date, games_file, teams_file = None, hiatus_file = None, disbanded_file = None):
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
		self.load_teams(teams_file)
		self.ranked_list_full = [] #a dictionary converted to a list of tuples. first item in tuple is team name, second item in tuple is the team object
		self.ranked_list_active = [] # a ranked list of only teams that meet minimum requirements
		self.inactive = []
		self.notes = "None"
		if hiatus_file is not None:
			self.load_hiatus_teams(hiatus_file)
		if disbanded_file is not None:
			self.load_disbanded_teams(disbanded_file)

		self.s = 100 # The scaling factor for the logistic equation

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

	def load_teams(self, teams_file):
		# Load the list of teams if given
		if teams_file:
			with open(teams_file, 'r') as teams_in:
				for row in teams_in:
					team = row.rstrip('\n')
					self.teams[team] = Team(team)
					self.fixed_order.append(team)
					# fixed_order is to force teams into a fixed order for later calculation, since dictionaries are not fixed

		# Fill in the games for each team, catches if team is not in the team list
		for game in self.games:
			home = game.home_team
			away = game.away_team

			# Add teams if they weren't loaded and append them to the teams_file
			if home not in self.teams:
				self.teams[home] = Team(home)
				self.fixed_order.append(home)
				with open(teams_file, 'a') as teams_in:
					teams_in.write(home + "\n")

			if away not in self.teams:
				self.teams[away] = Team(away)
				self.fixed_order.append(away)
				with open(teams_file, 'a') as teams_in:
					teams_in.write(away + "\n")

			self.teams[home].add_game(game)
			self.teams[away].add_game(game)

		#most appropriate to do this here after games and teams have been loaded
		self.determine_regions()
		
	def print_games_by_week(self):
		for week in self.weeks:
			week.print_week()

	def print_rankings(self, only_active_teams=True):
		print "\nRankings for period %s to %s" %(self.start, self.end)
		if only_active_teams:
			print "Only teams active this period are shown"
		print "Rank   Power  Games   Team"

		counter = 1

		no_games = []
		inactive = []

		if only_active_teams:
			for team in self.ranked_list_active:
				print "%3d   %6.1f    %2d    %s" %(counter, team.power, team.num_games, team.name)
				counter += 1
		else:
			for team in self.ranked_list_full:
				print "%3d   %6.1f    %2d    %s" %(counter, team.power, team.num_games, team.name)
				counter += 1

		if self.inactive:
			print "\nThe following teams played games, but did not meet minimum activity requirements:"
			for team in self.inactive:
				if team.name not in self.hiatus:
					print team.name

		if no_games:
			print "\nThe following teams played no games in the given period:"
			for team in no_games:
				print team

		if self.hiatus:
			print "\nThe following teams are not ranked because they are on hiatus:"
			for team in self.hiatus:
				print team

		if self.disbanded:
			count = 0
			print "\nThe following teams have disbanded, but their game results are used where required:"
			for team in self.disbanded:
				if team in self.teams:
					print team
					count += 1
			if count == 0:
				print "'None'\n"

	def determine_regions(self):
		# used to determine regions
		# creates a list for each isolated group of teams as a sublist in self.region_list
		for team in self.teams.values():
			if not self._in_a_region(team.name, self.region_list) and team.num_games != 0:
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
			# i is the team of interest
			# j is the opponent
			# x is a vector of powers, hence x[i] is the power for the team of interest and x[j] for the opponent
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

	def create_ranking(self):
		# the following line is whichever ranking methodology has been chosen
		self.regression_ranking()

		#sort the dictionary, then use list comprehension to only return the team object
		self.ranked_list_full = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]

		#normalise the powers and fix separate regions
		self.anchor_regions()

		#remove hiatus, disbanded, and non-minimum-requirements teams and populate inactive list
		counter = 1
		for team in self.ranked_list_full:
			if team.is_active() and not team.hiatus and not team.disbanded:
				self.ranked_list_active.append(team)
				team.rank = counter
				counter +=1
			else:
				if not team.disbanded:
					self.inactive.append(team)

		# Finally, save the ranking data to file
		self.output_ranking_data()

	def regression_ranking(self):
		#this uses least squares regression to find the most appropriate power rating for each team
		#it solves power ratings simulatenously and then uses them to rank the teams
		#to solve, we minimise the sum of least squares by taking a derivative and forcing it to zero
		#this cannot be solved analytically, so a numerical method for nonlinear systems is used (fsolve)
		regression = self._make_regression_function()
		reg_input = [0] * len(self.fixed_order) #initial guess power
		reg_result = fsolve(regression, reg_input) #magic happens here
		#order the teams by power
		#at this stage the powers have yet to be normalised to an appropriate range
		for team,i in zip(self.fixed_order,xrange(len(reg_result))):
			if self.teams[team].num_games !=0:
				self.teams[team].power  = copy.deepcopy(reg_result[i])

	def anchor_regions(self):
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
			if team.num_games !=0:
				team.power -= adjustment


		if len(self.region_list)>1:
			for sublist,region_number in zip(self.region_list,xrange(len(self.region_list))):
				if len(sublist)>1:
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
					for team in self.ranked_list_full:
						if team.name in sublist:
							if region_number>0:
								self.teams[team.name].power -= adjustment
							print "%7.1f    %2d    %s" %(team.power, team.num_games, team.name)
							ranked_regions[region_number].append(team.name)

			satisfied = False
			adjust_to = []

			while not satisfied:
				for i in xrange(1,len(ranked_regions)):
					print "\nPlease choose the power rating %s should have in Region 1" %(ranked_regions[i][0])
					adjust_to.append(raw_input("Power = "))
				#adjust powers and print full rankings
				for i in xrange(1,len(ranked_regions)):
					adjustment = float(adjust_to[i-1]) - self.teams[ranked_regions[i][0]].power
					for team in ranked_regions[i]:
						self.teams[team].power += adjustment

				self.ranked_list_full = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]
				self.print_rankings(False)


				print "\nAre you happy with these rankings?"
				response = raw_input("y or n: ")
				if response == "y":
					satisfied = True
				else:
					adjust_to = []

	def load_hiatus_teams(self, hiatus_file):
		#determine hiatus teams
		with open(hiatus_file, 'rU') as h:
			for row in h:
				team = row.rstrip("\n")
				self.hiatus.append(team)
				if team in self.teams:
					self.teams[team].hiatus = True
		
	def load_disbanded_teams(self,disbanded_file):
		#determine disbanded
		with open(disbanded_file, 'rU') as d:
			for row in d:
				team = row.rstrip("\n")
				self.disbanded.append(team)
				if team in self.teams:
					self.teams[team].disbanded = True
	
	def add_new_game(self, game_data):
		new_game = Game(game_data)
		print "Adding the game:"
		print new_game
		self.games.append(new_game)
		self.teams[new_game.home_team].add_game(new_game)
		self.teams[new_game.away_team].add_game(new_game)

	def expected_result(self, home_team, away_team):
		#uses logistic regression to predict the DOS outcome for a matchup
		home = self.teams[home_team]
		away = self.teams[away_team]
		e_DOS = -1 + 2/(1 + exp((away.power - home.power)/self.s))
		ratio = (1 - e_DOS)/(e_DOS + 1) #away_score = home_score * ratio
		print "%s has a power of %.1f" %(home_team, home.power)
		print "%s has a power of %.1f" %(away_team, away.power)
		if ratio > 1: #away is expected to win
			print "%s is predicted to beat %s by a factor of %.1f with a DOS of %.3f" %(away_team,home_team, ratio, abs(e_DOS))
		elif ratio <1:
			print "%s is predicted to beat %s by a factor of %.1f with a DOS of %.3f" %(home_team, away_team, 1/ratio, abs(e_DOS))
		elif ratio == 1:
			print "WTF? there are no draws in Derby!"

		if abs(away.power - home.power)<40:
			print "The data says this should be a close game!"

		if abs(away.power - home.power)>150:
			print "The data says this might be a bit lop-sided..."

	def expected_power(self, home_team, home_score, away_score):
		home = self.teams[home_team]
		DOS = float(home_score - away_score) / (home_score + away_score)
		print DOS

		e_power = home.power + self.s * log(2/(DOS +1) - 1)

		print "%s currently has a power rating of %.1f" %(home.name, home.power)
		print "A theoretical game with score line %s %d to Opponent %d is played" %(home.name, home_score, away_score)
		print "If this was the only game for the Opponent, the opponent's power would be:"
		print "%.1f" %(e_power)

	def compare_rankings(self, previous_ranking, full_list = False):
		#takes in a ranking object and shows how the teams have moved
		#the ranking passed in as argument is expected to be older than the ranking object that is running the function
		print "\nChanges in ranking between"
		print self
		print "and"
		print previous_ranking


		changes = {} #store team:[rank change, power change] or [in/out = (1/-1)]
		
		curr_rank = 1 #holds the rank position
		r_change = 0 #rank change
		p_change = 0.0 #power change
		for team in self.ranked_list_full:
			prev_rank = 1
			for team_pr in previous_ranking.ranked_list_full:
				if team.name == team_pr.name:
					r_change = prev_rank - curr_rank
					p_change = team.power - team_pr.power
					changes[team.name] = [r_change, p_change] #catches teams in both current and previous rankings
					break
				prev_rank +=1
			if team.name not in changes:
				changes[team.name] = ["*", "*"] #catches teams new to current rankings
			curr_rank += 1
		
		for team_pr in previous_ranking.ranked_list_full:
			if team_pr.name not in changes:
				changes[team_pr.name] = [None,None] #catches teams that have dropped out of rankings

		print "\nRank | +/- | Power |  +/-  | Games | Team"
		counter = 1
		if full_list:
			list_for_ranking = self.ranked_list_full
		else:
			list_for_ranking = self.ranked_list_active
		for team in list_for_ranking: #self.ranked_list_full:
			if changes[team.name][0]=="*": #if the team was not in the previous ranking
				print "%3d     *   %6.1f       *     %2d    %s" %(counter, team.power, team.num_games, team.name)
			else: # if the team was previously ranked
				if changes[team.name][0]==0:
					print "%3d         %6.1f" %(counter, team.power),
					if changes[team.name][1]==0.0:
						print "            %2d    %s" %(team.num_games, team.name)
					else:
						print " %6.1f     %2d    %s" %(changes[team.name][1],team.num_games, team.name)
				if changes[team.name][1]==0.0 and changes[team.name][0]!=0:
					print "%3d   %3d   %6.1f             %2d    %s" %(counter, changes[team.name][0], team.power, team.num_games, team.name)
				if changes[team.name][0]!=0 and changes[team.name][1]!=0.0:
					print "%3d   %3d   %6.1f  %6.1f     %2d    %s" %(counter, changes[team.name][0], team.power, changes[team.name][1],team.num_games, team.name)
			counter += 1
		print "\nTeams (re)entering the rankings this period"
		print "\nTeams dropping out of the rankings this period"
			
	def add_note(self, note):
		# Might be useful
		self.notes = note

	def plot_team(self, team, display=False):
		opponent_powers = []
		game_DOS = []
		game_list = self.teams[team].games
		colours = []
		sizes = []
		t_diff = (self.end - self.start).total_seconds()

		for game in game_list:
			colours.append((game.date - self.start).total_seconds()/t_diff)
			sizes.append(weight(game.date,self.start, self.end)*100)
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
		plt.plot(powers, f(powers), 'b')
		plt.scatter(opponent_powers,game_DOS, c= colours, marker = 'o', s=sizes)
		axes = plt.gca()
		axes.set_xlim([300,1200])
		axes.set_ylim([-1,1])
		
		if display:
			plt.show()
		else:
			name_parts = team.split(" ")
			if len(name_parts) >1:
				fig_name =  name_parts[0] + name_parts[1] + "_" + str(self.end) + ".png"
			else:
				fig_name =  name_parts[0] + "_" + str(self.end) + ".png"
			plt.savefig("Plots/" + fig_name )
		plt.close('all')

	def output_ranking_data(self):
		# A function to write all the important data to file
		self._output_games_organised_by_team()
		self._output_games_organised_by_week()
		self._output_ranking_all()
		self._output_ranking_active()
		self._output_powers_ranks()
		self._output_inactive_teams()
		self._output_ranking_detailed()

	def _output_games_organised_by_team(self):
		# This function writes a list of each team's games
		# It is ordered by the ranking, so the create_ranking method must be called first
		# Each game has two teams, so games will necessarily be found twice each in this list
		# This is mainly for ease of inspection to ensure all relevant games are accounted for
		output_file = "games_by_team_" + str(self.start) + '_to_' + str(self.end) + '.txt'
		with open(output_file, 'w') as output:
			output.write("A list of the games used in the rankings calculation for the period " + str(self.start) + ' to ' + str(self.end) + "\n")

			for team in self.ranked_list_full:
				output_string = "\n"
				output_string += "=" * len(team.name)
				output_string += "\n"
				output_string += team.name
				output_string += "\n"
				output_string += "=" * len(team.name)
				output_string += "\n"
				if team.power is not None:
					output_string += "Power: %5.1f" %(team.power)
					output_string += "\n"

				output_string += "Unique opponents: %d" %(len(team.opponents))
				output_string += "\n"
				output_string += "Games: %d" %(team.num_games)
				output_string += "\n"
				for game in team.games:
					if game.home_team == team.name:
						opponent = game.away_team
						opponent_score = game.away_score
						self_score = game.home_score
					else:
						opponent = game.home_team
						opponent_score = game.home_score
						self_score = game.away_score

					if opponent_score < self_score:
						result = "Win "
						signed_DOS = abs(game.DOS)
					else:
						result = "Loss"
						signed_DOS = -abs(game.DOS)

					output_string += "%s  %s  %3d  || %s  %3d  | %s  %4d  %6.3f" %(game.date, team.name.ljust(40), self_score, opponent.ljust(40), opponent_score, result, self_score - opponent_score, signed_DOS)
					output_string += "\n"

				output.write(output_string)

	def _output_games_organised_by_week(self):
		# This function writes a list of each team's games
		# It is ordered by date and grouped by week
		# This is mainly for ease of inspection to ensure all relevant games are accounted for
		output_file = "games_by_week_" + str(self.start) + '_to_' + str(self.end) + '.txt'
		with open(output_file, 'w') as output:
			output.write("A list of the games grouped by week used in the rankings calculation for the period " + str(self.start) + ' to ' + str(self.end) + "\n")

			for week in self.weeks:
				output_string = ''
				if week.games:
					#only prints the week if there are games in it
					output_string += "\n"
					output_string += "="*28
					output_string += "\n"
					output_string += "Week %s - %s" %(week.start, week.end)
					output_string += "\n"
					output_string += "="*28
					output_string += "\n"
					for game in week.games:
						output_string += "%s  %s  %3d  || %s  %3d  | %6.3f" %(game.date, game.home_team.ljust(40), game.home_score, game.away_team.ljust(40), game.away_score, game.DOS)
						output_string += "\n"
					output_string += "\n"
					output.write(output_string)

	def _output_ranking_all(self):
		output_file = 'ranking_all_' + str(self.start) + '_to_' + str(self.end) + '.csv'
		with open(output_file, 'w') as output:
			counter = 1
			output.write("Ranking for all teams in the period " + str(self.start) + ' to ' + str(self.end) + "\n")
			output.write("\n  Rank   Power  Games    Team\n")
			for team in self.ranked_list_full:
				team_data = " %3d   %7.1f   %3d     %s" %(counter,team.power, team.num_games, team.name)
				if not team.is_active():
					team_data += "\t(inactive)"
				if team.hiatus:
					team_data += "\t(hiatus)"
				if team.disbanded:
					team_data += "\t(disbanded)"
				team_data += "\n"
				output.write(team_data)
				counter += 1

	def _output_ranking_active(self):
		output = 'ranking_active_' + str(self.start) + '_to_' + str(self.end) + '.csv'
		with open(output, 'wb') as csvfile:
			game_writer = csv.writer(csvfile, delimiter=',')
			counter = 1
			csvfile.write("Ranking for active teams for the period " + str(self.start) + ' to ' + str(self.end) + "\n")
			for team in self.ranked_list_active:
				team_data = [counter,team.power, team.num_games, team.name]
				game_writer.writerow(team_data)
				counter += 1

	def _output_powers_ranks(self):
		power_file = 'powers_ranks_' + str(self.end) + '.csv'
		with open(power_file, 'wb') as pfile:
			date = str(self.end).replace("-","")
			power_writer = csv.writer(pfile, delimiter=',')
			for team in self.teams.values():
				if team.rank is not None:
					power_writer.writerow([team.name, team.power, team.rank])
				else:
					power_writer.writerow([team.name, team.power, "None"])

	def _output_inactive_teams(self):
		output_file = "inactive_teams_" + str(self.start) + '_to_' + str(self.end) + '.txt'
		with open(output_file,'w') as output:
			output.write("Inactive teams for the period "+ str(self.start) + ' to ' + str(self.end) + "\n\n")
			for team in self.inactive:
				output.write(team.name)
				if team.hiatus:
					output.write(" (hiatus)")
				output.write("\n")

	def _output_ranking_detailed(self):
		# Prints out a ranking ready to be distributed for public consumption
		# Includes a section at the end listing inactive teams + hiatus/disbanded teams if their game data is used
		output_file = 'ranking_' + str(self.start) + '_to_' + str(self.end) + '.csv'
		with open(output_file, 'w') as output:
			output.write("Ranking for active teams in the period " + str(self.start) + ' to ' + str(self.end) + "\n")
			output.write("\n  Rank   Power  Games    Team\n")
			for team in self.ranked_list_active:
				team_data = " %3d   %7.1f   %3d     %s\n" %(team.rank, team.power, team.num_games, team.name)
				output.write(team_data)
			output.write("\nInactive teams this period:\n")
			for team in self.inactive:
				output.write(team.name)
				if team.hiatus:
					output.write(" (hiatus)")
				output.write("\n")

	def __str__(self):
		#number of teams includes inactive, disbanded and hiatus teams that are in the teams list
		return "Ranking period: %s - %s\n%d games\n%d teams\nNotes: %s" %(str(self.start), str(self.end),len(self.games), len(self.teams),self.notes)

class ImprovedRanking(Ranking):
	# The file previous_ranking_dates_file must contain dates in descending order (i.e. newest first)
	# The dates are the end date of each ranking period
	# There should be at least one year's worth of ranking dates in the file
	# The file needs to be managed manually at this point
	
	def __init__(self, start_date, end_date, games_file, previous_ranking_dates_file, teams_file, hiatus_file = None, disbanded_file = None):
		Ranking.__init__(self, start_date, end_date, games_file, teams_file, hiatus_file, disbanded_file)
		self.previous_ranking_dates = [] # The dates will be loaded in order from newest to oldest
		self.teams_with_new_games = []
		self.load_previous_powers_ranks(previous_ranking_dates_file)

	def load_previous_powers_ranks(self, prd_file):
		with open(prd_file, 'r') as csvfile:
			prd_reader = csv.reader(csvfile, dialect='excel')
			for prd in prd_reader:
				self.previous_ranking_dates.append(str2dt(prd[0]))

		for date in self.previous_ranking_dates:
			ppr_file = 'powers_ranks_' + str(date) + '.csv'
			with open(ppr_file, 'r') as ppr_file:
				ppr_reader = csv.reader(ppr_file, delimiter=',')
				for ppr in ppr_reader:
					if ppr[0] not in self.teams:
						self.teams[ppr[0]] = Team(ppr[0])
						self.teams[ppr[0]].power = 700
					if ppr[1] != "0.0":
						self.teams[ppr[0]].previous_powers[date] = float(ppr[1])
					if ppr[2] != "None":
						self.teams[ppr[0]].previous_ranks[date] = int(ppr[2])
		
		# Make a list of teams that have added new games and who will have their ranking adjusted
		for game in self.games:
			if game.date > self.previous_ranking_dates[0]:
				if game.home_team not in self.teams_with_new_games:
					self.teams_with_new_games.append(game.home_team)
				if game.away_team not in self.teams_with_new_games:
					self.teams_with_new_games.append(game.away_team)

	def _make_regression_function(self):
		def reg_func(x):
			# y is a vector of derivatives. the goal is solve y = 0
			num_teams = len(self.fixed_order)
			y = [0] * num_teams
			# the loop assembles the sum of squares derivative for each team
			# i is the team of interest
			# j is the opponent
			# x is a vector of powers, hence x[i] is the power for the team of interest and x[j] for the opponent
			for team, i in zip(self.fixed_order, xrange(num_teams)):
				if team in self.teams_with_new_games:
					for game in self.teams[team].games:
						# derivative is slightly different if the team is home or away
						if game.home_team == self.teams[team].name:
							j = self.fixed_order.index(game.away_team)
							# If the game was first used in a previous ranking, then grab the opponent's power from that ranking
							if game.date > self.previous_ranking_dates[0]:
								y[i] += -(game.DOS + tanh((x[j]-x[i])/(2*self.s)))/(self.s*cosh((x[j]-x[i])/(2*self.s))**2)#*game.weight(self.start, self.end)
							else:
								prev_power = float(self.get_previous_power(game.away_team, game.date))
								y[i] += -(game.DOS + tanh((prev_power - x[i])/(2*self.s)))/(self.s*cosh((prev_power - x[i])/(2*self.s))**2)#*game.weight(self.start, self.end)
						else:
							j = self.fixed_order.index(game.home_team)
							if game.date > self.previous_ranking_dates[0]:
								y[i] += (game.DOS + tanh((x[i]-x[j])/(2*self.s)))/(self.s*cosh((x[i]-x[j])/(2*self.s))**2)#*game.weight(self.start, self.end)
							else:
								prev_power = float(self.get_previous_power(game.home_team, game.date))
								y[i] += (game.DOS + tanh((x[i]-prev_power)/(2*self.s)))/(self.s*cosh((x[i]-prev_power)/(2*self.s))**2)#*game.weight(self.start, self.end)
			return y
		return reg_func

	def regression_ranking(self):
		#this uses least squares regression to find the most appropriate power rating for each team
		#it solves power ratings simulatenously and then uses them to rank the teams
		#to solve, we minimise the sum of least squares by taking a derivative and forcing it to zero
		#this cannot be solved analytically, so a numerical method for nonlinear systems is used (fsolve)
		regression = self._make_regression_function()
		reg_input = []
		for team in self.fixed_order:
			if self.previous_ranking_dates[0] in self.teams[team].previous_powers:
				
				if team == "Manneken Beasts":
					reg_input.append(700)
				elif team == "San Diego Aftershocks":
					reg_input.append(800)
				elif team == "Toronto Men's Roller Derby":
					reg_input.append(800)
				elif team == "Tyne and Fear Roller Derby":
					reg_input.append(800)
				elif team == "Harm City Men's Derby":
					reg_input.append(600)
				elif team == "Pittsburgh Blue Streaks":
					reg_input.append(500)
				elif team == "Flour City Fear Men's Roller Derby":
					reg_input.append(500)
				elif team == "Cleveland Men's Roller Derby":
					reg_input.append(500)
				else:
					reg_input.append(self.teams[team].previous_powers[self.previous_ranking_dates[0]])
						
			else:
				 reg_input.append(700)#initial guess power

		reg_result = fsolve(regression, reg_input) #magic happens here

		#order the teams by power
		#at this stage the powers have yet to be normalised to an appropriate range
		for team,i in zip(self.fixed_order,xrange(len(reg_result))):
			if self.teams[team].num_games !=0:
				self.teams[team].power  = copy.deepcopy(reg_result[i])

	def create_ranking(self):
		# the following line is whichever ranking methodology has been chosen
		self.regression_ranking()

		#normalises the powers so the strongest team in the biggest region has power 1000
		# this assumes that the strongest team over all defninitely played games this time
		# max_power = None
		# for team in self.teams_with_new_games:
		# 	if self.teams[team].power > max_power:
		# 		max_power = self.teams[team].power
		# adjustment = max_power - 1000
		# for team in self.teams.values():
		# 	team.power -= adjustment

		# No need to normalise as we have anchor points from the old data

		#adjust the powers of the teams with no new games to their previous powers
		# Need to fix this for when there is more than one previous ranking period
		for team in self.teams:
			if team not in self.teams_with_new_games:
				if self.previous_ranking_dates[0] in self.teams[team].previous_powers:
					self.teams[team].power = self.teams[team].previous_powers[self.previous_ranking_dates[0]]

		#sort the dictionary, then use list comprehension to only return the team object
		self.ranked_list_full = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]

		#normalise the powers and fix separate regions
		#self.anchor_regions()

		#remove hiatus, disbanded, and non-minimum-requirements teams and populate inactive list
		counter = 1
		for team in self.ranked_list_full:
			if team.is_active() and not team.hiatus and not team.disbanded:
				self.ranked_list_active.append(team)
				team.rank = counter
				counter +=1
			else:
				if not team.disbanded:
					self.inactive.append(team)

		# Finally, save the ranking data to file
		self.output_ranking_data()

	def get_previous_power(self, team, game_date):

		for date in self.previous_ranking_dates:
			if game_date <= date:
				# Then we have found the rankings period where this game was first used
				return self.teams[team].previous_powers[date]
				# This should always find a value given a key (date) because a team will only be given a power for that ranking period
				# if they played a game in that period

		# If the loop finishes without returning, then something has gone wrong, and need to throw an error
		raise ValueError('Failed to get a date')

	def anchor_regions(self):
		#if there are disconnected regions in the network of games
		#this provides a means for giving the smaller regions a way to be subjectively anchored in
		#the largest region. it uses the highest ranked team in the smaller region as the anchor
		#and all of the other teams keep their relative power difference
		self.determine_regions()
		ranked_regions = []
		#orders regions by size
		self.region_list = sorted(self.region_list, key=len, reverse = True)


		#normalises the powers so the strongest team in the biggest region has power 1000
		# max_power = None
		# for team in self.region_list[0]:
		# 	if team in self.teams_with_new_games:
		# 		if self.teams[team].power > max_power:
		# 			max_power = self.teams[team].power
		# adjustment = max_power - 1000
		# for team in self.teams.values():
		# 	team.power -= adjustment

		if len(self.region_list)>1:
			for sublist,region_number in zip(self.region_list,xrange(len(self.region_list))):
				if len(sublist)>1:
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
					for team in self.ranked_list_full:
						if team.name in sublist:
							if region_number>0:
								self.teams[team.name].power -= adjustment
							print "%7.1f    %2d    %s" %(team.power, team.num_games, team.name)
							ranked_regions[region_number].append(team.name)

			satisfied = False
			adjust_to = []

			while not satisfied:
				for i in xrange(1,len(ranked_regions)):
					print "\nPlease choose the power rating %s should have in Region 1" %(ranked_regions[i][0])
					adjust_to.append(raw_input("Power = "))
				#adjust powers and print full rankings
				for i in xrange(1,len(ranked_regions)):
					adjustment = float(adjust_to[i-1]) - self.teams[ranked_regions[i][0]].power
					for team in ranked_regions[i]:
						self.teams[team].power += adjustment

				self.ranked_list_full = [value for key,value in sorted(self.teams.items(), key=lambda x: x[1].power, reverse = True)]
				self.print_rankings(False)


				print "\nAre you happy with these rankings?"
				response = raw_input("y or n: ")
				if response == "y":
					satisfied = True
				else:
					adjust_to = []

	def _output_ranking_detailed(self):
		# Prints out a ranking ready to be distributed for public consumption
		# Includes a section at the end listing inactive teams + hiatus/disbanded teams if their game data is used
		output_file = 'ranking_' + str(self.start) + '_to_' + str(self.end) + '.csv'
		with open(output_file, 'w') as output:
			output.write("Ranking for active teams in the period " + str(self.start) + ' to ' + str(self.end) + "\n")
			output.write("\n  Rank   Power  Games    Team\n")
			for team in self.ranked_list_active:
				team_data = " %3d   %7.1f   %3d     %s" %(team.rank,team.power, team.num_games, team.name)
				if self.previous_ranking_dates[0] not in team.previous_ranks:
					team_data += " /\/\/"
				team_data += "\n"
				output.write(team_data)
			
			output.write("\nInactive teams this period:\n")
			for team in self.inactive:
				output.write(team.name)
				if team.hiatus:
					output.write(" (hiatus)")
				if self.previous_ranking_dates[0] in team.previous_ranks:
					output.write(" *")
				output.write("\n")

	def _output_ranking_comparison(self):
		output_file = 'ranking_comparison_' + str(self.start) + '_to_' + str(self.end) + '.csv'
		with open(output_file, 'w') as output:
			output.write("Ranking for active teams in the period " + str(self.start) + ' to ' + str(self.end) + "\n")
			output.write("\nRank | +/- | Power |  +/-  | Games | Team\n")
			for team in self.ranked_list_active:
				previous_rank = "None"
				previous_power = "None"
				if self.previous_ranking_dates[0] in team.previous_ranks:
					# Need to make sure the team appears in the immeditaely preceding ranking
					previous_rank = team.previous_ranks[self.previous_ranking_dates[0]]
					previous_power = team.previous_powers[self.previous_ranking_dates[0]]
				
				if  previous_rank == "None" and previous_power == "None": #if the team was not in the previous ranking
					output.write("%3d         %6.1f       N     %2d    %s\n" %(team.rank, team.power, team.num_games, team.name))
				else: # if the team was previously ranked
					if team.rank == previous_rank:
						output.write("%3d         %6.1f" %(team.rank, team.power))
						if team.power == previous_power:
							output.write("             %2d    %s\n" %(team.num_games, team.name))
						else:
							output.write("  %6.1f     %2d    %s\n" %(team.power - previous_power,team.num_games, team.name))
					if team.power == previous_power and team.rank != previous_rank:
						output.write("%3d   %3d   %6.1f             %2d    %s\n" %(team.rank, -team.rank + previous_rank, team.power, team.num_games, team.name))
					if team.power != previous_power and team.rank != previous_rank:
						output.write("%3d   %3d   %6.1f  %6.1f     %2d    %s\n" %(team.rank, -team.rank + previous_rank, team.power, team.power - previous_power,team.num_games, team.name))

	def output_ranking_data(self):
		# A function to write all the important data to file
		self._output_games_organised_by_team()
		self._output_games_organised_by_week()
		self._output_ranking_all()
		self._output_ranking_active()
		self._output_powers_ranks()
		self._output_inactive_teams()
		self._output_ranking_detailed()
		# for team in self.teams_with_new_games:
		# 	self.plot_team(team)

class WFTDAGame(Game):
	def __init__(self, game_data):
		Game.__init__(self, game_data)
		self.WLFactorHome = 3 * float(self.home_score)/float(self.home_score + self.away_score)
		self.WLFactorAway = 3 * float(self.away_score)/float(self.home_score + self.away_score)

class WFTDATeam(Team):
	def __init__(self, name):
		Team.__init__(self,name)
		self.game_points = []


		
class WFTDARanking(Ranking):
	def __init__(self, start_date, end_date, games_file, previous_ranking_dates_file, teams_file, hiatus_file = None, disbanded_file = None):
		Ranking.__init__(self, start_date, end_date, games_file, teams_file, hiatus_file, disbanded_file)

	def calculate(self):
		pass



# Load a list of teams and handle teams that didn't play a game
